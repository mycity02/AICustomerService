"""Helpers for natural out-of-scope replies with business redirection."""
from __future__ import annotations

import re

from langchain_core.prompts import ChatPromptTemplate

_TRAVEL_RE = re.compile(r"(旅行|旅游|出游|景点|攻略|机票|酒店|新疆|西藏|北京|上海|城市|去哪玩)")
_WEATHER_RE = re.compile(r"(天气|下雨|下雪|气温|冷不冷|热不热|温度)")
_FOOD_RE = re.compile(r"(吃什么|好吃|餐厅|美食|火锅|奶茶|咖啡|饭店)")
_NEWS_RE = re.compile(r"(新闻|打仗|战争|冲突|国际|政治|局势)")
_LIFE_RE = re.compile(r"(焦虑|难过|失眠|烦|怎么办|恋爱|分手|心情)")
_SPORTS_RE = re.compile(r"(比赛|足球|篮球|NBA|CBA|欧冠|进球)")

_BANNED_TOKENS = (
    "我先接一下",
    "我先简短",
    "先放一放",
)

_ANCHOR_TOKENS = (
    "香型",
    "预算",
    "口感",
    "茶品",
    "订单",
    "售后",
    "商品",
    "购买",
    "物流",
    "优惠券",
    "购物车",
    "发票",
    "茶叶",
    "产地",
    "冲泡",
)

_FULL_REPLY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是中文业务助手，正在帮用户处理业务。用户临时岔开聊了别的话题，你要自然地接住并带回业务。

核心目标：像真人客服随口接话一样，在同一段话里顺势回到业务。不要有"先回应、再转折"的两段式模板感。

要求：
1. 接住用户的话，但不要展开讲、不要科普、不要评价得太满。
2. 在同一段回复里顺势带回业务，方式不限——追问、提醒、调侃、反问都行。
3. 整体 1-3 句，像同事间随口一说。每次换不同的说法和句式，避免千篇一律。
4. 参考"业务引导目标"的意思，但必须用自己的话重新表达，禁止照搬原文。
5. 如果有"对话上下文"，利用里面的具体信息（比如用户刚才选了什么、聊到哪一步），让回引更具体而不是泛泛的。

禁止出现的表达：
- "我先接一下""我先简短说一下""先放一放"
- "我们先说回刚才的XX""我们先接着刚才的XX任务"
- "XX确实挺XX的。" 开头（这个句式用太多了）

不自然示例（不要这样写）：
- 不要直接写“我们先说回刚才的茶品选择”，这种模板化转折会显得生硬。
- 新加坡确实挺不错的。我们先接着刚才的选茶任务。

更自然示例（注意每条风格都不同）：
- 哈哈俄罗斯冬天是真冷，不过咱先把订单的事搞定？刚才您还没选呢。
- 俄罗斯啊，等这边处理完可以慢慢聊。您那 7 个订单里要看哪个？
- 好家伙直接飞俄罗斯了，订单那边您还继续不？
- 新加坡好地方，回头可以聊。对了您刚才茶品选到哪一步了？
- 火锅确实治愈，吃完再说。您那个退货申请要不要先提交了？

只输出最终回复，不要解释。""",
        ),
        (
            "human",
            """用户消息：{message}
当前业务：{business_name}
当前主线任务：{task_hint}
对话上下文：{context_hint}
业务引导目标（参考意思，不要照搬）：{redirect}

直接输出回复：""",
        ),
    ]
)


def fallback_ack(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return "这个要看具体情况。"
    if _TRAVEL_RE.search(text):
        return "出去走走挺不错的。"
    if _WEATHER_RE.search(text):
        return "天气变化确实挺快的。"
    if _FOOD_RE.search(text):
        return "这个还是得看个人口味。"
    if _NEWS_RE.search(text):
        return "这类话题背景通常比较复杂。"
    if _LIFE_RE.search(text):
        return "这种事确实容易让人心里发紧。"
    if _SPORTS_RE.search(text):
        return "这种事往往得看临场状态。"
    return "这个问题不在我当前能可靠处理的范围内。"


def _normalize_reply(content: str) -> str:
    normalized = (content or "").replace("\n", "").strip()
    if normalized and normalized[-1] not in "。！？!":
        normalized += "。"
    return normalized


def _looks_scripted(content: str) -> bool:
    return any(token in content for token in _BANNED_TOKENS)


def _has_redirect_anchor(content: str, redirect: str) -> bool:
    anchors = [token for token in _ANCHOR_TOKENS if token in redirect]
    if not anchors:
        english_words = re.findall(r"[A-Za-z]{2,}", redirect)
        anchors = english_words[:3]
    if not anchors:
        return True
    return any(anchor in content for anchor in anchors)


def build_fallback_reply(message: str, redirect: str) -> str:
    redirect = (redirect or "").strip()
    ack = fallback_ack(message)
    if not redirect:
        return ack
    return f"{ack}{redirect}"


def compose_out_of_scope_reply(
    message: str,
    redirect: str,
    *,
    llm=None,
    business_name: str = "",
    task_hint: str = "",
    context_hint: str = "",
) -> str:
    fallback = build_fallback_reply(message, redirect)
    if llm is None:
        return fallback

    try:
        response = llm.invoke(
            _FULL_REPLY_PROMPT.format_messages(
                message=(message or "").strip(),
                business_name=business_name or "当前业务",
                task_hint=task_hint or "当前业务咨询",
                context_hint=context_hint or "无",
                redirect=(redirect or "").strip(),
            )
        )
    except Exception:
        return fallback

    content = _normalize_reply(response.content if hasattr(response, "content") else str(response))
    if not content:
        return fallback
    if _looks_scripted(content):
        return fallback
    if redirect and not _has_redirect_anchor(content, redirect):
        return fallback
    return content
