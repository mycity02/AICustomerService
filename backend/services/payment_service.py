"""
支付服务模块（模拟）
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from database.models import Transaction, Order, OrderStatus, TransactionStatus
import uuid
from datetime import datetime
import random


class PaymentService:
    """支付服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_payment(
        self,
        order_id: str,
        payment_method: str
    ) -> Dict[str, Any]:
        """创建支付"""
        # 获取订单
        result = self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError("订单不存在")
        
        if order.status != OrderStatus.PENDING:
            raise ValueError("订单状态不正确")
        
        # 生成交易号
        transaction_no = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
        
        # 创建交易记录
        transaction = Transaction(
            id=str(uuid.uuid4()),
            order_id=order_id,
            transaction_no=transaction_no,
            payment_method=payment_method,
            amount=order.total_amount,
            status=TransactionStatus.PENDING
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        return {
            "transaction_id": transaction.id,
            "transaction_no": transaction.transaction_no,
            "amount": transaction.amount / 100,
            "payment_method": payment_method,
            "payment_url": f"/api/payment/mock/{transaction.id}"  # 模拟支付URL
        }
    
    def process_payment(self, transaction_id: str) -> Dict[str, Any]:
        """处理支付（模拟）"""
        # 获取交易记录
        result = self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            raise ValueError("交易不存在")
        
        # 模拟支付成功（90%成功率）
        success = random.random() < 0.9
        
        if success:
            transaction.status = TransactionStatus.SUCCESS
            transaction.payment_time = datetime.now()
            
            # 更新订单状态
            result = self.db.execute(
                select(Order).where(Order.id == transaction.order_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                order.status = OrderStatus.PAID
                order.payment_method = transaction.payment_method
                order.payment_time = datetime.now()
        else:
            transaction.status = TransactionStatus.FAILED
        
        self.db.commit()
        self.db.refresh(transaction)
        
        return {
            "success": success,
            "transaction_id": transaction.id,
            "transaction_no": transaction.transaction_no,
            "status": transaction.status.value,
            "message": "支付成功" if success else "支付失败，请重试"
        }
    
    def refund_payment(self, transaction_id: str) -> Dict[str, Any]:
        """退款"""
        result = self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            raise ValueError("交易不存在")
        
        if transaction.status != TransactionStatus.SUCCESS:
            raise ValueError("只能退款成功的交易")
        
        transaction.status = TransactionStatus.REFUNDED
        transaction.refund_time = datetime.now()
        
        # 更新订单状态
        result = self.db.execute(
            select(Order).where(Order.id == transaction.order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            order.status = OrderStatus.REFUNDED
        
        self.db.commit()
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "message": "退款成功"
        }
    
    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """获取交易详情"""
        result = self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return None
        
        return {
            "id": transaction.id,
            "transaction_no": transaction.transaction_no,
            "order_id": transaction.order_id,
            "amount": transaction.amount / 100,
            "payment_method": transaction.payment_method,
            "status": transaction.status.value,
            "payment_time": transaction.payment_time.isoformat() if transaction.payment_time else None,
            "refund_time": transaction.refund_time.isoformat() if transaction.refund_time else None,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None
        }
