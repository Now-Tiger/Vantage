#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: graph/nodes/segregator.py
# description: Segregator agent — classifies every PDF page into one of 9 document types.
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.graph.state import PipelineState
from app.llm.provider import get_llm
from app.models.schema import DocumentType, PageClassification

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a medical-claim document classifier.
You will receive the text content of individual pages from a single PDF claim file.
For each page, determine which ONE of the following document types it belongs to:

1. claim_forms          – Insurance claim application or CASHLESS/REIMBURSEMENT request forms
2. cheque_or_bank_details – Cancelled cheque images or bank account details
3. identity_document    – Patient/policyholder ID proof (Aadhaar, PAN, driving licence, etc.)
4. itemized_bill        – Hospital bill with line-item charges
5. discharge_summary    – Hospital discharge summary / certificate
6. prescription         – Doctor prescriptions or medication orders
7. investigation_report – Lab reports, imaging/radiology reports, diagnostic tests
8. cash_receipt         – Payment receipts or cash memos
9. other                – Anything that does not fit the above categories

Rules:
- Assign exactly one type per page.
- Provide a confidence score between 0.0 and 1.0.
- If page text is empty or unreadable, classify as "other" with low confidence.
- Return results for ALL pages provided, in the same order.
"""


class SegregatorOutput(BaseModel):
    classifications: list[PageClassification] = Field(
        description="One classification per page, ordered by page number."
    )


def segregator_node(state: PipelineState) -> dict:
    """Classify every page and write ``page_classifications`` to state."""
    pages = state["pages"]
    if not pages:
        logger.warning("Segregator received zero pages — nothing to classify.")
        return {"page_classifications": []}

    page_block = "\n\n".join(
        f"--- PAGE {p.page_number} ---\n{p.text if p.text.strip() else '[EMPTY / NO TEXT]'}"
        for p in pages
    )

    llm = get_llm()
    structured_llm = llm.with_structured_output(SegregatorOutput)

    result: SegregatorOutput = structured_llm.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify each page below:\n\n{page_block}"},
        ]
    )

    logger.info(
        "Segregator classified %d page(s): %s",
        len(result.classifications),
        {c.document_type.value: c.page_number for c in result.classifications},
    )

    return {"page_classifications": result.classifications}
