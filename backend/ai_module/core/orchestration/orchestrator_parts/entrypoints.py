"""Public entrypoint mixin for AIWorkflow."""
from __future__ import annotations

from datetime import datetime

from ...constants import INTENT_QA


class WorkflowEntrypointsMixin:
    """Request-level entrypoint methods."""

    def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        attachments=None,
        purchase_flow=None,
        aftersales_flow=None,
    ):
        start_time = datetime.now()
        if purchase_flow or aftersales_flow:
            final_state = self._load_context_only(
                user_id=user_id,
                session_id=session_id,
                message=message,
                attachments=attachments,
                purchase_flow=purchase_flow,
                aftersales_flow=aftersales_flow,
            )
            final_state = self.generate_response(final_state)
        else:
            prepared_state = self.prepare_intent(
                user_id=user_id,
                session_id=session_id,
                message=message,
                attachments=attachments,
            )
            final_state = self.generate_response(prepared_state)

        final_state["processing_time"] = (datetime.now() - start_time).total_seconds()
        return final_state

    def process_message_stream(
        self,
        user_id,
        session_id,
        message,
        attachments=None,
        purchase_flow=None,
        aftersales_flow=None,
    ):
        start_time = datetime.now()

        if purchase_flow or aftersales_flow:
            state = self._load_context_only(
                user_id=user_id,
                session_id=session_id,
                message=message,
                attachments=attachments,
                purchase_flow=purchase_flow,
                aftersales_flow=aftersales_flow,
            )
            intent = (
                state.get("intent")
                or (state.get("active_task") or {}).get("intent")
                or state.get("last_intent")
                or INTENT_QA
            )
        else:
            state = self.prepare_intent(user_id, session_id, message, attachments)
            intent = state.get("intent", INTENT_QA)

        yield {"type": "intent", "intent": intent}

        for event in self.generate_response_stream(state):
            if event.get("type") == "end":
                event["processing_time"] = (datetime.now() - start_time).total_seconds()
            yield event
