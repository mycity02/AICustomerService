"""测试工作流各阶段耗时 + Function Calling 参数检查"""
import time
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))

# 开启 function_calling_node 的日志，查看工具调用参数
logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")

TEST_CASES = [
    ("推荐一个python的商品", "商品推荐 - 带技术关键词"),
    ("有什么推荐", "个性化推荐 - 无关键词"),
    ("我的订单到哪了", "订单查询 - 规则匹配"),
    ("你好", "问答 - 规则匹配"),
    ("推荐几个项目", "推荐 - 模糊表述"),
]


def test_single(workflow, user_id, session_id, message, desc):
    print(f"\n{'='*60}")
    print(f"测试: {desc}")
    print(f"消息: {message}")
    print(f"{'='*60}")

    total_start = time.time()

    # 阶段1: prepare_intent
    t0 = time.time()
    state = workflow.prepare_intent(user_id, session_id, message)
    t_intent = time.time() - t0

    intent = state.get("intent")
    confidence = state.get("confidence")
    print(f"[阶段1] 意图识别: {t_intent:.3f}s → {intent} (置信度: {confidence})")

    # 阶段2: generate_response
    t0 = time.time()
    state = workflow.generate_response(state)
    t_response = time.time() - t0

    tool_used = state.get("tool_used")
    tool_result = state.get("tool_result")
    response = state.get("response", "")[:120]

    print(f"[阶段2] 生成响应: {t_response:.3f}s")
    if tool_used:
        print(f"  工具调用: {tool_used}")
        if tool_result:
            for tr in tool_result:
                if tr.get("result"):
                    r = tr["result"]
                    print(f"  搜索结果: {r.get('total', 0)} 个商品")
                    for p in r.get("products", [])[:3]:
                        print(f"    - {p['title']} | 风味标签: {p.get('tech_stack', [])}")
    print(f"  响应: {response}")

    total = time.time() - total_start
    print(f"  总耗时: {total:.3f}s")

    return {
        "message": message,
        "intent": intent,
        "tool_used": tool_used,
        "total": total,
        "t_intent": t_intent,
        "t_response": t_response,
    }


def main():
    from ai_module.core.orchestration import AIWorkflow
    from services.redis_cache import redis_cache

    try:
        redis_cache.connect()
        print("✅ Redis连接成功")
    except Exception as e:
        print(f"⚠️ Redis连接失败: {e}")

    workflow = AIWorkflow()
    user_id = "545cd010-0000-4669-8847-5d3078545d1b"
    results = []

    for i, (message, desc) in enumerate(TEST_CASES):
        session_id = f"test_session_{i:03d}"
        r = test_single(workflow, user_id, session_id, message, desc)
        results.append(r)

    # 汇总
    print(f"\n\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    print(f"{'消息':<25} {'意图':<10} {'工具':<18} {'耗时':>6}")
    print("-" * 60)
    for r in results:
        tool = r["tool_used"] or "-"
        print(f"{r['message']:<25} {r['intent']:<10} {tool:<18} {r['total']:>5.2f}s")

    try:
        redis_cache.disconnect()
    except:
        pass


main()

