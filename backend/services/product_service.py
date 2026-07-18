"""
商品服务模块
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import joinedload, selectinload
from database.models import Product, Category, ProductImage, ProductFile, ProductStatus, ProductDifficulty, User
import uuid
from datetime import datetime
from .product_knowledge_sync import product_knowledge_sync


class ProductService:
    """商品服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_product(
        self,
        seller_id: str,
        category_id: str,
        title: str,
        description: str,
        price: float,
        original_price: Optional[float] = None,
        cover_image: Optional[str] = None,
        demo_video: Optional[str] = None,
        tech_stack: Optional[List[str]] = None,
        difficulty: str = "medium"
    ) -> Product:
        """创建商品"""
        product = Product(
            id=str(uuid.uuid4()),
            seller_id=seller_id,
            category_id=category_id,
            title=title,
            description=description,
            price=int(price * 100),  # 转换为分
            original_price=int(original_price * 100) if original_price else None,
            cover_image=cover_image,
            demo_video=demo_video,
            tech_stack=tech_stack,
            difficulty=ProductDifficulty(difficulty),
            status=ProductStatus.DRAFT
        )
        
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        
        return product
    
    def update_product(
        self,
        product_id: str,
        **kwargs
    ) -> Optional[Product]:
        """更新商品"""
        result = self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            return None
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(product, key):
                if key in ['price', 'original_price'] and value is not None:
                    value = int(value * 100)  # 转换为分
                setattr(product, key, value)
        
        product.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(product)
        
        # 如果商品已发布，同步到知识库
        if product.status == ProductStatus.PUBLISHED:
            product_knowledge_sync.update_product_in_knowledge(self.db, product_id)
        
        return product
    
    def delete_product(self, product_id: str) -> bool:
        """删除商品"""
        result = self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            return False
        
        # 从知识库删除
        product_knowledge_sync.remove_product_from_knowledge(product_id)
        
        self.db.delete(product)
        self.db.commit()
        
        return True
    
    def get_product(self, product_id: str, increment_view: bool = False) -> Optional[Dict[str, Any]]:
        """获取商品详情"""
        result = self.db.execute(
            select(Product)
            .options(
                joinedload(Product.seller),
                joinedload(Product.category),
                selectinload(Product.images),
                selectinload(Product.files)
            )
            .where(Product.id == product_id)
        )
        product = result.scalars().first()
        
        if not product:
            return None
        
        product_dict = self._product_to_dict(product)
        
        if increment_view:
            product.view_count += 1
            self.db.commit()
        
        return product_dict
    
    def search_products(
        self,
        keyword: Optional[str] = None,
        category_id: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        difficulty: Optional[str] = None,
        tech_stack: Optional[List[str]] = None,
        status: Optional[str] = None,
        seller_id: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """搜索商品"""
        query = select(Product).options(
            joinedload(Product.seller),
            joinedload(Product.category)
        )
        
        # 构建过滤条件
        filters = []
        
        if keyword:
            from sqlalchemy import cast, Text
            filters.append(
                or_(
                    Product.title.contains(keyword),
                    Product.description.contains(keyword),
                    cast(Product.tech_stack, Text).contains(keyword)
                )
            )
        
        if category_id:
            filters.append(Product.category_id == category_id)
        
        if min_price is not None:
            filters.append(Product.price >= int(min_price * 100))
        
        if max_price is not None:
            filters.append(Product.price <= int(max_price * 100))
        
        if difficulty:
            filters.append(Product.difficulty == ProductDifficulty(difficulty))
        
        if status:
            filters.append(Product.status == ProductStatus(status))
        else:
            # 默认只显示已发布的商品
            filters.append(Product.status == ProductStatus.PUBLISHED)
        
        if seller_id:
            filters.append(Product.seller_id == seller_id)
        
        if tech_stack:
            # 产地与风味标签匹配（底层字段名为 tech_stack，保持接口兼容）
            for tech in tech_stack:
                filters.append(Product.tech_stack.contains(tech))
        
        if filters:
            query = query.where(and_(*filters))
        
        # 排序
        if sort_by == "price":
            query = query.order_by(Product.price.desc() if order == "desc" else Product.price.asc())
        elif sort_by == "sales":
            query = query.order_by(Product.sales_count.desc() if order == "desc" else Product.sales_count.asc())
        elif sort_by == "rating":
            query = query.order_by(Product.rating.desc() if order == "desc" else Product.rating.asc())
        else:
            query = query.order_by(Product.created_at.desc() if order == "desc" else Product.created_at.asc())
        
        # 计算总数
        count_query = select(func.count()).select_from(Product)
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total_result = self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = self.db.execute(query)
        products = result.scalars().all()
        
        return {
            "products": [self._product_to_dict(p, simple=True) for p in products],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    def add_product_image(
        self,
        product_id: str,
        image_url: str,
        sort_order: int = 0
    ) -> ProductImage:
        """添加商品图片"""
        image = ProductImage(
            id=str(uuid.uuid4()),
            product_id=product_id,
            image_url=image_url,
            sort_order=sort_order
        )
        
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        
        return image
    
    def add_product_file(
        self,
        product_id: str,
        file_name: str,
        file_type: str,
        file_path: str,
        file_size: int,
        description: Optional[str] = None
    ) -> ProductFile:
        """添加商品文件"""
        file = ProductFile(
            id=str(uuid.uuid4()),
            product_id=product_id,
            file_name=file_name,
            file_type=file_type,
            file_path=file_path,
            file_size=file_size,
            description=description
        )
        
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)
        
        return file
    
    def _product_to_dict(self, product: Product, simple: bool = False) -> Dict[str, Any]:
        """将商品对象转换为字典"""
        data = {
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": product.price / 100,  # 转换为元
            "original_price": product.original_price / 100 if product.original_price else None,
            "cover_image": product.cover_image,
            "tech_stack": product.tech_stack,
            "difficulty": product.difficulty.value,
            "status": product.status.value,
            "view_count": product.view_count,
            "sales_count": product.sales_count,
            "rating": product.rating / 100 if product.rating else 0,  # 转换为小数
            "review_count": product.review_count,
            "created_at": product.created_at.isoformat() if product.created_at else None,
        }
        
        if hasattr(product, 'seller') and product.seller:
            data["seller"] = {
                "id": product.seller.id,
                "username": product.seller.username
            }
        
        if hasattr(product, 'category') and product.category:
            data["category"] = {
                "id": product.category.id,
                "name": product.category.name
            }
        
        if not simple:
            data["demo_video"] = product.demo_video
            data["updated_at"] = product.updated_at.isoformat() if product.updated_at else None
            
            if hasattr(product, 'images'):
                data["images"] = [
                    {
                        "id": img.id,
                        "url": img.image_url,
                        "sort_order": img.sort_order
                    }
                    for img in sorted(product.images, key=lambda x: x.sort_order)
                ]
            
            if hasattr(product, 'files'):
                data["files"] = [
                    {
                        "id": f.id,
                        "name": f.file_name,
                        "type": f.file_type,
                        "size": f.file_size,
                        "description": f.description
                    }
                    for f in product.files
                ]
        
        return data


class CategoryService:
    """分类服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_category(
        self,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        sort_order: int = 0
    ) -> Category:
        """创建分类"""
        category = Category(
            id=str(uuid.uuid4()),
            name=name,
            parent_id=parent_id,
            description=description,
            icon=icon,
            sort_order=sort_order
        )
        
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        
        return category
    
    def get_categories(
        self,
        parent_id: Optional[str] = None,
        include_children: bool = False
    ) -> List[Dict[str, Any]]:
        """获取分类列表"""
        query = select(Category).order_by(Category.sort_order, Category.name)
        
        if parent_id is not None:
            query = query.where(Category.parent_id == parent_id)
        elif not include_children:
            query = query.where(Category.parent_id.is_(None))
        
        result = self.db.execute(query)
        categories = result.scalars().all()
        
        return [self._category_to_dict(c) for c in categories]
    
    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """获取分类详情"""
        result = self.db.execute(
            select(Category)
            .options(joinedload(Category.children))
            .where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            return None
        
        return self._category_to_dict(category, include_children=True)
    
    def _category_to_dict(self, category: Category, include_children: bool = False) -> Dict[str, Any]:
        """将分类对象转换为字典"""
        data = {
            "id": category.id,
            "name": category.name,
            "parent_id": category.parent_id,
            "description": category.description,
            "icon": category.icon,
            "sort_order": category.sort_order,
            "created_at": category.created_at.isoformat() if category.created_at else None
        }
        
        if include_children and hasattr(category, 'children'):
            data["children"] = [
                self._category_to_dict(c)
                for c in sorted(category.children, key=lambda x: x.sort_order)
            ]
        
        return data
