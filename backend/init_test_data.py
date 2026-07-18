"""
初始化测试数据脚本
"""
import uuid
from sqlalchemy.orm import Session
from database.connection import engine, Base
from database.models import User, Category, Product, ProductDifficulty, ProductStatus
from services.auth_service import AuthService
from datetime import datetime
from migrate_tea_catalog import CATEGORY_SPECS, TEA_PRODUCTS

auth_service = AuthService()


def init_database():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功")


def create_test_users(session: Session):
    """创建测试用户"""
    users_data = [
        {"username": "admin", "password": "admin123", "email": "admin@example.com", "role": "admin"},
        {"username": "buyer1", "password": "buyer123", "email": "buyer1@example.com", "role": "user"},
        {"username": "seller1", "password": "seller123", "email": "seller1@example.com", "role": "user"},
        {"username": "seller2", "password": "seller123", "email": "seller2@example.com", "role": "user"},
    ]
    
    created_users = {}
    for user_data in users_data:
        # 检查用户是否已存在
        from sqlalchemy import select
        result = session.execute(
            select(User).where(User.username == user_data["username"])
        )
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            password_hash = auth_service.hash_password(user_data["password"])
            user = User(
                id=str(uuid.uuid4()),
                username=user_data["username"],
                password_hash=password_hash,
                email=user_data["email"],
                role=user_data["role"],
                is_active=True
            )
            session.add(user)
            created_users[user_data["username"]] = user
            print(f"✅ 创建用户: {user_data['username']}")
        else:
            created_users[user_data["username"]] = existing_user
            print(f"ℹ️  用户已存在: {user_data['username']}")
    
    session.commit()
    return created_users


def create_test_categories(session: Session):
    """创建测试分类"""
    categories_data = [
        {
            "name": name,
            "description": description,
            "icon": icon,
            "sort_order": sort_order,
        }
        for name, description, icon, sort_order in CATEGORY_SPECS
    ]

    created_categories = {}
    for cat_data in categories_data:
        from sqlalchemy import select
        result = session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing_cat = result.scalar_one_or_none()
        
        if not existing_cat:
            category = Category(
                id=str(uuid.uuid4()),
                name=cat_data["name"],
                description=cat_data["description"],
                icon=cat_data["icon"],
                sort_order=cat_data["sort_order"]
            )
            session.add(category)
            created_categories[cat_data["name"]] = category
            print(f"✅ 创建分类: {cat_data['name']}")
        else:
            created_categories[cat_data["name"]] = existing_cat
            print(f"ℹ️  分类已存在: {cat_data['name']}")
    
    session.commit()
    return created_categories


def create_test_products(session: Session, users: dict, categories: dict):
    """创建测试商品"""
    sellers = ["seller1", "seller1", "seller2", "seller2", "seller1", "seller1", "seller2", "seller1"]
    products_data = [
        {
            "title": spec["title"],
            "description": spec["description"],
            "price": spec["price"],
            "original_price": spec["original_price"],
            "cover_image": None,
            "tech_stack": spec["tags"],
            "difficulty": spec["taste"],
            "status": ProductStatus.PUBLISHED,
            "seller": sellers[index],
            "category": spec["category"],
            "view_count": spec["view_count"],
            "sales_count": spec["sales_count"],
            "rating": spec["rating"],
            "review_count": spec["review_count"],
        }
        for index, spec in enumerate(TEA_PRODUCTS)
    ]

    for prod_data in products_data:
        from sqlalchemy import select
        result = session.execute(
            select(Product).where(Product.title == prod_data["title"])
        )
        existing_prod = result.scalar_one_or_none()
        
        if not existing_prod:
            product = Product(
                id=str(uuid.uuid4()),
                seller_id=users[prod_data["seller"]].id,
                category_id=categories[prod_data["category"]].id,
                title=prod_data["title"],
                description=prod_data["description"],
                price=prod_data["price"],
                original_price=prod_data["original_price"],
                cover_image=prod_data["cover_image"],
                tech_stack=prod_data["tech_stack"],
                difficulty=prod_data["difficulty"],
                status=prod_data["status"],
                view_count=prod_data["view_count"],
                sales_count=prod_data["sales_count"],
                rating=prod_data["rating"],
                review_count=prod_data["review_count"]
            )
            session.add(product)
            print(f"✅ 创建商品: {prod_data['title']}")
        else:
            print(f"ℹ️  商品已存在: {prod_data['title']}")
    
    session.commit()


def main():
    """主函数"""
    print("开始初始化数据库...")
    
    # 初始化数据库表
    init_database()
    
    # 创建会话
    from database.connection import db_session
    with db_session() as session:
        # 创建测试用户
        users = create_test_users(session)
        
        # 创建测试分类
        categories = create_test_categories(session)
        
        # 创建测试商品
        create_test_products(session, users, categories)
    
    print("\n✅ 所有测试数据初始化完成！")
    print("\n可用的测试账户：")
    print("  管理员: admin / admin123")
    print("  买家: buyer1 / buyer123")
    print("  卖家: seller1 / seller123")
    print("  卖家: seller2 / seller123")


if __name__ == "__main__":
    main()
