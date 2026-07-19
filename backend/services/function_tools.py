"""
Function Calling工具系统
让AI能够主动调用数据库查询和业务功能
"""
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ==================== LangChain @tool 装饰器工具定义 ====================


@tool
def query_order(order_no: str) -> dict:
    """查询订单详情和状态。可以通过订单号查询订单信息、商品列表、支付状态等。

    Args:
        order_no: 订单号，格式如：ORD20240207123456
    """
    from database.connection import get_db_context
    from services.order_service import OrderService

    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_no(order_no)

        if not order:
            return {
                "success": False,
                "error": "订单不存在",
                "order_no": order_no
            }

        return {
            "success": True,
            "order_no": order["order_no"],
            "status": order["status"],
            "total_amount": float(order["total_amount"]),
            "created_at": str(order["created_at"]),
            "items": order.get("items", []),
            "buyer_name": order.get("buyer_name", ""),
            "buyer_phone": order.get("buyer_phone", "")
        }


@tool
def search_products(keyword: str, max_price: float | None = None,
                    difficulty: str | None = None,
                    tech_stack: list[str] | None = None) -> dict:
    """搜索茶叶商品。支持关键词、价格、口感浓度及风味标签筛选。

    Args:
        keyword: 搜索关键词，如：龙井、乌龙茶、花香、送礼
        max_price: 最高价格（元）
        difficulty: 口感浓度：easy(清新)、medium(醇香)、hard(浓醇)
        tech_stack: 风味标签列表，如：['花香', '鲜爽', '福建安溪']（内部兼容字段名）
    """
    from database.connection import get_db_context
    from services.product_service import ProductService

    with get_db_context() as db:
        product_service = ProductService(db)

        # 构建搜索参数
        filters = {
            "keyword": keyword,
            "status": "published",
            "page": 1,
            "page_size": 5
        }

        if max_price:
            filters["max_price"] = max_price
        if difficulty:
            filters["difficulty"] = difficulty
        if tech_stack:
            filters["tech_stack"] = tech_stack

        result = product_service.search_products(**filters)
        products = result.get("products", [])

        return {
            "success": True,
            "total": len(products),
            "products": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "price": float(p["price"]),
                    "rating": float(p["rating"]),
                    "sales_count": p["sales_count"],
                    "tech_stack": p.get("tech_stack", []),
                    "difficulty": p.get("difficulty", ""),
                    "description": p.get("description", "")[:200]
                }
                for p in products
            ]
        }


@tool
def get_user_info(user_id: str) -> dict:
    """获取用户基本信息，包括用户名、邮箱、注册时间等。

    Args:
        user_id: 用户ID
    """
    from database.connection import get_db_context
    from database.models import User
    from sqlalchemy import select

    with get_db_context() as db:
        result = db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "用户不存在"
            }

        return {
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": str(user.created_at)
        }


@tool
def check_inventory(product_id: str) -> dict:
    """检查商品库存状态。返回商品是否有货、库存数量等信息。

    Args:
        product_id: 商品ID
    """
    from database.connection import get_db_context
    from services.product_service import ProductService

    with get_db_context() as db:
        product_service = ProductService(db)
        product = product_service.get_product(product_id)

        if not product:
            return {
                "success": False,
                "error": "商品不存在"
            }

        # 茶叶为实物商品，当前演示环境使用默认库存
        # 这里简化处理，实际可以根据业务需求调整
        stock = product.get("stock", 999)
        in_stock = stock > 0

        return {
            "success": True,
            "product_id": product_id,
            "product_title": product["title"],
            "in_stock": in_stock,
            "stock": stock,
            "status": product["status"]
        }


@tool
def get_logistics(order_no: str) -> dict:
    """查询订单的物流信息。返回物流状态、物流公司、快递单号等。用于查询茶叶订单的备货、发货与签收状态。

    Args:
        order_no: 订单号
    """
    from database.connection import get_db_context
    from services.order_service import OrderService

    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_no(order_no)

        if not order:
            return {
                "success": False,
                "error": "订单不存在"
            }

        # 根据订单状态返回茶品备货、配送或签收说明
        # 当前订单模型复用既有状态字段
        status = order["status"]

        if status == "delivered":
            return {
                "success": True,
                "order_no": order_no,
                "delivery_type": "physical",
                "message": "茶品订单已签收，如商品或包装有问题请及时申请售后。",
                "status": "已签收"
            }
        elif status == "paid":
            return {
                "success": True,
                "order_no": order_no,
                "delivery_type": "physical",
                "message": "订单已支付，茶坊正在备货并安排发货。",
                "status": "备货中"
            }
        else:
            return {
                "success": True,
                "order_no": order_no,
                "delivery_type": "physical",
                "message": f"订单状态：{status}",
                "status": status
            }


@tool
def calculate_price(product_ids: list[str], coupon_code: str = None) -> dict:
    """计算商品总价。支持多个商品、优惠券等。返回原价、折扣、最终价格等信息。

    Args:
        product_ids: 商品ID列表
        coupon_code: 优惠券代码（可选）
    """
    from database.connection import get_db_context
    from services.product_service import ProductService

    with get_db_context() as db:
        product_service = ProductService(db)

        total_price = 0.0
        products_info = []

        for product_id in product_ids:
            product = product_service.get_product(product_id)
            if product:
                price = float(product["price"])
                total_price += price
                products_info.append({
                    "id": product_id,
                    "title": product["title"],
                    "price": price
                })

        # 简化处理：暂不实现优惠券逻辑
        discount = 0.0
        if coupon_code:
            # TODO: 实现优惠券验证和折扣计算
            pass

        final_price = total_price - discount

        return {
            "success": True,
            "products": products_info,
            "original_price": total_price,
            "discount": discount,
            "final_price": final_price,
            "coupon_applied": coupon_code if discount > 0 else None
        }


@tool
def get_personalized_recommendations(user_id: str, limit: int = 5) -> dict:
    """基于用户浏览历史获取个性化商品推荐。该工具会分析用户近期浏览过的商品，根据茶类、产地与风味标签偏好推荐相关茶品。

    Args:
        user_id: 用户的唯一标识ID
        limit: 返回推荐商品数量，默认5个
    """
    print(f"🎯 [get_personalized_recommendations] user_id={user_id}, limit={limit}", flush=True)
    from database.connection import get_db_context
    from services.recommendation_service import RecommendationService

    with get_db_context() as db:
        rec_service = RecommendationService(db)
        
        recommendations = rec_service.get_personalized_recommendations(
            user_id=user_id,
            limit=limit
        )
        
        if not recommendations:
            popular = rec_service.get_popular_products(limit=limit)
            return {
                "success": True,
                "message": "暂无个性化推荐，为您推荐热门商品",
                "products": popular,
                "is_popular": True
            }
        
        return {
            "success": True,
            "message": "为您推荐以下商品",
            "products": recommendations,
            "is_personalized": True
        }


# ==================== LangChain 工具列表 ====================

all_tools = [query_order, search_products, get_user_info,
             check_inventory, get_logistics, calculate_price,
             get_personalized_recommendations]


# ==================== AI 选茶顾问工具（接口名保持兼容） ====================

@tool
def search_projects(keyword: str, max_price: float | None = None,
                    user_level: str | None = None) -> dict:
    """搜索茶叶商品。工具名保持兼容，支持按关键词、预算与口感浓度搜索。

    Args:
        keyword: 搜索关键词，如：西湖龙井、花香、乌龙茶、送礼
        max_price: 最高预算（元），如：500
        user_level: 口感偏好兼容参数：beginner(清新)、intermediate(醇香)、advanced(浓醇)
    """
    from database.connection import get_db_context
    from services.product_service import ProductService

    with get_db_context() as db:
        product_service = ProductService(db)

        filters = {
            "keyword": keyword,
            "status": "published",
            "page": 1,
            "page_size": 10
        }

        if max_price:
            filters["max_price"] = max_price

        if user_level:
            level_map = {
                "beginner": "easy",
                "intermediate": "medium",
                "advanced": "hard"
            }
            filters["difficulty"] = level_map.get(user_level)

        result = product_service.search_products(**filters)
        products = result.get("products", [])

        return {
            "success": True,
            "total": len(products),
            "keyword": keyword,
            "budget": max_price,
            "user_level": user_level,
            "projects": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "price": float(p["price"]),
                    "rating": float(p.get("rating", 0)),
                    "sales_count": p.get("sales_count", 0),
                    "tech_stack": p.get("tech_stack", []),
                    "difficulty": p.get("difficulty", ""),
                    "description": p.get("description", "")[:200]
                }
                for p in products
            ]
        }


@tool
def get_project_detail(project_id: str) -> dict:
    """获取茶叶商品详情，包括产地风味标签、口感浓度、价格与商品描述。

    Args:
        project_id: 茶品ID（兼容现有参数名）
    """
    from database.connection import get_db_context
    from services.product_service import ProductService

    with get_db_context() as db:
        product_service = ProductService(db)
        product = product_service.get_product(project_id)

        if not product:
            return {
                "success": False,
                "error": "茶品不存在"
            }

        return {
            "success": True,
            "project_id": project_id,
            "title": product["title"],
            "price": float(product["price"]),
            "rating": float(product.get("rating", 0)),
            "sales_count": product.get("sales_count", 0),
            "tech_stack": product.get("tech_stack", []),
            "difficulty": product.get("difficulty", ""),
            "description": product.get("description", ""),
            "features": product.get("features", []),
            "tea_tags": product.get("tech_stack", []),
            "taste_profile": product.get("difficulty", ""),
            "category": product.get("category", {})
        }


@tool
def compare_projects(project_ids: list[str]) -> dict:
    """对比多款茶叶的风味标签、口感浓度与价格，帮助顾客选择。

    Args:
        project_ids: 茶品ID列表（兼容现有参数名），如：["id1", "id2", "id3"]
    """
    from database.connection import get_db_context
    from services.product_service import ProductService

    with get_db_context() as db:
        product_service = ProductService(db)

        projects = []
        for pid in project_ids:
            product = product_service.get_product(pid)
            if product:
                projects.append({
                    "id": pid,
                    "title": product["title"],
                    "price": float(product["price"]),
                    "rating": float(product.get("rating", 0)),
                    "tech_stack": product.get("tech_stack", []),
                    "difficulty": product.get("difficulty", ""),
                    "sales_count": product.get("sales_count", 0),
                    "description": product.get("description", "")[:150]
                })

        if not projects:
            return {
                "success": False,
                "error": "未找到任何茶品"
            }

        min_price = min(p["price"] for p in projects)
        max_price = max(p["price"] for p in projects)

        return {
            "success": True,
            "total": len(projects),
            "price_range": {"min": min_price, "max": max_price},
            "projects": projects
        }


@tool
def check_tech_stack_match(project_id: str, user_skills: list[str]) -> dict:
    """匹配顾客风味偏好与茶品标签，工具名和参数名保持向后兼容。

    Args:
        project_id: 茶品ID
        user_skills: 顾客偏好标签，如：["花香", "清新", "乌龙茶"]
    """
    from database.connection import get_db_context
    from services.product_service import ProductService

    with get_db_context() as db:
        product = ProductService(db).get_product(project_id)
        if not product:
            return {"success": False, "error": "茶品不存在"}

        product_tags = [tag.strip().lower() for tag in product.get("tech_stack", [])]
        preference_tags = [tag.strip().lower() for tag in user_skills]
        matched = [
            tag for tag in product_tags
            if any(preference in tag or tag in preference for preference in preference_tags)
        ]
        match_rate = len(matched) / len(preference_tags) if preference_tags else 0

        if match_rate >= 0.7:
            level = "高度匹配"
        elif match_rate >= 0.4:
            level = "部分匹配"
        else:
            level = "可进一步了解"

        return {
            "success": True,
            "project_id": project_id,
            "title": product["title"],
            "match_level": level,
            "match_rate": round(match_rate * 100, 1),
            "matched_tags": matched,
            "product_tags": product_tags,
            "suggestion": "这款茶与您的偏好较匹配" if matched else "可以补充喜欢的香型、口感或茶类，我再帮您判断",
        }


topic_advisor_tools = [search_projects, get_project_detail, compare_projects, check_tech_stack_match, get_personalized_recommendations]
