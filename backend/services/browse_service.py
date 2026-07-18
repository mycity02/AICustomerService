"""
浏览历史服务
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
import uuid
from datetime import datetime, timedelta

from database.models import UserBrowseHistory, Product


class BrowseService:
    def __init__(self, db: Session):
        self.db = db
    
    def record_browse(
        self,
        user_id: str,
        product_id: str,
        view_duration: int = 0
    ) -> Dict[str, Any]:
        """记录浏览历史（存在则更新，不存在则新增）"""
        import uuid
        browse_id = str(uuid.uuid4())
        
        stmt = insert(UserBrowseHistory).values(
            id=browse_id,
            user_id=user_id,
            product_id=product_id,
            view_duration=view_duration
        ).on_duplicate_key_update(
            view_duration=view_duration,
            created_at=datetime.now()
        )
        
        self.db.execute(stmt)
        self.db.commit()
        
        return {
            "success": True,
            "message": "浏览记录已保存"
        }
    
    def get_browse_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取用户浏览历史"""
        query = select(UserBrowseHistory).options(
        ).where(
            UserBrowseHistory.user_id == user_id
        ).order_by(
            desc(UserBrowseHistory.created_at)
        )
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = self.db.execute(query)
        records = result.scalars().all()
        
        count_query = select(func.count()).select_from(UserBrowseHistory).where(
            UserBrowseHistory.user_id == user_id
        )
        count_result = self.db.execute(count_query)
        total = count_result.scalar()
        
        items = []
        for record in records:
            product = self.db.get(Product, record.product_id)
            items.append({
                "id": record.id,
                "product_id": record.product_id,
                "product_title": product.title if product else "",
                "product_cover": product.cover_image if product else "",
                "product_price": float(product.price) if product else 0,
                "view_duration": record.view_duration,
                "created_at": record.created_at.isoformat() if record.created_at else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total else 0
        }
    
    def get_user_interests(
        self,
        user_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """获取用户兴趣标签（基于浏览历史中的茶品风味标签）"""
        query = select(UserBrowseHistory).options(
        ).where(
            UserBrowseHistory.user_id == user_id
        ).order_by(
            desc(UserBrowseHistory.created_at)
        ).limit(50)
        
        result = self.db.execute(query)
        records = result.scalars().all()
        
        tech_counter: Dict[str, int] = {}
        category_counter: Dict[str, int] = {}
        
        for record in records:
            product = self.db.get(Product, record.product_id)
            if product:
                if product.tech_stack:
                    for tech in product.tech_stack:
                        tech_counter[tech] = tech_counter.get(tech, 0) + 1
                if product.category_id:
                    category_counter[product.category_id] = category_counter.get(product.category_id, 0) + 1
        
        sorted_techs = sorted(tech_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
        sorted_categories = sorted(category_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return {
            "tech_stack": [{"tech": t[0], "count": t[1]} for t in sorted_techs],
            "categories": [{"category_id": c[0], "count": c[1]} for c in sorted_categories]
        }
    
    def delete_browse_record(
        self,
        user_id: str,
        product_id: str
    ) -> bool:
        """删除单条浏览记录"""
        query = select(UserBrowseHistory).where(
            and_(
                UserBrowseHistory.user_id == user_id,
                UserBrowseHistory.product_id == product_id
            )
        )
        result = self.db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            self.db.delete(record)
            self.db.commit()
            return True
        return False
    
    def clear_browse_history(self, user_id: str) -> bool:
        """清空用户所有浏览记录"""
        query = select(UserBrowseHistory).where(
            UserBrowseHistory.user_id == user_id
        )
        result = self.db.execute(query)
        records = result.scalars().all()
        
        for record in records:
            self.db.delete(record)
        
        self.db.commit()
        return True
