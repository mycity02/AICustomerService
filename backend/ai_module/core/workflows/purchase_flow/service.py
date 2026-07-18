"""Purchase flow service helpers."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class PurchaseFlowService:
    """Encapsulates business logic for each purchase flow step."""

    def _load_product_summary(self, product_id):
        from database.connection import get_db_context
        from services.product_service import ProductService

        with get_db_context() as db:
            product_service = ProductService(db)
            product = product_service.get_product(product_id)

        if not product:
            return None

        return {
            "id": product.get("id"),
            "title": product.get("title"),
            "price": product.get("price", 0),
            "tech_stack": product.get("tech_stack", []),
        }

    def get_available_coupons(self, user_id: str, order_amount: float):
        """获取用户可用优惠券。"""
        from database.connection import get_db_context
        from sqlalchemy import select
        from database.models import Coupon, UserCoupon

        with get_db_context() as db:
            stmt = select(UserCoupon, Coupon).join(
                Coupon, UserCoupon.coupon_id == Coupon.id
            ).where(
                UserCoupon.user_id == user_id,
                UserCoupon.status == "unused",
                Coupon.min_amount <= order_amount,
                Coupon.expire_date > datetime.now(),
            )
            result = db.execute(stmt)
            rows = result.all()

            coupons = []
            for _, coupon in rows:
                coupons.append(
                    {
                        "id": coupon.id,
                        "name": coupon.name,
                        "discount_amount": coupon.discount_amount,
                        "min_amount": coupon.min_amount,
                        "expire_date": coupon.expire_date.strftime("%Y-%m-%d") if coupon.expire_date else "",
                    }
                )

            return coupons

    def get_user_addresses(self, user_id: str):
        """获取用户收货地址。"""
        from database.connection import get_db_context
        from sqlalchemy import select
        from database.models import Address

        with get_db_context() as db:
            stmt = select(Address).where(
                Address.user_id == user_id
            ).order_by(Address.is_default.desc())
            result = db.execute(stmt)
            addresses = result.scalars().all()

            return [
                {
                    "id": address.id,
                    "contact": address.contact,
                    "phone": address.phone,
                    "province": address.province,
                    "city": address.city,
                    "district": address.district,
                    "detail": address.detail,
                    "full_address": f"{address.province}{address.city}{address.district}{address.detail}",
                }
                for address in addresses
            ]

    def _load_address_info(self, address_id):
        from database.connection import get_db_context
        from sqlalchemy import select
        from database.models import Address

        with get_db_context() as db:
            stmt = select(Address).where(Address.id == address_id)
            result = db.execute(stmt)
            address = result.scalar_one_or_none()

        if not address:
            return None

        return {
            "id": address.id,
            "contact": address.contact,
            "phone": address.phone,
            "full_address": f"{address.province}{address.city}{address.district}{address.detail}",
        }

    def handle_confirm_product(self, state, flow_data: dict):
        """步骤1: 确认商品。"""
        product_id = flow_data.get("product_id")

        if not product_id:
            state["response"] = "请先选择要购买的商品"
            return state

        product = self._load_product_summary(product_id)
        if not product:
            state["response"] = "商品不存在或已下架"
            return state

        state["purchase_flow"] = {
            **flow_data,
            "product": product,
            "step": "select_coupon",
        }

        coupons = self.get_available_coupons(state.get("user_id"), product.get("price", 0))

        if coupons:
            coupon_cards = []
            for coupon in coupons[:3]:
                coupon_cards.append(
                    {
                        "type": "coupon",
                        "data": {
                            "coupon_id": coupon["id"],
                            "name": coupon["name"],
                            "discount": coupon["discount_amount"],
                            "min_amount": coupon["min_amount"],
                            "expire_date": coupon["expire_date"],
                        },
                    }
                )

            state["response"] = (
                f"✅ 已确认商品：{product.get('title')}（¥{product.get('price', 0)}）\n\n"
                f"您有 {len(coupons)} 张可用优惠券："
            )
            state["quick_actions"] = coupon_cards + [
                {
                    "type": "button",
                    "label": "不使用优惠券",
                    "action": "purchase_flow",
                    "data": {
                        "step": "confirm_coupon",
                        "product_id": product_id,
                        "coupon_id": None,
                    },
                    "icon": "➡️",
                }
            ]
        else:
            state["response"] = (
                f"✅ 已确认商品：{product.get('title')}（¥{product.get('price', 0)}）\n\n"
                "暂无优惠券可用，是否确认收货地址？"
            )
            state["quick_actions"] = [
                {
                    "type": "button",
                    "label": "选择收货地址",
                    "action": "purchase_flow",
                    "data": {
                        "step": "select_address",
                        "product_id": product_id,
                        "coupon_id": None,
                    },
                    "icon": "📍",
                }
            ]

        return state

    def handle_select_coupon(self, state, flow_data: dict):
        """步骤2: 选择优惠券。"""
        return self.handle_confirm_product(state, {**flow_data, "step": "confirm_coupon"})

    def handle_confirm_coupon(self, state, flow_data: dict):
        """步骤2.1: 确认优惠券选择。"""
        product = flow_data.get("product", {})
        coupon_id = flow_data.get("coupon_id")

        from database.connection import get_db_context
        from sqlalchemy import select
        from database.models import Coupon

        coupon_info = None
        if coupon_id:
            with get_db_context() as db:
                stmt = select(Coupon).where(Coupon.id == coupon_id)
                result = db.execute(stmt)
                coupon = result.scalar_one_or_none()
                if coupon:
                    coupon_info = {
                        "id": coupon.id,
                        "name": coupon.name,
                        "discount": coupon.discount_amount / 100,
                    }

        product_price = product.get("price", 0)
        discount = coupon_info["discount"] if coupon_info else 0
        final_price = max(0, product_price - discount)

        state["purchase_flow"] = {
            **flow_data,
            "coupon": coupon_info,
            "final_price": final_price,
            "step": "select_address",
        }

        response = f"✅ 商品已确认：{product.get('title')}（¥{product_price}）\n"
        if coupon_info:
            response += f"✅ 优惠券：{coupon_info['name']}（-¥{discount}）\n"
        response += "\n请选择收货地址："

        addresses = self.get_user_addresses(state.get("user_id"))

        if addresses:
            address_cards = []
            for address in addresses[:3]:
                address_cards.append(
                    {
                        "type": "address",
                        "data": {
                            "address_id": address["id"],
                            "contact": address["contact"],
                            "phone": address["phone"],
                            "address": address["full_address"],
                            "product_id": flow_data.get("product_id"),
                            "coupon_id": coupon_id,
                            "final_price": final_price,
                        },
                    }
                )

            state["response"] = response
            state["quick_actions"] = address_cards + [
                {
                    "type": "button",
                    "label": "使用默认地址",
                    "action": "purchase_flow",
                    "data": {
                        "step": "confirm_address",
                        "product_id": flow_data.get("product_id"),
                        "coupon_id": coupon_id,
                        "address_id": addresses[0]["id"] if addresses else None,
                        "product": product,
                        "coupon": coupon_info,
                        "final_price": final_price,
                    },
                    "icon": "📍",
                }
            ]
        else:
            state["response"] = response + "\n\n您还没有收货地址，请先添加。"
            state["quick_actions"] = [
                {
                    "type": "button",
                    "label": "去添加地址",
                    "action": "navigate",
                    "data": {"path": "/profile/addresses"},
                    "icon": "➡️",
                }
            ]

        return state

    def handle_select_address(self, state, flow_data: dict):
        """步骤3: 选择地址。"""
        product = flow_data.get("product")
        product_id = flow_data.get("product_id")
        coupon = flow_data.get("coupon")
        coupon_id = flow_data.get("coupon_id")
        final_price = flow_data.get("final_price")

        if not product and product_id:
            product = self._load_product_summary(product_id)

        if final_price is None and product:
            final_price = product.get("price", 0)

        state["purchase_flow"] = {
            **flow_data,
            "product": product,
            "step": "select_address",
        }

        addresses = self.get_user_addresses(state.get("user_id"))
        response = "请选择收货地址："

        if addresses:
            address_cards = []
            for address in addresses[:3]:
                address_cards.append(
                    {
                        "type": "address",
                        "data": {
                            "address_id": address["id"],
                            "contact": address["contact"],
                            "phone": address["phone"],
                            "address": address["full_address"],
                            "product_id": product_id,
                            "coupon_id": coupon_id,
                            "final_price": final_price,
                        },
                    }
                )

            state["response"] = response
            state["quick_actions"] = address_cards + [
                {
                    "type": "button",
                    "label": "使用默认地址",
                    "action": "purchase_flow",
                    "data": {
                        "step": "confirm_address",
                        "product_id": product_id,
                        "coupon_id": coupon_id,
                        "address_id": addresses[0]["id"],
                        "product": product,
                        "coupon": coupon,
                        "final_price": final_price,
                    },
                    "icon": "📍",
                }
            ]
        else:
            state["response"] = response + "\n\n您还没有收货地址，请先添加。"
            state["quick_actions"] = [
                {
                    "type": "button",
                    "label": "去添加地址",
                    "action": "navigate",
                    "data": {"path": "/profile/addresses"},
                    "icon": "➡️",
                }
            ]

        return state

    def handle_confirm_address(self, state, flow_data: dict):
        """步骤3.1: 确认地址。"""
        product = flow_data.get("product", {})
        product_id = flow_data.get("product_id")
        coupon = flow_data.get("coupon")
        address_id = flow_data.get("address_id")

        if (not product or not product.get("title")) and product_id:
            product = self._load_product_summary(product_id)

        final_price = flow_data.get("final_price", product.get("price", 0))

        if not address_id:
            state["response"] = "请选择收货地址"
            return state

        address_info = self._load_address_info(address_id)
        if not address_info:
            state["response"] = "地址不存在"
            return state

        state["purchase_flow"] = {
            **flow_data,
            "address": address_info,
            "step": "order_confirm",
        }

        coupon_line = ""
        if coupon:
            coupon_line = f"优惠券：{coupon['name']}（-¥{coupon['discount']}）\n"

        state["response"] = (
            "🧾 订单确认\n\n"
            f"商品：{product.get('title')} x 1\n"
            f"原价：¥{product.get('price')}\n"
            f"{coupon_line}"
            f"实付：¥{final_price}\n"
            f"收货地址：{address_info['contact']} | {address_info['phone']} | {address_info['full_address']}\n\n"
            "请确认订单信息："
        )

        state["quick_actions"] = [
            {
                "type": "button",
                "label": "确认下单",
                "action": "purchase_flow",
                "data": {
                    "step": "payment",
                    "product_id": flow_data.get("product_id"),
                    "coupon_id": flow_data.get("coupon_id"),
                    "address_id": address_id,
                    "product": product,
                    "coupon": coupon,
                    "address": address_info,
                    "final_price": final_price,
                },
                "icon": "✅",
            },
            {
                "type": "button",
                "label": "修改信息",
                "action": "purchase_flow",
                "data": {
                    "step": "start",
                    "product_id": flow_data.get("product_id"),
                },
                "icon": "✏️",
            },
        ]

        return state

    def handle_order_confirm(self, state, flow_data: dict):
        """步骤4: 订单确认。"""
        return self.handle_confirm_address(state, {**flow_data, "step": "confirm_address"})

    def handle_payment(self, state, flow_data: dict):
        """步骤5: 支付。"""
        product = flow_data.get("product", {})
        product_id = flow_data.get("product_id")
        address = flow_data.get("address")
        address_id = flow_data.get("address_id")
        final_price = flow_data.get("final_price", 0)

        if (not product or not product.get("id")) and product_id:
            product = self._load_product_summary(product_id)
            if product and not final_price:
                final_price = product.get("price", 0)

        if (not address or not address.get("full_address")) and address_id:
            address = self._load_address_info(address_id)

        from database.connection import get_db_context
        from services.order_service import OrderService

        with get_db_context() as db:
            order_service = OrderService(db)
            order_result = order_service.create_order(
                buyer_id=state.get("user_id"),
                product_ids=[product.get("id")],
            )

            if order_result.get("id"):
                order_no = order_result.get("order_no", f"ORD{uuid.uuid4().hex[:12].upper()}")
                order_id = order_result.get("id")

                state["purchase_flow"] = {
                    **flow_data,
                    "order_id": order_id,
                    "order_no": order_no,
                    "step": "payment_done",
                }

                state["response"] = (
                    "🎀 订单已创建！\n\n"
                    f"订单号：{order_no}\n"
                    f"商品：{product.get('title')}\n"
                    f"实付金额：¥{final_price}\n"
                    f"收货地址：{address.get('full_address') if address else '未设置'}\n\n"
                    "请选择支付方式："
                )

                state["quick_actions"] = [
                    {
                        "type": "button",
                        "label": "微信支付",
                        "action": "purchase_flow",
                        "data": {
                            "step": "payment_done",
                            "order_id": order_id,
                            "order_no": order_no,
                            "payment_method": "wechat",
                            "final_price": final_price,
                        },
                        "icon": "💌",
                    },
                    {
                        "type": "button",
                        "label": "支付宝",
                        "action": "purchase_flow",
                        "data": {
                            "step": "payment_done",
                            "order_id": order_id,
                            "order_no": order_no,
                            "payment_method": "alipay",
                            "final_price": final_price,
                        },
                        "icon": "💳",
                    },
                ]
            else:
                state["response"] = "订单创建失败，请重试"

        return state

    def handle_payment_done(self, state, flow_data: dict):
        """步骤6: 支付方式确认后，展示支付密码输入。"""
        order_no = flow_data.get("order_no", "")
        order_id = flow_data.get("order_id", "")
        payment_method = flow_data.get("payment_method", "wechat")
        final_price = flow_data.get("final_price", 0)

        method_name = "微信支付" if payment_method == "wechat" else "支付宝"

        state["purchase_flow"] = {
            **flow_data,
            "step": "payment_password",
        }

        state["response"] = (
            f"💸 {method_name}\n\n"
            f"订单号：{order_no}\n"
            f"支付金额：¥{final_price}\n\n"
            "请输入6位数字支付密码完成支付："
        )
        state["quick_actions"] = [
            {
                "type": "payment_password",
                "label": f"使用{method_name}支付",
                "action": "payment_password",
                "data": {
                    "order_id": order_id,
                    "order_no": order_no,
                    "payment_method": payment_method,
                    "amount": final_price,
                },
                "icon": "🔐",
            }
        ]

        return state

    def handle_payment_success(self, state, flow_data: dict):
        """步骤7: 支付成功。"""
        order_no = flow_data.get("order_no", "")
        order_id = flow_data.get("order_id", "")
        payment_method = flow_data.get("payment_method", "wechat")

        method_name = "微信支付" if payment_method == "wechat" else "支付宝"

        from database.connection import get_db_context
        from services.order_service import OrderService

        try:
            with get_db_context() as db:
                order_service = OrderService(db)
                order_service.update_order_status(
                    order_id=order_id,
                    status="paid",
                )
        except Exception as exc:
            logger.error("更新订单状态失败: %s", exc)

        state["purchase_flow"] = None
        state["response"] = (
            "🎀 支付成功！\n\n"
            f"订单号：{order_no}\n"
            f"支付方式：{method_name}\n"
            f"支付时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "您的订单已支付成功，我们将尽快为您安排发货。\n"
            '您可以在"我的订单"中查看订单详情。'
        )
        state["quick_actions"] = [
            {
                "type": "button",
                "label": "查看我的订单",
                "action": "navigate",
                "data": {"path": "/orders"},
                "icon": "📝",
            },
            {
                "type": "button",
                "label": "继续购物",
                "action": "navigate",
                "data": {"path": "/products"},
                "icon": "🛒",
            },
        ]
        return state


__all__ = ["PurchaseFlowService"]
