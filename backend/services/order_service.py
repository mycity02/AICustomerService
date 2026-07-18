"""
订单服务模块
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload
from database.models import Order, OrderItem, Product, CartItem, OrderStatus, ProductStatus
import uuid
from datetime import datetime


class OrderService:
    """订单服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_order(self, buyer_id: str, product_ids: List[str]) -> Dict[str, Any]:
        """创建订单"""
        # 打印调试信息
        print(f"创建订单 - buyer_id: {buyer_id}, product_ids: {product_ids}")
        
        # 获取商品信息
        result = self.db.execute(
            select(Product).where(
                and_(
                    Product.id.in_(product_ids),
                    Product.status == ProductStatus.PUBLISHED
                )
            )
        )
        products = result.scalars().all()
        
        print(f"找到的商品数量: {len(products)}, 期望数量: {len(product_ids)}")
        
        if not products:
            raise ValueError("商品不存在或未发布")
        
        if len(products) != len(product_ids):
            found_ids = [p.id for p in products]
            missing_ids = [pid for pid in product_ids if pid not in found_ids]
            raise ValueError(f"部分商品不存在或未发布，缺失的商品ID: {missing_ids}")
        
        # 计算总金额
        total_amount = sum(p.price for p in products)
        
        # 生成订单号
        order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        
        # 创建订单
        order = Order(
            id=str(uuid.uuid4()),
            order_no=order_no,
            buyer_id=buyer_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING
        )
        
        self.db.add(order)
        
        # 创建订单明细
        order_items = []
        for product in products:
            order_item = OrderItem(
                id=str(uuid.uuid4()),
                order_id=order.id,
                product_id=product.id,
                seller_id=product.seller_id,
                product_title=product.title,
                product_cover=product.cover_image,
                price=product.price
            )
            self.db.add(order_item)
            order_items.append(order_item)
        
        self.db.commit()
        self.db.refresh(order)
        
        # 从购物车删除已下单商品
        result = self.db.execute(
            select(CartItem).where(
                and_(
                    CartItem.user_id == buyer_id,
                    CartItem.product_id.in_(product_ids)
                )
            )
        )
        cart_items = result.scalars().all()
        for item in cart_items:
            self.db.delete(item)
        
        self.db.commit()
        
        return {
            "id": order.id,
            "order_no": order.order_no,
            "buyer_id": buyer_id,
            "total_amount": total_amount,
            "status": order.status.value,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_title": item.product_title,
                    "product_cover": item.product_cover,
                    "price": item.price,
                    "seller_id": item.seller_id
                }
                for item in order_items
            ]
        }
    
    def get_order(self, order_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取订单详情"""
        query = select(Order).options(
            joinedload(Order.buyer),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).where(Order.id == order_id)
        
        if user_id:
            query = query.where(Order.buyer_id == user_id)
        
        result = self.db.execute(query)
        order = result.unique().scalar_one_or_none()
        
        if not order:
            return None
        
        return self._order_to_dict(order)

    def get_order_by_no(
        self,
        order_no: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get an order by business order number."""
        query = select(Order).options(
            joinedload(Order.buyer),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).where(Order.order_no == order_no)

        if user_id:
            query = query.where(Order.buyer_id == user_id)

        result = self.db.execute(query)
        order = result.unique().scalar_one_or_none()

        if not order:
            return None

        data = self._order_to_dict(order)
        if hasattr(order, "buyer") and order.buyer:
            data["buyer_name"] = order.buyer.username
            data["buyer_phone"] = getattr(order.buyer, "phone", "")
        return data

    def list_orders(
        self,
        user_id: Optional[str] = None,
        seller_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取订单列表"""
        query = select(Order).options(
            joinedload(Order.buyer),
            joinedload(Order.items)
        )
        
        filters = []
        
        if user_id:
            filters.append(Order.buyer_id == user_id)
        
        if seller_id:
            # 查询包含该卖家商品的订单
            query = query.join(Order.items).where(OrderItem.seller_id == seller_id)
        
        if status:
            filters.append(Order.status == OrderStatus(status))
        
        if filters:
            query = query.where(and_(*filters))
        
        # 计算总数
        count_query = select(Order)
        if filters:
            count_query = count_query.where(and_(*filters))
        count_result = self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        query = query.order_by(Order.created_at.desc())
        
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = self.db.execute(query)
        orders = result.unique().scalars().all()
        
        return {
            "items": [self._order_to_dict(o, simple=True) for o in orders],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    def update_order_status(
        self,
        order_id: str,
        status: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新订单状态"""
        result = self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        # 权限检查（如果提供了user_id）
        if user_id and order.buyer_id != user_id:
            raise PermissionError("无权操作此订单")
        
        order.status = OrderStatus(status)
        
        # 更新相关时间戳
        if status == "paid":
            order.payment_time = datetime.now()
        elif status == "delivered":
            order.delivery_time = datetime.now()
        elif status == "completed":
            order.completion_time = datetime.now()
            # 更新商品销量
            result = self.db.execute(
                select(OrderItem).where(OrderItem.order_id == order_id)
            )
            items = result.scalars().all()
            for item in items:
                product_result = self.db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = product_result.scalar_one_or_none()
                if product:
                    product.sales_count += 1
        
        self.db.commit()
        self.db.refresh(order)
        
        return self._order_to_dict(order)
    
    def cancel_order(self, order_id: str, user_id: str) -> bool:
        """取消订单"""
        result = self.db.execute(
            select(Order).where(
                and_(
                    Order.id == order_id,
                    Order.buyer_id == user_id
                )
            )
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return False
        
        # 只能取消待支付的订单
        if order.status != OrderStatus.PENDING:
            raise ValueError("只能取消待支付的订单")
        
        order.status = OrderStatus.CANCELLED
        self.db.commit()
        
        return True
    
    def _order_to_dict(self, order: Order, simple: bool = False) -> Dict[str, Any]:
        """将订单对象转换为字典"""
        data = {
            "id": order.id,
            "order_no": order.order_no,
            "total_amount": order.total_amount,  # 保持分为单位
            "status": order.status.value,
            "payment_method": order.payment_method,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
        
        if hasattr(order, 'buyer') and order.buyer:
            data["buyer"] = {
                "id": order.buyer.id,
                "username": order.buyer.username
            }
        
        # items 字段始终返回（前端需要显示商品名称）
        if hasattr(order, 'items'):
            data["items"] = [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_title": item.product_title,
                    "product_cover": item.product_cover,
                    "price": item.price,  # 保持分为单位
                    "seller_id": item.seller_id
                }
                for item in order.items
            ]
        
        if not simple:
            data.update({
                "payment_time": order.payment_time.isoformat() if order.payment_time else None,
                "delivery_time": order.delivery_time.isoformat() if order.delivery_time else None,
                "completion_time": order.completion_time.isoformat() if order.completion_time else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            })
        
        return data
