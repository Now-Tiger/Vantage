#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: graph/nodes/aggregator.py
# description: Aggregator node — merges all extraction agent results into the final output.

from __future__ import annotations

import logging

from app.graph.state import PipelineState
from app.models.schema import DischargeSummaryInfo, IdentityInfo, ItemizedBillInfo, PageClassification

logger = logging.getLogger(__name__)


def aggregator_node(state: PipelineState) -> dict:
    """Combine segregation + extraction results into ``final_output``."""
    results = state.get("extraction_results", {})
    classifications: list[PageClassification] = state.get("page_classifications", [])

    identity_raw = results.get("identity")
    discharge_raw = results.get("discharge_summary")
    bill_raw = results.get("itemized_bill")

    final: dict = {
        "claim_id": state["claim_id"],
        "segregation": [c.model_dump() for c in classifications],
        "identity": IdentityInfo(**identity_raw).model_dump() if identity_raw else None,
        "discharge_summary": DischargeSummaryInfo(**discharge_raw).model_dump() if discharge_raw else None,
        "itemized_bill": ItemizedBillInfo(**bill_raw).model_dump() if bill_raw else None,
    }

    logger.info("Aggregator built final output for claim_id=%s", state["claim_id"])
    return {"final_output": final}
