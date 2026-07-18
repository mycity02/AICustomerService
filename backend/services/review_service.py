"""
评价服务模块
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from sqlalchemy.orm import joinedload
from database.models import Review, OrderItem, Order, Product, OrderStatus
import uuid
from datetime import datetime


class ReviewService:
    """评价服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_review(
        self,
        order_item_id: str,
        buyer_id: str,
        rating: int,
        content: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """创建评价"""
        # 验证评分
        if rating < 1 or rating > 5:
            raise ValueError("评分必须在1-5之间")
        
        # 获取订单项
        result = self.db.execute(
            select(OrderItem)
            .options(joinedload(OrderItem.order))
            .where(OrderItem.id == order_item_id)
        )
        order_item = result.scalar_one_or_none()
        
        if not order_item:
            raise ValueError("订单项不存在")
        
        # 验证订单状态和买家
        if order_item.order.buyer_id != buyer_id:
            raise PermissionError("无权评价此订单")
        
        if order_item.order.status != OrderStatus.COMPLETED:
            raise ValueError("只能评价已完成的订单")
        
        # 检查是否已评价
        result = self.db.execute(
            select(Review).where(Review.order_item_id == order_item_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError("已评价过此商品")
        
        # 创建评价
        review = Review(
            id=str(uuid.uuid4()),
            order_item_id=order_item_id,
            product_id=order_item.product_id,
            buyer_id=buyer_id,
            seller_id=order_item.seller_id,
            rating=rating,
            content=content,
            images=images
        )
        
        self.db.add(review)
        
        # 更新商品评分
        result = self.db.execute(
            select(Product).where(Product.id == order_item.product_id)
        )
        product = result.scalar_one_or_none()
        
        if product:
            # 计算新的平均评分
            result = self.db.execute(
                select(func.avg(Review.rating), func.count(Review.id))
                .where(Review.product_id == product.id)
            )
            avg_rating, count = result.one()
            
            # 包含新评价
            new_count = (count or 0) + 1
            new_avg = ((avg_rating or 0) * (count or 0) + rating) / new_count
            
            product.rating = int(new_avg * 100)  # 存储为整数
            product.review_count = new_count
        
        self.db.commit()
        self.db.refresh(review)
        
        return self._review_to_dict(review)
    
    def get_reviews(
        self,
        product_id: Optional[str] = None,
        buyer_id: Optional[str] = None,
        seller_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取评价列表"""
        query = select(Review).options(
            joinedload(Review.buyer),
            joinedload(Review.product)
        )
        
        filters = []
        
        if product_id:
            filters.append(Review.product_id == product_id)
        
        if buyer_id:
            filters.append(Review.buyer_id == buyer_id)
        
        if seller_id:
            filters.append(Review.seller_id == seller_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(Review.created_at.desc())
        
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = self.db.execute(query)
        reviews = result.scalars().all()
        
        return {
            "reviews": [self._review_to_dict(r) for r in reviews],
            "page": page,
            "page_size": page_size
        }
    
    def reply_review(
        self,
        review_id: str,
        seller_id: str,
        reply: str
    ) -> Dict[str, Any]:
        """回复评价"""
        result = self.db.execute(
            select(Review).where(Review.id == review_id)
        )
        review = result.scalar_one_or_none()
        
        if not review:
            raise ValueError("评价不存在")
        
        if review.seller_id != seller_id:
            raise PermissionError("无权回复此评价")
        
        review.reply = reply
        review.reply_time = datetime.now()
        
        self.db.commit()
        self.db.refresh(review)
        
        return self._review_to_dict(review)
    
    def _review_to_dict(self, review: Review) -> Dict[str, Any]:
        """将评价对象转换为字典"""
        data = {
            "id": review.id,
            "product_id": review.product_id,
            "rating": review.rating,
            "content": review.content,
            "images": review.images,
            "reply": review.reply,
            "reply_time": review.reply_time.isoformat() if review.reply_time else None,
            "created_at": review.created_at.isoformat() if review.created_at else None
        }
        
        if hasattr(review, 'buyer') and review.buyer:
            data["buyer"] = {
                "id": review.buyer.id,
                "username": review.buyer.username
            }
        
        if hasattr(review, 'product') and review.product:
            data["product"] = {
                "id": review.product.id,
                "title": review.product.title,
                "cover_image": review.product.cover_image
            }
        
        return data
