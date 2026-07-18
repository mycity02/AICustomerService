"""
售后退款服务
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from database.models import (
    RefundRequest, RefundType, RefundStatus, RefundReason,
    Order, OrderItem, OrderStatus, Transaction, TransactionStatus
)

logger = logging.getLogger(__name__)

# 退款原因中文映射
REASON_LABELS = {
    RefundReason.QUALITY_ISSUE: "质量问题",
    RefundReason.NOT_AS_DESCRIBED: "与描述不符",
    RefundReason.WRONG_ITEM: "发错商品",
    RefundReason.MISSING_PARTS: "缺少部件",
    RefundReason.NO_LONGER_NEEDED: "不想要了",
    RefundReason.OTHER: "其他原因",
}

TYPE_LABELS = {
    RefundType.REFUND_ONLY: "仅退款",
    RefundType.RETURN_REFUND: "退货退款",
    RefundType.EXCHANGE: "换货",
}

STATUS_LABELS = {
    RefundStatus.PENDING: "待审核",
    RefundStatus.APPROVED: "已同意",
    RefundStatus.REJECTED: "已拒绝",
    RefundStatus.RETURNING: "退货中",
    RefundStatus.REFUNDING: "退款中",
    RefundStatus.COMPLETED: "已完成",
    RefundStatus.CANCELLED: "已取消",
}


class RefundService:
    """售后退款服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_eligible_orders(self, user_id: str) -> List[Dict]:
        """获取可申请售后的订单（已支付/已发货/已完成，且无进行中的售后）"""
        # 查询有效订单（使用枚举值）
        stmt = select(Order).where(
            Order.buyer_id == user_id,
            Order.status.in_([OrderStatus.PAID.value, OrderStatus.DELIVERED.value, OrderStatus.COMPLETED.value])
        ).order_by(Order.created_at.desc())
        result = self.db.execute(stmt)
        orders = result.scalars().all()
        
        logger.info(f"找到 {len(orders)} 个有效订单（已支付/已送达/已完成）")

        # 过滤掉已有进行中售后的订单
        eligible = []
        for order in orders:
            logger.info(f"检查订单 {order.order_no}, 状态: {order.status.value}")
            refund_stmt = select(RefundRequest).where(
                RefundRequest.order_id == order.id,
                RefundRequest.status.in_([
                    RefundStatus.PENDING, RefundStatus.APPROVED,
                    RefundStatus.RETURNING, RefundStatus.REFUNDING
                ])
            )
            refund_result = self.db.execute(refund_stmt)
            existing_refund = refund_result.scalar_one_or_none()
            if existing_refund:
                logger.info(f"订单 {order.order_no} 已有进行中的售后，跳过")
            if existing_refund is None:
                # 获取订单商品
                items_stmt = select(OrderItem).where(OrderItem.order_id == order.id)
                items_result = self.db.execute(items_stmt)
                items = items_result.scalars().all()

                eligible.append({
                    "id": order.id,
                    "order_no": order.order_no,
                    "status": order.status.value,
                    "total_amount": order.total_amount,
                    "created_at": order.created_at.isoformat() if order.created_at else "",
                    "items": [
                        {
                            "id": item.id,
                            "product_id": item.product_id,
                            "product_title": item.product_title,
                            "price": item.price,
                        }
                        for item in items
                    ]
                })
        
        logger.info(f"最终符合条件的订单数: {len(eligible)}")

        return eligible

    def create_refund_request(
        self, user_id: str, order_id: str, order_item_id: Optional[str],
        refund_type: str, reason: str, description: Optional[str],
        evidence_images: Optional[List[str]], refund_amount: int
    ) -> Dict:
        """创建售后申请"""
        refund_id = str(uuid.uuid4())
        refund_no = f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

        refund = RefundRequest(
            id=refund_id,
            refund_no=refund_no,
            order_id=order_id,
            order_item_id=order_item_id,
            user_id=user_id,
            refund_type=RefundType(refund_type),
            reason=RefundReason(reason),
            description=description,
            evidence_images=evidence_images,
            refund_amount=refund_amount,
            status=RefundStatus.PENDING,
        )
        self.db.add(refund)
        self.db.commit()
        self.db.refresh(refund)

        return {
            "id": refund.id,
            "refund_no": refund.refund_no,
            "status": refund.status.value,
            "refund_type": refund.refund_type.value,
            "refund_amount": refund.refund_amount,
        }

    def auto_review(self, refund_id: str) -> Dict:
        """自动审核：小额或质量问题自动通过"""
        stmt = select(RefundRequest).where(RefundRequest.id == refund_id)
        result = self.db.execute(stmt)
        refund = result.scalar_one_or_none()
        if not refund:
            return {"approved": False, "reason": "售后单不存在"}

        auto_approve = False
        note = ""

        # 小额自动通过（50元以下）
        if refund.refund_amount < 5000:
            auto_approve = True
            note = "小额自动审核通过"
        # 质量问题/发错商品自动通过
        elif refund.reason in (RefundReason.QUALITY_ISSUE, RefundReason.WRONG_ITEM):
            auto_approve = True
            note = f"原因({REASON_LABELS.get(refund.reason, '')})自动审核通过"

        if auto_approve:
            if refund.refund_type == RefundType.REFUND_ONLY:
                refund.status = RefundStatus.REFUNDING
            else:
                refund.status = RefundStatus.APPROVED
            refund.review_note = note
            refund.reviewed_at = datetime.now()
            self.db.commit()

            # 仅退款类型直接执行退款
            if refund.refund_type == RefundType.REFUND_ONLY:
                self.process_refund(refund_id)

            return {"approved": True, "reason": note, "status": refund.status.value}

        return {"approved": False, "reason": "需要人工审核", "status": RefundStatus.PENDING.value}

    def process_refund(self, refund_id: str) -> bool:
        """执行退款：更新订单状态和交易记录"""
        stmt = select(RefundRequest).where(RefundRequest.id == refund_id)
        result = self.db.execute(stmt)
        refund = result.scalar_one_or_none()
        if not refund:
            return False

        # 更新售后状态
        refund.status = RefundStatus.COMPLETED
        refund.completed_at = datetime.now()

        # 更新订单状态
        order_stmt = select(Order).where(Order.id == refund.order_id)
        order_result = self.db.execute(order_stmt)
        order = order_result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.REFUNDED

        # 更新交易记录
        tx_stmt = select(Transaction).where(
            Transaction.order_id == refund.order_id,
            Transaction.status == TransactionStatus.SUCCESS
        )
        tx_result = self.db.execute(tx_stmt)
        transaction = tx_result.scalar_one_or_none()
        if transaction:
            transaction.status = TransactionStatus.REFUNDED
            transaction.refund_time = datetime.now()

        self.db.commit()
        logger.info(f"退款完成: refund_no={refund.refund_no}, amount={refund.refund_amount}")
        return True

    def get_refund(self, refund_id: str) -> Optional[Dict]:
        """获取售后详情"""
        stmt = select(RefundRequest).where(RefundRequest.id == refund_id)
        result = self.db.execute(stmt)
        refund = result.scalar_one_or_none()
        if not refund:
            return None
        return self._to_dict(refund)

    def list_refunds(self, user_id: str, page: int = 1, page_size: int = 20) -> Dict:
        """获取用户售后列表"""
        stmt = select(RefundRequest).where(
            RefundRequest.user_id == user_id
        ).order_by(RefundRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = self.db.execute(stmt)
        refunds = result.scalars().all()
        return {"items": [self._to_dict(r) for r in refunds]}

    def _to_dict(self, refund: RefundRequest) -> Dict:
        return {
            "id": refund.id,
            "refund_no": refund.refund_no,
            "order_id": refund.order_id,
            "refund_type": refund.refund_type.value,
            "refund_type_text": TYPE_LABELS.get(refund.refund_type, ""),
            "reason": refund.reason.value,
            "reason_text": REASON_LABELS.get(refund.reason, ""),
            "description": refund.description,
            "refund_amount": refund.refund_amount,
            "status": refund.status.value,
            "status_text": STATUS_LABELS.get(refund.status, ""),
            "review_note": refund.review_note,
            "created_at": refund.created_at.isoformat() if refund.created_at else "",
        }
