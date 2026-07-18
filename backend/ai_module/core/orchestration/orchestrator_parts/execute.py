"""Response execution mixin for AIWorkflow."""
from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from ...constants import INTENT_RECOMMEND
from ...state import ConversationState

logger = logging.getLogger(__name__)


class WorkflowExecuteMixin:
    """Workflow and node execution helpers (sync + stream)."""

    def _safe_save_context(self, state: ConversationState) -> None:
        try:
            self.save_context_node.execute(state)
        except Exception:
            logger.warning("Failed to persist conversation context", exc_info=True)

    def _execute_forced_route(self, state: ConversationState) -> ConversationState:
        route = state.get("skill_route")
        if not route:
            return state

        logger.info("Executing forced route=%s", route)
        node = self.handlers.get(route, default=self._get_qa_node())
        try:
            result_state = node.execute(state)
            state.update(result_state)
        except Exception as exc:
            logger.error("Forced route %s failed: %s", route, exc, exc_info=True)
            state["response"] = "抱歉，处理您的请求时出现了问题，请稍后再试。"

        if route != "clarify":
            self._safe_save_context(state)
        return state

    def _execute_workflow(
        self,
        workflow_name: str,
        state: ConversationState,
        *,
        error_response: str,
        save_context: bool = True,
    ) -> ConversationState:
        workflow = self.workflows.get(workflow_name)
        if workflow is None:
            state["response"] = error_response
            return state

        try:
            result_state = workflow.execute(state)
            state.update(result_state)
            if save_context:
                self._safe_save_context(state)
        except Exception as exc:
            logger.error("Workflow %s failed: %s", workflow_name, exc, exc_info=True)
            state["response"] = error_response
        return state

    def _stream_workflow(
        self,
        workflow_name: str,
        state: ConversationState,
        *,
        error_response: str,
        save_context: bool = True,
        status: Optional[Dict[str, bool]] = None,
    ):
        stream_status = status if status is not None else {}
        stream_status["failed"] = False
        workflow = self.workflows.get(workflow_name)
        if workflow is None:
            stream_status["failed"] = True
            yield {"type": "content", "delta": error_response}
            return

        try:
            stream_workflow = self.workflows.get_stream(workflow_name)
            if stream_workflow is not None:
                for token in stream_workflow.execute_stream(state):
                    yield {"type": "content", "delta": token}
            else:
                result_state = workflow.execute(state)
                state.update(result_state)
                if state.get("response"):
                    yield {"type": "content", "delta": state["response"]}

            if save_context:
                self._safe_save_context(state)
        except Exception as exc:
            logger.error("Workflow %s streaming failed: %s", workflow_name, exc, exc_info=True)
            stream_status["failed"] = True
            yield {"type": "content", "delta": error_response}

    def generate_response(self, state):
        purchase_flow = state.get("purchase_flow")
        if purchase_flow:
            logger.info("Purchase flow detected step=%s", purchase_flow.get("step"))
            return self._execute_workflow(
                "purchase_flow",
                state,
                error_response="抱歉，购买流程出现了问题，请重新开始。",
            )

        aftersales_flow = state.get("aftersales_flow")
        if aftersales_flow:
            logger.info("Aftersales flow detected step=%s", aftersales_flow.get("step"))
            return self._execute_workflow(
                "aftersales_flow",
                state,
                error_response="抱歉，售后流程出现了问题，请重新开始。",
            )

        logger.info("Generating response intent=%s", state.get("intent"))

        if self._should_use_conversation_control(state):
            result_state = self.conversation_control_node.execute(state)
            state.update(result_state)
            self._safe_save_context(state)
            return state

        if self._should_clarify(state):
            result_state = self._get_clarify_node().execute(state)
            state.update(result_state)
            return state

        if state.get("skill_route"):
            return self._execute_forced_route(state)

        if state.get("intent") == INTENT_RECOMMEND:
            logger.info("Recommendation intent routed directly to topic advisor")
            return self._execute_workflow(
                "topic_advisor",
                state,
                error_response="抱歉，处理您的请求时出现了问题，请稍后再试。",
            )

        t0 = time.time()
        state = self.function_calling_node.execute(state)
        logger.info(
            "function_calling_node completed in %.2fs tool_used=%s",
            time.time() - t0,
            state.get("tool_used"),
        )

        route = self.router.route_after_function_calling(state)
        node = self.handlers.get(route, default=self._get_qa_node())

        try:
            result_state = node.execute(state)
            state.update(result_state)
        except Exception as exc:
            logger.error("Node %s failed: %s", route, exc, exc_info=True)
            state["response"] = "抱歉，处理您的请求时出现了问题，请稍后再试。"

        if route != "clarify":
            self._safe_save_context(state)

        return state

    def generate_response_stream(self, state):
        purchase_flow = state.get("purchase_flow")
        if purchase_flow:
            logger.info("Streaming purchase flow step=%s", purchase_flow.get("step"))
            stream_status = {"failed": False}
            for event in self._stream_workflow(
                "purchase_flow",
                state,
                error_response="抱歉，购买流程出现了问题，请重新开始。",
                status=stream_status,
            ):
                yield event
            yield {
                "type": "end",
                "status": "error" if stream_status["failed"] else "success",
                "quick_actions": state.get("quick_actions"),
            }
            return

        aftersales_flow = state.get("aftersales_flow")
        if aftersales_flow:
            logger.info("Streaming aftersales flow step=%s", aftersales_flow.get("step"))
            stream_status = {"failed": False}
            for event in self._stream_workflow(
                "aftersales_flow",
                state,
                error_response="抱歉，售后流程出现了问题，请重新开始。",
                status=stream_status,
            ):
                yield event
            yield {
                "type": "end",
                "status": "error" if stream_status["failed"] else "success",
                "quick_actions": state.get("quick_actions"),
            }
            return

        if self._should_use_conversation_control(state):
            result_state = self.conversation_control_node.execute(state)
            state.update(result_state)
            if state.get("response"):
                yield {"type": "content", "delta": state["response"]}
            self._safe_save_context(state)
            yield {"type": "end", "quick_actions": state.get("quick_actions")}
            return

        if self._should_clarify(state):
            result_state = self._get_clarify_node().execute(state)
            state.update(result_state)
            if state.get("response"):
                yield {"type": "content", "delta": state["response"]}
            yield {"type": "end", "quick_actions": state.get("quick_actions")}
            return

        if state.get("skill_route"):
            result_state = self._execute_forced_route(state)
            state.update(result_state)
            if state.get("response"):
                yield {"type": "content", "delta": state["response"]}
            yield {
                "type": "end",
                "quick_actions": state.get("quick_actions"),
                "recommended_products": state.get("recommended_products"),
            }
            return

        if state.get("intent") == INTENT_RECOMMEND:
            logger.info("Streaming recommendation via topic advisor")
            for event in self._stream_workflow(
                "topic_advisor",
                state,
                error_response="抱歉，处理您的请求时出现了问题，请稍后再试。",
            ):
                yield event
            yield {
                "type": "end",
                "quick_actions": state.get("quick_actions"),
                "recommended_products": state.get("recommended_products"),
            }
            return

        t0 = time.time()
        state = self.function_calling_node.execute(state)
        logger.info("function_calling_node completed in %.2fs", time.time() - t0)

        route = self.router.route_after_function_calling(state)
        logger.info("stream route=%s", route)

        stream_node = self.handlers.get_stream(route)
        if stream_node is not None:
            try:
                for token in stream_node.execute_stream(state):
                    yield {"type": "content", "delta": token}
            except Exception as exc:
                logger.error("Streaming node %s failed: %s", route, exc, exc_info=True)
                state["response"] = "抱歉，处理您的请求时出现了问题，请稍后再试。"
                yield {"type": "content", "delta": state["response"]}
        else:
            node = self.handlers.get(route, default=self._get_qa_node())
            try:
                result_state = node.execute(state)
                state.update(result_state)
            except Exception as exc:
                logger.error("Node %s failed: %s", route, exc, exc_info=True)
                state["response"] = "抱歉，处理您的请求时出现了问题，请稍后再试。"
            if state.get("response"):
                yield {"type": "content", "delta": state["response"]}

        if route != "clarify":
            self._safe_save_context(state)

        yield {
            "type": "end",
            "sources": state.get("sources"),
            "quick_actions": state.get("quick_actions"),
            "recommended_products": state.get("recommended_products"),
        }
