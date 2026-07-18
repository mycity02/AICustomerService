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


def is_simple_social_message(message: str) -> bool:
    return bool(_SOCIAL_MESSAGE_RE.match((message or "").strip()))


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

    if re.search(r"(茶叶|绿茶|红茶|乌龙茶|白茶|普洱茶|花茶|选茶)", normalized, re.IGNORECASE):
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
    if is_simple_social_message(normalized):
        return False
    if has_business_signal(normalized, runtime=runtime):
        return False
    return len(normalized) >= 4
