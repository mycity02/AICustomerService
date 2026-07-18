"""Order query workflow service helpers."""
from __future__ import annotations

import logging
import re

from .contracts import OrderQueryMode

logger = logging.getLogger(__name__)


class OrderQueryService:
    """Operational logic behind the order query workflow."""

    CANCEL_ORDER_KEYWORDS = (
        "取消订单",
        "取消这笔订单",
        "取消该订单",
        "不要这个订单",
        "不想要这个订单",
    )
    CART_QUERY_KEYWORDS = (
        "购物车",
        "购物袋",
        "购物清单",
        "购物车里",
        "加入购物车",
        "车里有",
    )

    STATUS_MAP = {
        "pending": "待支付",
        "paid": "已支付",
        "shipped": "已发货",
        "delivered": "已送达",
        "completed": "已完成",
        "cancelled": "已取消",
        "refunded": "已退款",
    }

    def resolve_mode(self, state) -> OrderQueryMode:
        order_no_pattern = r"ORD\d{14}[A-Z0-9]{6}"
        order_no_match = re.search(order_no_pattern, state["user_message"], re.IGNORECASE)
        if order_no_match:
            state["_order_query_order_no"] = order_no_match.group(0).upper()
            return OrderQueryMode.DETAIL
        return OrderQueryMode.LIST

    def is_cancel_order_request(self, user_message: str) -> bool:
        return any(keyword in user_message for keyword in self.CANCEL_ORDER_KEYWORDS)

    def is_cart_query_request(self, user_message: str) -> bool:
        return any(keyword in user_message for keyword in self.CART_QUERY_KEYWORDS)

    def build_order_quick_actions(self, target_order: dict, items: list, order_no: str) -> list:
        quick_actions = []
        order_status = target_order.get("status")

        if order_status == "shipped":
            quick_actions.append(
                {
                    "type": "button",
                    "label": "查看物流信息",
                    "action": "send_question",
                    "data": {"question": f"查看订单 {order_no} 的物流信息"},
                    "icon": "📦",
                }
            )
        elif order_status == "pending":
            quick_actions.extend(
                [
                    {
                        "type": "button",
                        "label": "去支付",
                        "action": "navigate",
                        "data": {"path": "/orders"},
                        "icon": "💳",
                    },
                    {
                        "type": "button",
                        "label": "取消订单",
                        "action": "cancel_order",
                        "data": {
                            "order_id": target_order.get("id"),
                            "order_no": order_no,
                        },
                        "icon": "✖️",
                    },
                ]
            )

        if order_status in ["paid", "delivered", "completed"]:
            action_label = "申请退款" if order_status == "paid" else "申请售后"
            action_icon = "💰" if order_status == "paid" else "🧾"
            quick_actions.append(
                {
                    "type": "button",
                    "label": action_label,
                    "action": "aftersales_flow",
                    "data": {
                        "step": "select_type",
                        "order_id": target_order.get("id"),
                        "order_no": order_no,
                        "status": order_status,
                        "product_name": items[0].get("product_title", "商品") if items else "商品",
                        "total_amount": target_order.get("total_amount", 0) / 100,
                        "items": items,
                    },
                    "icon": action_icon,
                }
            )

        quick_actions.extend(
            [
                {
                    "type": "button",
                    "label": "联系卖家",
                    "action": "send_question",
                    "data": {"question": "如何联系卖家?"},
                    "icon": "💬",
                },
                {
                    "type": "button",
                    "label": "查看其他订单",
                    "action": "open_order_selector",
                    "data": {},
                    "icon": "📋",
                },
            ]
        )

        return quick_actions

    def handle_order_detail(self, state):
        order_no = state.get("_order_query_order_no")
        user_message = state["user_message"].lower()

        from database.connection import get_db_context
        from services.order_service import OrderService

        with get_db_context() as db:
            order_service = OrderService(db)
            result = order_service.list_orders(
                user_id=state["user_id"],
                page=1,
                page_size=100,
            )
            orders = result.get("items", [])

            target_order = None
            for order in orders:
                if order.get("order_no") == order_no:
                    target_order = order
                    break

            if not target_order:
                state["response"] = f"抱歉，没有找到订单号 {order_no}。请确认订单号是否正确。"
                return state

            order_status = target_order.get("status")
            status_text = self.STATUS_MAP.get(order_status, "未知")
            total_amount = target_order.get("total_amount", 0) / 100
            created_at = target_order.get("created_at", "")
            items = target_order.get("items", [])
            product_info = "\n".join(
                [f"- {item.get('product_title', '商品')}" for item in items]
            ) if items else "- 商品"

            if self.is_cancel_order_request(user_message):
                try:
                    order_service.cancel_order(target_order.get("id"), state["user_id"])
                except ValueError as exc:
                    state["response"] = (
                        f"订单 {order_no} 当前状态为 {status_text}，暂时不能直接取消。\n\n"
                        f"原因：{str(exc)}"
                    )
                    state["quick_actions"] = self.build_order_quick_actions(target_order, items, order_no)
                    return state

                state["response"] = (
                    f"好的，订单 {order_no} 已为您取消。\n\n"
                    f"订单金额：¥{total_amount:.2f}\n"
                    f"商品清单：\n{product_info}\n\n"
                    "如果您还想继续选茶，我可以根据口味和预算为您推荐。"
                )
                state["quick_actions"] = [
                    {
                        "type": "button",
                        "label": "查看其他订单",
                        "action": "open_order_selector",
                        "data": {},
                        "icon": "📋",
                    },
                    {
                        "type": "button",
                        "label": "继续逛商品",
                        "action": "navigate",
                        "data": {"path": "/products"},
                        "icon": "🛍️",
                    },
                ]
                return state

            state["response"] = (
                f"好的，为您查询订单 {order_no}：\n"
                f"订单状态：{status_text}\n"
                f"订单金额：¥{total_amount:.2f}\n"
                f"下单时间：{created_at}\n"
                f"商品清单：\n{product_info}\n\n"
                "请问您需要什么帮助？"
            )
            state["quick_actions"] = self.build_order_quick_actions(target_order, items, order_no)
            return state

    def handle_list_orders(self, state):
        if self.is_cart_query_request(state["user_message"]):
            state["response"] = (
                "这句是在问购物车，不是订单。"
                "当前助手还不支持通过对话直接查询购物车内容，您可以先打开购物车页面查看。"
            )
            state["quick_actions"] = [
                {
                    "type": "button",
                    "label": "查看购物车",
                    "action": "navigate",
                    "data": {"path": "/cart"},
                    "icon": "🛒",
                    "color": "primary",
                },
                {
                    "type": "button",
                    "label": "查看我的订单",
                    "action": "send_question",
                    "data": {"question": "查看我的订单"},
                    "icon": "📦",
                },
            ]
            return state

        from database.connection import get_db_context
        from services.order_service import OrderService

        with get_db_context() as db:
            order_service = OrderService(db)
            result = order_service.list_orders(
                user_id=state["user_id"],
                page=1,
                page_size=10,
            )
            orders = result.get("items", [])

        if not orders:
            state["response"] = "您还没有订单记录。如果您想购买商品，可以前往商城首页浏览。"
            state["quick_actions"] = [
                {
                    "type": "button",
                    "label": "前往商城首页",
                    "action": "navigate",
                    "data": {"path": "/products"},
                    "icon": "🛍️",
                    "color": "primary",
                }
            ]
            return state

        state["response"] = f"您好！您有 {len(orders)} 个订单，请点击下方按钮选择您要咨询的订单："
        state["quick_actions"] = [
            {
                "type": "button",
                "label": "📋 选择订单",
                "action": "open_order_selector",
                "data": {},
                "icon": "📋",
            }
        ]
        logger.info("生成订单选择按钮")
        return state
