"""Rule-based extraction for tea shopping preferences.

The dialogue layer uses these deterministic signals before asking the LLM so
short replies such as ``兰花香`` remain attached to an open recommendation
task instead of being treated as a brand-new product question.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional


TEA_CATEGORIES = (
    "绿茶",
    "红茶",
    "乌龙茶",
    "青茶",
    "白茶",
    "黄茶",
    "黑茶",
    "普洱茶",
    "普洱",
    "花茶",
    "茉莉花茶",
    "岩茶",
    "铁观音",
    "单丛茶",
    "单丛",
)

AROMA_KEYWORDS = (
    "栀子花香",
    "桂花香",
    "茉莉花香",
    "兰花香",
    "蜜兰香",
    "荔枝香",
    "蜜桃香",
    "果香",
    "花香",
    "豆香",
    "栗香",
    "蜜香",
    "甜香",
    "陈香",
    "木香",
    "枣香",
    "药香",
    "焙火香",
    "炭焙香",
    "清香",
    "浓香",
)

TASTE_KEYWORDS = (
    "清淡",
    "清爽",
    "鲜爽",
    "清鲜",
    "柔和",
    "甘甜",
    "回甘",
    "醇厚",
    "浓醇",
    "厚重",
    "不苦",
    "不涩",
)

USAGE_KEYWORDS = {
    "送礼": "送礼",
    "礼盒": "送礼",
    "送人": "送礼",
    "自饮": "自饮",
    "自己喝": "自饮",
    "日常喝": "日常饮用",
    "办公室": "办公饮用",
    "办公": "办公饮用",
    "待客": "待客",
}

_LOW_BOILING_POINT_RE = re.compile(
    r"(西藏|高原|海拔高|沸点低|水温(?:不够|上不去)|烧不到\s*100|低温冲泡)",
    re.IGNORECASE,
)


def _first_contained(message: str, values: Iterable[str]) -> Optional[str]:
    return next((value for value in values if value in message), None)


def extract_tea_preferences(message: str) -> Dict[str, Any]:
    """Extract stable tea-domain slots from a single user message."""
    normalized = (message or "").strip()
    if not normalized:
        return {}

    updates: Dict[str, Any] = {}

    category = _first_contained(normalized, TEA_CATEGORIES)
    if category:
        updates["tea_category"] = "普洱茶" if category == "普洱" else category

    aroma = _first_contained(normalized, AROMA_KEYWORDS)
    if aroma:
        updates["aroma"] = aroma

    taste = _first_contained(normalized, TASTE_KEYWORDS)
    if taste:
        updates["taste"] = taste

    for keyword, usage in USAGE_KEYWORDS.items():
        if keyword in normalized:
            updates["usage"] = usage
            break

    if _LOW_BOILING_POINT_RE.search(normalized):
        updates["brewing_constraint"] = "low_boiling_point"
        if "西藏" in normalized:
            updates["location"] = "西藏"
        elif "高原" in normalized or "海拔高" in normalized:
            updates["location"] = "高原地区"

    return updates


def build_preference_search_keyword(slots: Dict[str, Any]) -> str:
    """Choose the most discriminative catalog keyword from merged slots."""
    for key in ("aroma", "tea_category", "taste", "usage"):
        value = slots.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


TEA_PREFERENCE_SLOT_KEYS = frozenset(
    {"tea_category", "aroma", "taste", "usage", "brewing_constraint", "location"}
)


def has_tea_preference_slots(slots: Dict[str, Any]) -> bool:
    return any(key in slots for key in TEA_PREFERENCE_SLOT_KEYS)
