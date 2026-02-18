#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: graph/state.py
# description: LangGraph shared state for the claim-processing pipeline.
from __future__ import annotations

from typing import Annotated, Any

from typing_extensions import TypedDict

from app.models.schema import PageClassification, PageData


def _merge_dicts(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Reducer: shallow-merge two dicts (used for extraction_results)."""
    merged = current.copy()
    merged.update(update)
    return merged


class PipelineState(TypedDict):
    claim_id: str
    pages: list[PageData]
    page_classifications: list[PageClassification]
    extraction_results: Annotated[dict[str, Any], _merge_dicts]
    final_output: dict[str, Any]
