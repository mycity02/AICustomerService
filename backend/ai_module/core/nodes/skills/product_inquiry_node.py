"""商品目录查询节点。"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List


from ai_module.core.nodes.common.base import BaseNode
from ai_module.core.state import ConversationState
from ai_module.core.tea_preferences import (
    build_preference_search_keyword,
    extract_tea_preferences,
    has_tea_preference_slots,
)

logger = logging.getLogger(__name__)


def _get_search_products_tool():
    """延迟加载数据库工具，避免节点导入时绑定运行环境。"""
    from services.function_tools import search_products

    return search_products


_CATALOG_QUERY_RE = re.compile(
    r"(商城|逛(?:一逛|逛)?|浏览.*(?:商品|茶品)|看看.*(?:商品|茶品)|"
    r"(?:有|卖)(?:哪些|什么).*(?:商品|茶品|茶叶|茶)|"
    r"(?:商品|茶品|茶叶|茶).*(?:有哪些|有什么)|"
    r"想(?:买|购买|要).*(?:商品|茶品|茶叶)|在售(?:商品|茶品|茶叶))",
    re.IGNORECASE,
)


class ProductInquiryNode(BaseNode):
    """查询真实在售茶品，并生成可点击的商品卡片。"""

    @staticmethod
    def _as_float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _as_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _normalize_products(products: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        seen_ids = set()
        for product in products:
            if not isinstance(product, dict):
                continue
            product_id = product.get("id") or product.get("product_id")
            title = (product.get("title") or "").strip()
            if not product_id or not title or product_id in seen_ids:
                continue
            seen_ids.add(product_id)
            tags = product.get("tech_stack") or []
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            normalized.append(
                {
                    "id": product_id,
                    "title": title,
                    "price": ProductInquiryNode._as_float(product.get("price")),
                    "rating": ProductInquiryNode._as_float(product.get("rating")),
                    "sales_count": ProductInquiryNode._as_int(product.get("sales_count")),
                    "tech_stack": list(tags) if isinstance(tags, (list, tuple)) else [],
                    "description": (product.get("description") or "").strip(),
                }
            )
        return normalized

    def _products_from_tool_result(self, state: ConversationState) -> List[Dict[str, Any]]:
        raw_results = state.get("tool_result") or []
        if isinstance(raw_results, dict):
            raw_results = [raw_results]

        products = []
        for entry in raw_results:
            if not isinstance(entry, dict):
                continue
            result = entry.get("result") if "result" in entry else entry
            if not isinstance(result, dict) or result.get("success") is False:
                continue
            candidates = result.get("products") or result.get("projects") or []
            if isinstance(candidates, list):
                products.extend(candidates)
        return self._normalize_products(products)

    @staticmethod
    def _merged_preference_slots(state: ConversationState, message: str) -> Dict[str, Any]:
        slots = dict((state.get("active_task") or {}).get("slots") or {})
        slots.update(state.get("slot_updates") or {})
        extracted = extract_tea_preferences(message)
        slots.update(extracted)
        if extracted:
            updates = dict(state.get("slot_updates") or {})
            updates.update(extracted)
            state["slot_updates"] = updates
        return slots

    def _load_catalog(
        self,
        state: ConversationState,
        arguments: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        arguments = arguments or {"keyword": ""}
        try:
            result = _get_search_products_tool().invoke(arguments)
        except Exception as exc:
            logger.warning("Catalog lookup failed: %s", exc)
            return []

        previous_results = state.get("tool_result") or []
        if isinstance(previous_results, dict):
            previous_results = [previous_results]
        state["tool_result"] = list(previous_results) + [
            {"tool": "search_products", "result": result}
        ]
        state["tool_used"] = state.get("tool_used") or "search_products"
        candidates = result.get("products", []) if isinstance(result, dict) else []
        return self._normalize_products(candidates)

    @staticmethod
    def _build_product_actions(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        actions = []
        for product in products[:5]:
            actions.append(
                {
                    "type": "product",
                    "data": {
                        "product_id": product["id"],
                        "title": product["title"],
                        "price": product["price"],
                        "rating": product["rating"],
                        "sales_count": product["sales_count"],
                        "tech_stack": product["tech_stack"],
                        "description": product["description"][:150],
                    },
                }
            )
        actions.append(
            {
                "type": "button",
                "label": "查看全部茶品",
                "action": "navigate",
                "data": {"path": "/products"},
                "icon": "🏠",
                "color": "primary",
            }
        )
        return actions

    @staticmethod
    def _build_catalog_response(products: List[Dict[str, Any]]) -> str:
        lines = [f"商城里有多类在售茶品，先给您展示这 {len(products[:5])} 款："]
        for index, product in enumerate(products[:5], start=1):
            tags = "、".join(product["tech_stack"][:3])
            details = [f"¥{product['price']:.2f}"]
            if product["rating"]:
                details.append(f"评分 {product['rating']:.1f}")
            if tags:
                details.append(tags)
            lines.append(f"{index}. **{product['title']}**｜{'｜'.join(details)}")
        lines.extend(
            [
                "",
                "可以直接点击商品卡片查看详情。告诉我预算、想要的茶类，以及自饮还是送礼，我还能继续帮您筛选。",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _build_preference_response(
        products: List[Dict[str, Any]],
        slots: Dict[str, Any],
    ) -> str:
        keyword = build_preference_search_keyword(slots)
        lines = [f"按您喜欢的“{keyword}”，目前找到这 {len(products[:5])} 款在售茶品："]
        for index, product in enumerate(products[:5], start=1):
            tags = "、".join(product["tech_stack"][:3])
            details = [f"¥{product['price']:.2f}"]
            if product["rating"]:
                details.append(f"评分 {product['rating']:.1f}")
            if tags:
                details.append(tags)
            lines.append(f"{index}. **{product['title']}**｜{'｜'.join(details)}")
        lines.extend(
            [
                "",
                "可以直接点击商品卡片查看详情；如果您补充预算和口感浓淡，我还能继续缩小范围。",
            ]
        )
        return "\n".join(lines)

    def execute(self, state: ConversationState) -> ConversationState:
        """Use real catalog data for both broad browsing and preference queries."""
        message = (state.get("user_message") or "").strip()
        products = self._products_from_tool_result(state)
        is_catalog_query = bool(_CATALOG_QUERY_RE.search(message))
        preference_slots = self._merged_preference_slots(state, message)
        preference_keyword = build_preference_search_keyword(preference_slots)
        is_preference_query = bool(
            preference_keyword and has_tea_preference_slots(preference_slots)
        )

        if not products and (is_catalog_query or is_preference_query):
            arguments: Dict[str, Any] = {
                "keyword": preference_keyword if is_preference_query else ""
            }
            budget = preference_slots.get("budget_max")
            if budget is not None:
                arguments["max_price"] = budget
            products = self._load_catalog(state, arguments)

        if products:
            state["response"] = (
                self._build_preference_response(products, preference_slots)
                if is_preference_query
                else self._build_catalog_response(products)
            )
            state["quick_actions"] = self._build_product_actions(products)
            state["recommended_products"] = [product["id"] for product in products[:5]]
            return state

        if is_preference_query:
            state["response"] = (
                f"目前在售商品中没有检索到明确标注“{preference_keyword}”的茶品。"
                "您可以换一个相近香型，或者告诉我预算和茶类，我再继续筛选。"
            )
        elif is_catalog_query:
            state["response"] = (
                "暂时没有查询到可展示的在售茶品。您可以打开商城查看最新上架内容，"
                "也可以告诉我预算和口味偏好，我再为您精确查找。"
            )
        else:
            state["response"] = (
                "我可以帮您查询茶品的产地、香型、口感、冲泡方式和保质期。"
                "请告诉我具体茶名，或者直接说预算、茶类和饮用场景。"
            )

        state["quick_actions"] = [
            {
                "type": "button",
                "label": "浏览全部茶品",
                "action": "navigate",
                "data": {"path": "/products"},
                "icon": "🏠",
                "color": "primary",
            },
            {
                "type": "button",
                "label": "帮我选茶",
                "action": "send_question",
                "data": {"question": "帮我推荐一款适合我的茶"},
                "icon": "🍵",
            },
        ]
        state["recommended_products"] = None
        return state