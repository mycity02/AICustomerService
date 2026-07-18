"""
收藏服务模块
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from database.models import Favorite, Product, ProductStatus
import uuid


class FavoriteService:
    """收藏服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_favorite(self, user_id: str, product_id: str) -> Dict[str, Any]:
        """添加收藏"""
        # 检查商品是否存在
        result = self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise ValueError("商品不存在")
        
        # 检查是否已收藏
        result = self.db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.product_id == product_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return {"message": "已收藏", "favorite_id": existing.id}
        
        # 添加收藏
        favorite = Favorite(
            id=str(uuid.uuid4()),
            user_id=user_id,
            product_id=product_id
        )
        
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)
        
        return {"message": "收藏成功", "favorite_id": favorite.id}
    
    def remove_favorite(self, user_id: str, product_id: str) -> bool:
        """取消收藏"""
        result = self.db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.product_id == product_id
                )
            )
        )
        favorite = result.scalar_one_or_none()
        
        if not favorite:
            return False
        
        self.db.delete(favorite)
        self.db.commit()
        
        return True
    
    def get_favorites(self, user_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取收藏列表"""
        print(f"[DEBUG] 开始获取收藏列表，用户ID: {user_id}, 页码: {page}")
        
        query = select(Favorite).options(
            joinedload(Favorite.product).joinedload(Product.seller),
            joinedload(Favorite.product).joinedload(Product.category)
        ).where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
        
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        print(f"[DEBUG] 执行数据库查询...")
        result = self.db.execute(query)
        print(f"[DEBUG] 查询完成，开始处理结果...")
        favorites = result.unique().scalars().all()
        print(f"[DEBUG] 找到 {len(favorites)} 条收藏记录")
        
        items = []
        for favorite in favorites:
            product = favorite.product
            print(f"[DEBUG] 处理商品: {product.title if product else 'None'}")
            
            item_data = {
                "favorite_id": favorite.id,
                "product_id": product.id,
                "title": product.title,
                "description": product.description[:100] + "..." if len(product.description) > 100 else product.description,
                "price": product.price / 100,
                "cover_image": product.cover_image,
                "rating": product.rating / 100 if product.rating else 0,
                "sales_count": product.sales_count,
                "status": product.status.value,
                "seller": {
                    "id": product.seller.id,
                    "username": product.seller.username
                } if product.seller else None,
                "favorited_at": favorite.created_at.isoformat() if favorite.created_at else None
            }
            
            items.append(item_data)
        
        print(f"[DEBUG] 返回数据，共 {len(items)} 条")
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": len(items)
        }
    
    def is_favorited(self, user_id: str, product_id: str) -> bool:
        """检查是否已收藏"""
        result = self.db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.product_id == product_id
                )
            )
        )
        favorite = result.scalar_one_or_none()
        
        return favorite is not None
