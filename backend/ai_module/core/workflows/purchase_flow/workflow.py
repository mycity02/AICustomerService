"""Purchase flow workflow implementation."""
from __future__ import annotations

import logging

from ...nodes.purchase_flow import PurchaseFallbackNode, PurchaseRouteNode, PurchaseValidateNode
from ...state import ConversationState
from ..base import BaseWorkflow
from .service import PurchaseFlowService
from .state_machine import PurchaseFlowState, STEP_TO_NODE_KEY, next_state
from .steps import build_step_nodes, cleanup_runtime_keys

logger = logging.getLogger(__name__)


class PurchaseFlowWorkflow(BaseWorkflow):
    name = "purchase_flow"
    stream_enabled = False

    def __init__(
        self,
        validate_node: PurchaseValidateNode | None = None,
        route_node: PurchaseRouteNode | None = None,
        fallback_node: PurchaseFallbackNode | None = None,
        service: PurchaseFlowService | None = None,
    ):
        self.service = service or PurchaseFlowService()
        self.validate_node = validate_node or PurchaseValidateNode()
        self.route_node = route_node or PurchaseRouteNode(STEP_TO_NODE_KEY)
        self.fallback_node = fallback_node or PurchaseFallbackNode()
        self.step_nodes = build_step_nodes(self.service)

    def execute(self, state: ConversationState) -> ConversationState:
        current = PurchaseFlowState.START

        while current != PurchaseFlowState.END:
            current = next_state(current)
            if current == PurchaseFlowState.VALIDATE_FLOW:
                state = self.validate_node.execute(state)
            elif current == PurchaseFlowState.RESOLVE_STEP:
                state = self.route_node.execute(state)
            elif current == PurchaseFlowState.RUN_STEP_NODE:
                node_key = state.get("_purchase_flow_node_key")
                step_node = self.step_nodes.get(node_key)
                if step_node is None:
                    logger.warning("Unknown purchase flow step route=%s", node_key)
                    state = self.fallback_node.execute(state)
                else:
                    state = step_node.execute(state)
            elif current == PurchaseFlowState.CLEANUP:
                state = cleanup_runtime_keys(state)

        return state
