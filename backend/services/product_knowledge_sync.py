"""
商品知识库同步服务
将商品信息同步到 FAISS 向量数据库，用于 AI 推荐和咨询
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from database.models import Product, ProductStatus, Review
from .knowledge_retriever import knowledge_retriever
import json


class ProductKnowledgeSync:
    """商品知识库同步类"""
    
    def sync_product_to_knowledge(
        self,
        db: Session,
        product_id: str
    ) -> bool:
        """
        将单个商品同步到知识库
        
        Args:
            db: 数据库会话
            product_id: 商品ID
            
        Returns:
            是否成功
        """
        if not knowledge_retriever.available:
            return False
        
        # 获取商品信息
        result = db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product or product.status != ProductStatus.PUBLISHED:
            return False
        
        # 获取商品评价
        reviews_result = db.execute(
            select(Review)
            .where(Review.product_id == product_id)
            .order_by(Review.rating.desc())
            .limit(5)
        )
        reviews = reviews_result.scalars().all()
        
        # 底层字段名保持兼容，对外知识文档使用茶叶销售语义。
        difficulty = getattr(product.difficulty, "value", product.difficulty)
        features = getattr(product, "features", None) or []
        deliverables = getattr(product, "deliverables", None) or []
        content_parts = [
            f"商品名称：{product.title}",
            f"商品描述：{product.description}",
            f"价格：¥{product.price / 100:.2f}",
            f"产地与风味标签：{', '.join(product.tech_stack or [])}",
            f"口感浓度：{difficulty}",
            f"评分：{product.rating / 100:.2f}⭐",
            f"销量：{product.sales_count}",
        ]

        if features:
            content_parts.append(f"茶品特点：{', '.join(features)}")

        if deliverables:
            content_parts.append(f"包装与配送：{', '.join(deliverables)}")
        
        # 添加评价摘要
        if reviews:
            review_texts = [f"用户评价：{r.comment}" for r in reviews if r.comment]
            if review_texts:
                content_parts.append("\n".join(review_texts[:3]))  # 只取前3条
        
        content = "\n".join(content_parts)
        
        # 准备文档数据
        document = {
            "id": f"product_{product.id}",
            "content": content,
            "metadata": {
                "product_id": product.id,
                "title": product.title,
                "price": product.price / 100,
                "difficulty": difficulty,
                "rating": product.rating / 100,
                "sales_count": product.sales_count,
                "tech_stack": json.dumps(product.tech_stack or [], ensure_ascii=False),
                "category_id": product.category_id,
                "seller_id": product.seller_id,
                "source": "product_catalog"
            }
        }
        
        # 使用稳定文档 ID 实现可重复同步，避免重复向量。
        knowledge_retriever.delete_document(document["id"], "product_catalog")
        knowledge_retriever.add_documents([document], "product_catalog")
        
        return True
    
    def sync_all_products(self, db: Session) -> Dict[str, Any]:
        """
        同步所有已发布的商品到知识库
        
        Args:
            db: 数据库会话
            
        Returns:
            同步结果统计
        """
        if not knowledge_retriever.available:
            return {"success": False, "message": "知识库不可用"}
        
        # 获取所有已发布的商品
        result = db.execute(
            select(Product).where(Product.status == ProductStatus.PUBLISHED)
        )
        products = result.scalars().all()
        
        success_count = 0
        failed_count = 0
        
        for product in products:
            try:
                success = self.sync_product_to_knowledge(db, product.id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"同步商品 {product.id} 失败：{e}")
                failed_count += 1
        
        return {
            "success": True,
            "total": len(products),
            "success_count": success_count,
            "failed_count": failed_count
        }
    
    def remove_product_from_knowledge(
        self,
        product_id: str
    ) -> bool:
        """
        从知识库删除商品
        
        Args:
            product_id: 商品ID
            
        Returns:
            是否成功
        """
        if not knowledge_retriever.available:
            return False
        
        try:
            knowledge_retriever.delete_document(
                f"product_{product_id}",
                "product_catalog"
            )
            return True
        except Exception as e:
            print(f"删除商品知识库失败：{e}")
            return False
    
    def update_product_in_knowledge(
        self,
        db: Session,
        product_id: str
    ) -> bool:
        """
        更新知识库中的商品信息
        
        Args:
            db: 数据库会话
            product_id: 商品ID
            
        Returns:
            是否成功
        """
        # 先删除旧数据
        self.remove_product_from_knowledge(product_id)
        
        # 重新添加
        return self.sync_product_to_knowledge(db, product_id)


# 全局实例
product_knowledge_sync = ProductKnowledgeSync()
