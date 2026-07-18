"""
电商业务适配器
适配电商类业务系统（当前默认业务为茶叶零售）
"""
from typing import Dict, Any, List, Optional
from .base import BusinessAdapter


class EcommerceAdapter(BusinessAdapter):
    """电商业务适配器"""
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        # 如果配置了外部API，调用外部系统
        if self.api_base_url:
            try:
                response = self.call_business_api(
                    f"/api/users/{user_id}",
                    method="GET"
                )
                return self._normalize_user_info(response)
            except Exception as e:
                print(f"调用外部用户API失败: {e}")
        
        # 否则使用本地数据库
        from database.connection import get_db_context
        from database.models import User
        from sqlalchemy import select
        
        with get_db_context() as db:
            result = db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {}
            
            return {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "vip_level": 0,  # 可扩展
                "extra": {}
            }
    
    def query_orders(self, user_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """查询订单"""
        if self.api_base_url:
            try:
                params = {"user_id": user_id}
                if filters:
                    params.update(filters)
                
                response = self.call_business_api(
                    "/api/orders",
                    method="GET",
                    params=params
                )
                return [self._normalize_order(order) for order in response.get("orders", [])]
            except Exception as e:
                print(f"调用外部订单API失败: {e}")
        
        # 使用本地数据库
        from database.connection import get_db_context
        from services.order_service import OrderService
        
        with get_db_context() as db:
            order_service = OrderService(db)
            result = order_service.list_orders(
                user_id=user_id,
                page=1,
                page_size=10
            )
            
            orders = result.get("items", [])
            return [self._normalize_order(order) for order in orders]

    def get_order_by_no(self, order_no: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Query a single order by order number."""
        if self.api_base_url:
            try:
                params = {"order_no": order_no}
                if user_id:
                    params["user_id"] = user_id

                response = self.call_business_api(
                    "/api/orders/detail",
                    method="GET",
                    params=params
                )
                if not response:
                    return None

                normalized = self._normalize_order(response)
                normalized["buyer_name"] = response.get("buyer_name", "")
                normalized["buyer_phone"] = response.get("buyer_phone", "")
                return normalized
            except Exception as e:
                print(f"调用外部订单详情 API 失败: {e}")

        from database.connection import get_db_context
        from services.order_service import OrderService

        with get_db_context() as db:
            order_service = OrderService(db)
            return order_service.get_order_by_no(order_no, user_id=user_id)
    
    def search_products(self, keyword: str, filters: Optional[Dict] = None) -> List[Dict]:
        """搜索商品"""
        if self.api_base_url:
            try:
                params = {"keyword": keyword}
                if filters:
                    params.update(filters)
                
                response = self.call_business_api(
                    "/api/products/search",
                    method="GET",
                    params=params
                )
                return [self._normalize_product(product) for product in response.get("products", [])]
            except Exception as e:
                print(f"调用外部商品API失败: {e}")
        
        # 使用本地数据库
        from database.connection import get_db_context
        from services.product_service import ProductService
        
        with get_db_context() as db:
            product_service = ProductService(db)
            result = product_service.search_products(
                keyword=keyword,
                status="published",
                page=1,
                page_size=10,
                **(filters or {})
            )
            
            products = result.get("products", [])
            return [self._normalize_product(product) for product in products]

    def get_personalized_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get personalized recommendations for the current user."""
        if self.api_base_url:
            try:
                response = self.call_business_api(
                    "/api/recommendations/personalized",
                    method="GET",
                    params={"user_id": user_id, "limit": limit}
                )
                return response.get("products", [])
            except Exception as e:
                print(f"调用外部推荐 API 失败: {e}")

        from database.connection import get_db_context
        from services.recommendation_service import RecommendationService

        with get_db_context() as db:
            recommendation_service = RecommendationService(db)
            return recommendation_service.get_personalized_recommendations(
                user_id=user_id,
                limit=limit
            )
    
    def create_ticket(self, user_id: str, ticket_data: Dict) -> Dict:
        """创建工单"""
        if self.api_base_url:
            try:
                data = {
                    "user_id": user_id,
                    **ticket_data
                }
                response = self.call_business_api(
                    "/api/tickets",
                    method="POST",
                    data=data
                )
                return self._normalize_ticket(response)
            except Exception as e:
                print(f"调用外部工单API失败: {e}")
        
        # 使用本地数据库
        from database.connection import get_db_context
        from services.ticket_service import TicketService
        from schemas import TicketCreate
        
        with get_db_context() as db:
            ticket_service = TicketService(db)
            ticket_create = TicketCreate(
                user_id=user_id,
                **ticket_data
            )
            ticket = ticket_service.create_ticket(ticket_create)
            
            return self._normalize_ticket(ticket)
    
    def _normalize_user_info(self, data: Dict) -> Dict[str, Any]:
        """标准化用户信息"""
        return {
            "user_id": data.get("id") or data.get("user_id"),
            "username": data.get("username", ""),
            "email": data.get("email", ""),
            "vip_level": data.get("vip_level", 0),
            "extra": {k: v for k, v in data.items() if k not in ["id", "user_id", "username", "email", "vip_level"]}
        }
    
    def _normalize_order(self, data: Dict) -> Dict[str, Any]:
        """标准化订单信息"""
        return {
            "order_id": data.get("id") or data.get("order_id"),
            "order_no": data.get("order_no", ""),
            "status": data.get("status", ""),
            "total_amount": float(data.get("total_amount", 0)),
            "created_at": str(data.get("created_at", "")),
            "items": data.get("items", [])
        }
    
    def _normalize_product(self, data: Dict) -> Dict[str, Any]:
        """标准化商品信息"""
        return {
            "product_id": data.get("id") or data.get("product_id"),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "price": float(data.get("price", 0)),
            "stock": int(data.get("stock", 0)),
            "rating": float(data.get("rating", 0)),
            "extra": {
                "tech_stack": data.get("tech_stack", []),
                "difficulty": data.get("difficulty", ""),
                "sales_count": data.get("sales_count", 0)
            }
        }
    
    def _normalize_ticket(self, data: Dict) -> Dict[str, Any]:
        """标准化工单信息"""
        return {
            "ticket_id": data.get("id") or data.get("ticket_id"),
            "ticket_no": data.get("ticket_no", ""),
            "status": data.get("status", ""),
            "created_at": str(data.get("created_at", ""))
        }
