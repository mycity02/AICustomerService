"""
商品咨询节点
"""
import logging
from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState

logger = logging.getLogger(__name__)


class ProductInquiryNode(BaseNode):
    """商品咨询节点 - 引导用户去商城"""
    
    def execute(self, state: ConversationState) -> ConversationState:
        """执行商品咨询 - 引导用户去商城页面"""
        
        # 客服定位调整: 不在客服中推荐商品,引导用户去商城
        state["response"] = """您好！关于商品浏览和选购，建议您：

1. **访问商城首页** 🏠
   - 查看所有在售茶品
   - 按茶类、产地、香型、价格和评分筛选

2. **使用搜索功能** 🔍
   - 搜索喜欢的茶类或风味（如龙井、花香、醇厚等）
   - 查看详细的产地、工艺和冲泡说明

3. **查看商品详情** 📋
   - 完整的产地与风味说明
   - 包装规格与冲泡建议
   - 用户评价和评分

如果您在购买过程中遇到问题，或者对已购买的商品有疑问，我随时为您服务！"""
        
        # 生成快速操作按钮
        state["quick_actions"] = [
            {
                "type": "button",
                "label": "前往商城首页",
                "action": "navigate",
                "data": {"path": "/products"},
                "icon": "🏠",
                "color": "primary"
            },
            {
                "type": "button",
                "label": "查看我的订单",
                "action": "send_question",
                "data": {"question": "查看我的订单"},
                "icon": "📦"
            },
            {
                "type": "button",
                "label": "如何购买茶品？",
                "action": "send_question",
                "data": {"question": "如何购买茶品？"},
                "icon": "🛒"
            }
        ]
        
        return state
