"""
个性化推荐服务
基于用户浏览历史推荐商品
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import Session
import math

from database.models import UserBrowseHistory, Product, Category


class RecommendationService:
    """个性化推荐服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_personalized_recommendations(
        self,
        user_id: str,
        limit: int = 10,
        exclude_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """获取个性化推荐商品"""
        browse_query = select(UserBrowseHistory).where(
            UserBrowseHistory.user_id == user_id
        ).order_by(
            desc(UserBrowseHistory.created_at)
        ).limit(30)
        
        result = self.db.execute(browse_query)
        browse_records = result.scalars().all()
        
        if not browse_records:
            return self._get_popular_products(limit)
        
        tech_weights: Dict[str, float] = {}
        category_weights: Dict[str, int] = {}
        viewed_product_ids = set()
        
        for i, record in enumerate(browse_records):
            viewed_product_ids.add(record.product_id)
            product = self.db.get(Product, record.product_id)
            
            if not product:
                continue
            
            recency_weight = 1.0 / (1 + i * 0.1)
            
            if product.tech_stack:
                for tech in product.tech_stack:
                    tech_weights[tech] = tech_weights.get(tech, 0) + recency_weight
            
            if product.category_id:
                category_weights[product.category_id] = category_weights.get(product.category_id, 0) + 1
        
        sorted_techs = sorted(tech_weights.items(), key=lambda x: x[1], reverse=True)
        top_techs = [t[0] for t in sorted_techs[:10]]
        top_categories = [c[0] for c in sorted(category_weights.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        all_products_query = select(Product).where(
            Product.status == "published"
        )
        
        result = self.db.execute(all_products_query)
        all_products = result.scalars().all()
        
        product_scores = []
        for product in all_products:
            if product.id in viewed_product_ids:
                continue
            
            if exclude_ids and product.id in exclude_ids:
                continue
            
            score = self._calculate_recommendation_score(
                product=product,
                top_techs=top_techs,
                top_categories=top_categories,
                tech_weights=tech_weights
            )
            
            if score > 0:
                product_scores.append({
                    "product": product,
                    "score": score
                })
        
        product_scores.sort(key=lambda x: x["score"], reverse=True)
        
        recommendations = []
        for item in product_scores[:limit]:
            product = item["product"]
            recommendations.append({
                "id": product.id,
                "title": product.title,
                "cover_image": product.cover_image,
                "price": float(product.price) / 100,  # 分转元
                "original_price": float(product.original_price) / 100 if product.original_price else None,
                "rating": float(product.rating) / 100 if product.rating else 0,  # 分转元
                "sales_count": product.sales_count or 0,
                "tech_stack": product.tech_stack or [],
                "score": round(item["score"], 2)
            })
        
        return recommendations
    
    def _calculate_recommendation_score(
        self,
        product: Product,
        top_techs: List[str],
        top_categories: List[str],
        tech_weights: Dict[str, float]
    ) -> float:
        """计算推荐分数"""
        score = 0.0
        
        tech_match_score = 0.0
        if product.tech_stack:
            for i, tech in enumerate(top_techs[:5]):
                if tech in product.tech_stack:
                    tech_match_score += (5 - i) * 2.0
        
        score += tech_match_score
        
        if product.category_id and product.category_id in top_categories:
            category_idx = top_categories.index(product.category_id)
            score += (5 - category_idx) * 1.5
        
        if product.rating:
            score += product.rating * 0.5
        
        if product.sales_count:
            score += min(product.sales_count / 100, 5)
        
        return score
    
    def _get_popular_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门商品（无浏览历史时使用）"""
        query = select(Product).where(
            Product.status == "published"
        ).order_by(
            desc(Product.sales_count),
            desc(Product.rating)
        ).limit(limit)
        
        result = self.db.execute(query)
        products = result.scalars().all()
        
        return [{
            "id": p.id,
            "title": p.title,
            "cover_image": p.cover_image,
            "price": float(p.price) / 100,  # 分转元
            "original_price": float(p.original_price) / 100 if p.original_price else None,
            "rating": float(p.rating) / 100 if p.rating else 0,
            "sales_count": p.sales_count or 0,
            "tech_stack": p.tech_stack or []
        } for p in products]
    
    def get_similar_products(
        self,
        product_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取相似商品"""
        product = self.db.get(Product, product_id)
        
        if not product:
            return []
        
        query = select(Product).where(
            and_(
                Product.status == "published",
                Product.id != product_id
            )
        )
        
        result = self.db.execute(query)
        all_products = result.scalars().all()
        
        scores = []
        for p in all_products:
            score = self._calculate_similarity(product, p)
            if score > 0:
                scores.append({
                    "product": p,
                    "score": score
                })
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        return [{
            "id": p["product"].id,
            "title": p["product"].title,
            "cover_image": p["product"].cover_image,
            "price": float(p["product"].price) / 100,  # 分转元
            "rating": float(p["product"].rating) / 100 if p["product"].rating else 0,
            "sales_count": p["product"].sales_count or 0,
            "tech_stack": p["product"].tech_stack or [],
            "similarity": round(p["score"], 2)
        } for p in scores[:limit]]
    
    def _calculate_similarity(self, p1: Product, p2: Product) -> float:
        """计算两个商品的相似度"""
        score = 0.0
        
        if p1.category_id and p2.category_id:
            if p1.category_id == p2.category_id:
                score += 5.0
        
        if p1.tech_stack and p2.tech_stack:
            set1 = set(p1.tech_stack)
            set2 = set(p2.tech_stack)
            intersection = set1 & set2
            union = set1 | set2
            if union:
                jaccard = len(intersection) / len(union)
                score += jaccard * 10.0
        
        return score
