#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: services/pdf.py
# description: PDF processing utilities — memory-efficient, parallel text extraction.
"""
PDF processing utilities — memory-efficient, parallel text extraction.

Uses pdfplumber for text extraction and ProcessPoolExecutor so that
CPU-bound per-page work runs across cores without blocking the async
event loop.  Each page is opened independently inside the worker so
only the raw bytes (shared once via fork) and the resulting text string
cross the process boundary — never a heavy pdfplumber/PDF object.
"""

from __future__ import annotations

import io
import logging
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import pdfplumber

from app.models.schema import PageData

logger = logging.getLogger(__name__)

# Cap workers to avoid over-subscribing on large machines; 4 is plenty for
# a 10–20 page PDF where each page takes ~5–20 ms of CPU time.
_MAX_WORKERS = 4


# Worker function (runs in a child process)
def _extract_single_page(pdf_bytes: bytes, page_index: int) -> PageData:
    """Open the PDF in this process, extract text for *one* page, close it."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_index]
        text = page.extract_text() or ""
    return PageData(page_number=page_index + 1, text=text)


# Public API
def extract_pages(pdf_bytes: bytes) -> list[PageData]:
    """
    Extract text from every page of a PDF in parallel.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        Ordered list of ``PageData`` (1-indexed page numbers).

    Raises:
        ValueError: If the PDF has zero pages or cannot be parsed.
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)

    if total_pages == 0:
        raise ValueError("PDF contains no pages.")

    logger.info("Extracting text from %d page(s) using up to %d workers", total_pages, min(_MAX_WORKERS, total_pages))

    worker = partial(_extract_single_page, pdf_bytes)

    with ProcessPoolExecutor(max_workers=min(_MAX_WORKERS, total_pages)) as pool:
        results = list(pool.map(worker, range(total_pages)))

    return results


def get_page_subset(pages: list[PageData], indices: list[int]) -> list[PageData]:
    """
    Return only the pages whose 1-indexed page_number is in *indices*.

    Args:
        pages:   Full list of extracted pages.
        indices: 1-indexed page numbers to keep.

    Returns:
        Filtered (order-preserved) list of ``PageData``.
    """
    target = set(indices)
    return [p for p in pages if p.page_number in target]
