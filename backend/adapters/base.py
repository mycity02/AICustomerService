"""
业务适配器基类
定义统一的业务系统接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BusinessAdapter(ABC):
    """业务适配器基类 - 所有业务适配器必须实现此接口"""
    
    def __init__(self, business_id: str, config: Dict[str, Any]):
        """
        初始化适配器
        
        Args:
            business_id: 业务标识
            config: 业务配置
        """
        self.business_id = business_id
        self.config = config
        self.api_base_url = config.get("api", {}).get("base_url", "")
        self.api_key = config.get("api", {}).get("api_key", "")
    
    @abstractmethod
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            标准化的用户信息
            {
                "user_id": str,
                "username": str,
                "email": str,
                "vip_level": int,
                "extra": dict
            }
        """
        pass
    
    @abstractmethod
    def query_orders(self, user_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        查询订单
        
        Args:
            user_id: 用户ID
            filters: 过滤条件
            
        Returns:
            标准化的订单列表
            [{
                "order_id": str,
                "order_no": str,
                "status": str,
                "total_amount": float,
                "created_at": str,
                "items": list
            }]
        """
        pass
    
    @abstractmethod
    def search_products(self, keyword: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        搜索商品
        
        Args:
            keyword: 搜索关键词
            filters: 过滤条件
            
        Returns:
            标准化的商品列表
            [{
                "product_id": str,
                "title": str,
                "description": str,
                "price": float,
                "stock": int,
                "rating": float,
                "extra": dict
            }]
        """
        pass
    
    @abstractmethod
    def create_ticket(self, user_id: str, ticket_data: Dict) -> Dict:
        """
        创建工单
        
        Args:
            user_id: 用户ID
            ticket_data: 工单数据
            
        Returns:
            创建的工单信息
            {
                "ticket_id": str,
                "ticket_no": str,
                "status": str,
                "created_at": str
            }
        """
        pass
    
    def get_business_config(self) -> Dict[str, Any]:
        """
        获取业务配置
        
        Returns:
            业务配置信息
        """
        return {
            "business_id": self.business_id,
            "business_name": self.config.get("business_name", ""),
            "business_type": self.config.get("business_type", ""),
            "features": self.config.get("features", {}),
            "custom_intents": self.config.get("custom_intents", [])
        }
    
    def call_business_api(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        调用业务系统API的通用方法
        
        Args:
            endpoint: API端点
            method: HTTP方法
            params: URL参数
            data: 请求体数据
            
        Returns:
            API响应
        """
        import httpx
        
        url = f"{self.api_base_url}{endpoint}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        with httpx.Client() as client:
            if method == "GET":
                response = client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = client.post(url, json=data, headers=headers)
            elif method == "PUT":
                response = client.put(url, json=data, headers=headers)
            elif method == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
