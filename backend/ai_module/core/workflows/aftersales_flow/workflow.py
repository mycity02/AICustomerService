"""Aftersales flow workflow implementation."""
from __future__ import annotations

import logging

from ...nodes.aftersales import AftersalesFallbackNode, AftersalesRouteNode, AftersalesValidateNode
from ...state import ConversationState
from ..base import BaseWorkflow
from .state_machine import AftersalesFlowState, STEP_TO_NODE_KEY, next_state
from .steps import build_step_nodes, cleanup_runtime_keys

logger = logging.getLogger(__name__)


class AftersalesFlowWorkflow(BaseWorkflow):
    name = "aftersales_flow"
    stream_enabled = False

    def __init__(
        self,
        validate_node: AftersalesValidateNode | None = None,
        route_node: AftersalesRouteNode | None = None,
        fallback_node: AftersalesFallbackNode | None = None,
    ):
        self.validate_node = validate_node or AftersalesValidateNode()
        self.route_node = route_node or AftersalesRouteNode(STEP_TO_NODE_KEY)
        self.fallback_node = fallback_node or AftersalesFallbackNode()
        self.step_nodes = build_step_nodes()

    def execute(self, state: ConversationState) -> ConversationState:
        current = AftersalesFlowState.START

        while current != AftersalesFlowState.END:
            current = next_state(current)
            if current == AftersalesFlowState.VALIDATE_FLOW:
                state = self.validate_node.execute(state)
            elif current == AftersalesFlowState.RESOLVE_STEP:
                state = self.route_node.execute(state)
            elif current == AftersalesFlowState.RUN_STEP_NODE:
                node_key = state.get("_aftersales_node_key")
                step_node = self.step_nodes.get(node_key)
                if step_node is None:
                    logger.warning("Unknown aftersales step route=%s", node_key)
                    state = self.fallback_node.execute(state)
                else:
                    state = step_node.execute(state)
            elif current == AftersalesFlowState.CLEANUP:
                state = cleanup_runtime_keys(state)

        return state
