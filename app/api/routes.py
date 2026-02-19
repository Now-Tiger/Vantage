#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: api/routes.py
# description: API Routes for the application
from __future__ import annotations

import asyncio
import logging
import random
from datetime import date
from functools import partial

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.db.repository import fetch_all_claims, fetch_claim_result, save_claim_result
from app.graph.workflow import pipeline
from app.models.schema import ClaimListResponse, ProcessResponse
from app.services.pdf import extract_pages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["processing"])

MAX_PDF_BYTES = settings.MAX_PDF_SIZE_MB * 1024 * 1024


def _generate_claim_id() -> str:
    """Generate ``claim-YYYYMMDD-<6 random digits>``."""
    today = date.today().strftime("%Y%m%d")
    suffix = random.randint(100_000, 999_999)
    return f"claim-{today}-{suffix}"


@router.post("/process", response_model=ProcessResponse)
async def process_claim(file: UploadFile = File(...)) -> ProcessResponse:
    """Accept a PDF claim, run the LangGraph segregation + extraction pipeline, return structured JSON."""

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()

    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF exceeds the {settings.MAX_PDF_SIZE_MB} MB limit.",
        )

    claim_id = _generate_claim_id()

    try:
        loop = asyncio.get_running_loop()
        pages = await loop.run_in_executor(None, partial(extract_pages, pdf_bytes))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = await asyncio.to_thread(
            pipeline.invoke,
            {"claim_id": claim_id, "pages": pages, "page_classifications": [], "extraction_results": {}, "final_output": {}},
            {"recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT},
        )
    except Exception as exc:
        logger.exception("Pipeline failed for claim_id=%s", claim_id)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    response = ProcessResponse(**result["final_output"])

    try:
        await save_claim_result(response)
    except Exception as exc:
        logger.exception("Failed to persist claim_id=%s to DB", claim_id)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc

    return response


@router.get("/claims", response_model=ClaimListResponse)
async def list_claims(limit: int = 20, offset: int = 0) -> ClaimListResponse:
    """List all processed claims (paginated)."""
    items, total = await fetch_all_claims(limit=limit, offset=offset)
    return ClaimListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/claims/{claim_id}", response_model=ProcessResponse)
async def get_claim(claim_id: str) -> ProcessResponse:
    """Fetch a previously processed claim by its ID."""
    result = await fetch_claim_result(claim_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    return result
