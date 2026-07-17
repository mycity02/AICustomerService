import asyncio
import importlib.util
import sys
import types
from pathlib import Path

class _FakePromptTemplate:
    def __init__(self, messages):
        self.messages = messages

    @classmethod
    def from_messages(cls, messages):
        return cls(messages)

    def format_messages(self, **kwargs):
        return [{"role": "human", "content": kwargs.get("context", "")}]


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def __init__(self, content):
        self._content = content

    async def ainvoke(self, _messages):
        return _FakeResponse(self._content)


def _load_service_module(fake_llm):
    service_path = Path(__file__).resolve().parents[1] / "services" / "smart_questions_service.py"
    module_name = "smart_questions_service_under_test"

    fake_prompt_module = types.ModuleType("langchain_core.prompts")
    fake_prompt_module.ChatPromptTemplate = _FakePromptTemplate

    fake_config_module = types.ModuleType("config")
    fake_config_module.init_chat_model = lambda **_kwargs: fake_llm

    original_prompt_module = sys.modules.get("langchain_core.prompts")
    original_config_module = sys.modules.get("config")
    sys.modules["langchain_core.prompts"] = fake_prompt_module
    sys.modules["config"] = fake_config_module

    try:
        spec = importlib.util.spec_from_file_location(module_name, service_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if original_prompt_module is None:
            sys.modules.pop("langchain_core.prompts", None)
        else:
            sys.modules["langchain_core.prompts"] = original_prompt_module

        if original_config_module is None:
            sys.modules.pop("config", None)
        else:
            sys.modules["config"] = original_config_module


def test_generate_smart_questions_keeps_llm_to_text_candidates_only():
    llm = _FakeLLM(
        """
        {
          "questions": [
            {"label": "查看物流", "question": "帮我查看物流信息", "topic": "logistics"},
            {"label": "申请退款", "question": "如何申请退款？", "topic": "refund"},
            {"label": "申请退款", "question": "如何申请退款？", "topic": "refund"},
            {"label": "购物车", "question": "购物车里有什么", "topic": "cart"}
          ]
        }
        """
    )
    module = _load_service_module(llm)
    service = module.SmartQuestionsService()

    result = asyncio.run(
        service.generate_smart_questions(
            user_id="u1",
            user_profile={},
            recent_orders=[{"status": "shipped", "product_name": "Python 项目"}],
            browsing_history=None,
        )
    )

    assert len(result) == 3
    assert all(item["type"] == "button" for item in result)
    assert all(item["action"] == "send_question" for item in result)
    assert {item["data"]["question"] for item in result} >= {"帮我查看物流信息", "如何申请退款？"}
    assert all("购物车" not in item["data"]["question"] for item in result)


def test_generate_smart_questions_falls_back_when_llm_payload_is_invalid():
    llm = _FakeLLM("not-json")
    module = _load_service_module(llm)
    service = module.SmartQuestionsService()

    result = asyncio.run(
        service.generate_smart_questions(
            user_id="u2",
            user_profile={},
            recent_orders=[{"status": "shipped", "product_name": "Java 项目"}],
            browsing_history=None,
        )
    )

    assert len(result) == 3
    assert result[0]["data"]["question"] == "帮我查看物流信息"
    assert all(item["action"] == "send_question" for item in result)
