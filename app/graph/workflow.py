#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: graph/workflow.py
# description: LangGraph workflow — wires the full claim-processing pipeline.
from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.graph.nodes.aggregator import aggregator_node
from app.graph.nodes.bill_agent import bill_agent_node
from app.graph.nodes.discharge_agent import discharge_agent_node
from app.graph.nodes.id_agent import id_agent_node
from app.graph.nodes.segregator import segregator_node
from app.graph.state import PipelineState
from app.models.schema import DocumentType

logger = logging.getLogger(__name__)


AGENT_FOR_DOC_TYPE: dict[DocumentType, str] = {
    DocumentType.IDENTITY: "id_agent",
    DocumentType.DISCHARGE_SUMMARY: "discharge_agent",
    DocumentType.ITEMIZED_BILL: "bill_agent",
}


def _route_to_agents(state: PipelineState) -> list[Send]:
    """Fan-out: send state to each extraction agent that has matching pages."""
    classifications = state.get("page_classifications", [])

    needed_agents: set[str] = set()
    for c in classifications:
        agent_name = AGENT_FOR_DOC_TYPE.get(c.document_type)
        if agent_name:
            needed_agents.add(agent_name)

    if not needed_agents:
        logger.warning("No pages matched any extraction agent — skipping straight to aggregator.")
        return [Send("aggregator", state)]

    logger.info("Routing to extraction agents: %s", sorted(needed_agents))
    return [Send(agent, state) for agent in sorted(needed_agents)]


def build_workflow() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("segregator", segregator_node)
    graph.add_node("id_agent", id_agent_node)
    graph.add_node("discharge_agent", discharge_agent_node)
    graph.add_node("bill_agent", bill_agent_node)
    graph.add_node("aggregator", aggregator_node)

    graph.add_edge(START, "segregator")
    graph.add_conditional_edges("segregator", _route_to_agents)
    graph.add_edge("id_agent", "aggregator")
    graph.add_edge("discharge_agent", "aggregator")
    graph.add_edge("bill_agent", "aggregator")
    graph.add_edge("aggregator", END)

    return graph


pipeline = build_workflow().compile()
