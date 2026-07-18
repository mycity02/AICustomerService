"""
购买指导节点
"""
from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from langchain_core.prompts import ChatPromptTemplate


class PurchaseGuideNode(BaseNode):
    """购买指导节点"""
    
    def execute(self, state: ConversationState) -> ConversationState:
        """执行购买指导"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是购买指导专家。帮助用户了解购买流程。

平台购买流程：
1. 浏览茶品，选择适合自饮或礼赠的茶叶
2. 点击"加入购物车"或"立即购买"
3. 在购物车中确认商品和价格
4. 点击"去结算"，填写订单信息
5. 选择支付方式（支持支付宝、微信支付）
6. 完成支付后，茶坊会备货并安排物流发出
7. 确认收货后可以评价

支付方式：
- 支付宝
- 微信支付

退款政策：
- 订单发货前可以申请取消，审核通过后原路退款
- 签收后如有包装破损、错发或质量问题可申请售后
- 退款会在3-5个工作日内到账

要求：
1. 根据用户问题提供相应指导
2. 语言简洁明了
3. 如果用户遇到具体问题，建议创建工单"""),
            ("human", "用户问题：{question}\n\n请提供购买指导：")
        ])
        
        response = self.llm.invoke(prompt.format_messages(
            question=state["user_message"]
        ))
        
        state["response"] = response.content
        return state

    def execute_stream(self, state: ConversationState):
        """以流式方式执行购买指导，逐字输出结果。"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是购买指导专家。帮助用户了解购买流程。

平台购买流程：
1. 浏览茶品，选择适合自饮或礼赠的茶叶
2. 点击"加入购物车"或"立即购买"
3. 在购物车中确认商品和价格
4. 点击"去结算"，填写订单信息
5. 选择支付方式（支持支付宝、微信支付）
6. 完成支付后，茶坊会备货并安排物流发出
7. 确认收货后可以评价

支付方式：
- 支付宝
- 微信支付

退款政策：
- 订单发货前可以申请取消，审核通过后原路退款
- 签收后如有包装破损、错发或质量问题可申请售后
- 退款会在3-5个工作日内到账

要求：
1. 根据用户问题提供相应指导
2. 语言简洁明了
3. 如果用户遇到具体问题，建议创建工单"""),
            ("human", "用户问题：{question}\n\n请提供购买指导：")
        ])

        messages = prompt.format_messages(question=state["user_message"])

        full_response = ""
        for chunk in self.llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        state["response"] = full_response
