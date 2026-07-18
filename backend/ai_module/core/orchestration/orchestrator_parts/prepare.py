"""Preparation pipeline mixin for AIWorkflow."""
from __future__ import annotations

import logging
import time

from ...constants import CONTROL_RESPONSE_MODES
from ...state import ConversationState

logger = logging.getLogger(__name__)


class WorkflowPrepareMixin:
    """Intent preparation and context-loading pipeline."""

    def _should_use_conversation_control(self, state: ConversationState) -> bool:
        return state.get("response_mode") in CONTROL_RESPONSE_MODES

    def _should_clarify(self, state: ConversationState) -> bool:
        if self._should_use_conversation_control(state):
            return False
        if state.get("need_clarification"):
            return True
        confidence = float(state.get("confidence") or 0.0)
        return not state.get("intent") and confidence < 0.6

    def _load_context_only(
        self,
        user_id: str,
        session_id: str,
        message: str,
        attachments=None,
        purchase_flow=None,
        aftersales_flow=None,
    ) -> ConversationState:
        state = self._make_initial_state(
            user_id=user_id,
            session_id=session_id,
            message=message,
            attachments=attachments,
            purchase_flow=purchase_flow,
            aftersales_flow=aftersales_flow,
        )
        return self.context_node.execute(state)

    def _run_prepare_pipeline(self, state: ConversationState) -> ConversationState:
        logger.info("Preparing intent for session=%s", state.get("session_id"))
        total_start = time.time()

        t0 = time.time()
        state = self.context_node.execute(state)
        logger.info("context_node completed in %.2fs", time.time() - t0)

        t0 = time.time()
        state = self.message_entry_node.execute(state)
        logger.info(
            "message_entry_node completed in %.2fs entry_classifier=%s inflow_type=%s intent=%s active_flow=%s current_step=%s",
            time.time() - t0,
            state.get("entry_classifier"),
            state.get("inflow_type"),
            state.get("intent"),
            state.get("active_flow"),
            state.get("current_step"),
        )

        if state.get("skill_route"):
            logger.info(
                "prepare_intent completed in %.2fs via forced_route=%s",
                time.time() - total_start,
                state.get("skill_route"),
            )
            return state

        t0 = time.time()
        state = self.response_planner_node.execute(state)
        logger.info(
            "response_planner_node completed in %.2fs response_mode=%s resume_mode=%s",
            time.time() - t0,
            state.get("response_mode"),
            state.get("resume_mode"),
        )

        if self._should_use_conversation_control(state):
            logger.info("prepare_intent completed in %.2fs via conversation_control", time.time() - total_start)
            return state

        t0 = time.time()
        state = self.policy_node.execute(state)
        logger.info(
            "policy_node completed in %.2fs intent=%s confidence=%s need_clarification=%s",
            time.time() - t0,
            state.get("intent"),
            state.get("confidence"),
            state.get("need_clarification"),
        )

        if self._should_clarify(state):
            logger.info("prepare_intent completed in %.2fs via clarify", time.time() - total_start)
            return state

        t0 = time.time()
        state = self.dialogue_state_node.execute(state)
        logger.info(
            "dialogue_state_node completed in %.2fs active_task=%s stack_size=%s",
            time.time() - t0,
            (state.get("active_task") or {}).get("intent"),
            len(state.get("task_stack") or []),
        )

        logger.info("prepare_intent completed in %.2fs", time.time() - total_start)
        return state

    def prepare_intent(
        self,
        user_id,
        session_id,
        message,
        attachments=None,
        purchase_flow=None,
        aftersales_flow=None,
    ):
        state = self._make_initial_state(
            user_id=user_id,
            session_id=session_id,
            message=message,
            attachments=attachments,
            purchase_flow=purchase_flow,
            aftersales_flow=aftersales_flow,
        )
        return self._run_prepare_pipeline(state)
