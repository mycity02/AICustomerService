"""Business-domain scope detection helpers."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .capability_registry import build_capability_specs
from .constants import DEFAULT_INTENT_RULES, INTENT_QA

_SOCIAL_MESSAGE_RE = re.compile(
    r"^(你好|您好|hello|hi|在吗|哈哈|哈喽|谢谢|感谢|辛苦了|好的|ok|再见|拜拜)[!！。.\s]*$",
    re.IGNORECASE,
)


_CATALOG_QUERY_RE = re.compile(
    r"((?:有|卖|提供|上架).{0,8}(?:什么|哪些|啥).{0,4}(?:茶|商品)|"
    r"(?:茶|商品).{0,8}(?:有什么|有哪些|卖什么|卖哪些|种类))",
    re.IGNORECASE,
)


_GUARDED_REQUEST_PATTERNS = (
    (
        "crisis",
        re.compile(r"(不想活了|想死|自杀|自残|结束生命|伤害自己|活不下去)", re.IGNORECASE),
    ),
    (
        "prompt_security",
        re.compile(
            r"(?:(?:(?:系统|开发者|隐藏|内部).{0,8}(?:提示词|指令|规则)|"
            r"(?:api[\s_-]?key|密钥|访问令牌|token)).{0,16}"
            r"(?:告诉|显示|输出|泄露|给我|发给|是什么|查看)|"
            r"(?:告诉|显示|输出|泄露|给我|发给|查看).{0,16}"
            r"(?:(?:系统|开发者|隐藏|内部).{0,8}(?:提示词|指令|规则)|"
            r"(?:api[\s_-]?key|密钥|访问令牌|token))|"
            r"(?:忽略|绕过|覆盖).{0,8}(?:之前|系统|安全).{0,8}(?:指令|规则))",
            re.IGNORECASE,
        ),
    ),
    (
        "privacy",
        re.compile(
            r"(?:(?:其他|别的|他人|别人|所有|全部).{0,4}(?:用户|顾客|会员|账号)?).{0,16}"
            r"(?:订单|收货地址|地址|手机号|电话|身份证|聊天记录|个人信息|账户余额|验证码|密码)|"
            r"(?:订单|收货地址|地址|手机号|电话|身份证|聊天记录|个人信息|账户余额|验证码|密码).{0,16}"
            r"(?:(?:其他|别的|他人|别人|所有|全部).{0,4}(?:用户|顾客|会员|账号)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "harmful",
        re.compile(
            r"(?:(?:怎么|如何|教程|步骤|方法|制作|教我|帮我).{0,18}"
            r"(?:炸弹|爆炸物|毒药|枪支|武器|木马|勒索软件|盗号|黑进|入侵|诈骗|洗钱|绕过支付|破解账号)|"
            r"(?:炸弹|爆炸物|毒药|枪支|武器|木马|勒索软件|盗号|黑进|入侵|诈骗|洗钱|绕过支付|破解账号).{0,18}"
            r"(?:怎么|如何|教程|步骤|方法|制作|教我|帮我))",
            re.IGNORECASE,
        ),
    ),
    (
        "medical",
        re.compile(
            r"(?:(?:茶|茶叶|喝茶).{0,18}"
            r"(?:治疗|治愈|能治|可以治|治病|替代药物|替代.{0,4}药|停药|诊断|处方|降血压|降血糖)|"
            r"(?:治疗|治愈|替代药物|替代.{0,4}药|停药|诊断|处方).{0,18}(?:茶|茶叶|喝茶)|"
            r"(?:孕妇|孕期|哺乳期|糖尿病|高血压|心脏病|服药|吃药|药物过敏).{0,16}"
            r"(?:能不能|可以|适合|推荐|喝|饮用).{0,8}(?:茶|茶叶)|"
            r"(?:茶|茶叶).{0,12}(?:孕妇|孕期|哺乳期|糖尿病|高血压|心脏病|服药|吃药|药物过敏))",
            re.IGNORECASE,
        ),
    ),
)


def classify_guarded_request(message: str) -> Optional[str]:
    """识别必须使用确定性拒答、不能交给模型自由发挥的请求。"""
    normalized = (message or "").strip()
    if not normalized:
        return None
    for category, pattern in _GUARDED_REQUEST_PATTERNS:
        if pattern.search(normalized):
            return category
    return None


def is_simple_social_message(message: str) -> bool:
    return bool(_SOCIAL_MESSAGE_RE.match((message or "").strip()))


def looks_like_catalog_query(message: str) -> bool:
    """识别“卖什么茶/有哪些商品”等目录浏览问法。"""
    return bool(_CATALOG_QUERY_RE.search((message or "").strip()))


def get_intent_rules(runtime=None) -> Dict[str, List[str]]:
    if runtime is None:
        return {intent: list(keywords) for intent, keywords in DEFAULT_INTENT_RULES.items()}
    return runtime.get_intent_rules()


def get_runtime_config(runtime=None) -> Dict[str, object]:
    business_pack = getattr(runtime, "business_pack", None) if runtime is not None else None
    config = getattr(business_pack, "config", {}) if business_pack is not None else {}
    return config if isinstance(config, dict) else {}


def has_business_signal(message: str, *, runtime=None) -> bool:
    normalized = (message or "").strip().lower()
    if not normalized:
        return False

    if looks_like_catalog_query(normalized):
        return True
    if re.search(r"(茶叶|茶品|商品|商城|在售|绿茶|红茶|乌龙茶|白茶|普洱茶|花茶|选茶)", normalized, re.IGNORECASE):
        return True
    if re.search(r"(找|想要|需要|推荐).*(茶|茶叶|茶品)", normalized, re.IGNORECASE):
        return True

    for intent, keywords in get_intent_rules(runtime).items():
        if intent == INTENT_QA:
            continue
        for keyword in keywords:
            if keyword and keyword.lower() in normalized:
                return True

    for spec in build_capability_specs(get_runtime_config(runtime)):
        for keyword in spec.keywords:
            if keyword and keyword.lower() in normalized:
                return True

    return False


def looks_out_of_business_scope(message: str, *, runtime=None) -> bool:
    normalized = (message or "").strip()
    if not normalized:
        return False
    if classify_guarded_request(normalized):
        return True
    if is_simple_social_message(normalized):
        return False
    if has_business_signal(normalized, runtime=runtime):
        return False
    return len(normalized) >= 4
