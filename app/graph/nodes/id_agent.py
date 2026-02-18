"""
ID Agent — extracts identity / policy information from pages classified
as ``identity_document``.
"""

from __future__ import annotations

import logging

from app.graph.state import PipelineState
from app.llm.provider import get_llm
from app.models.schema import DocumentType, IdentityInfo
from app.services.pdf import get_page_subset

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a medical-claim identity-document extraction specialist.
You will receive the text of one or more pages from an identity document
(e.g. Aadhaar card, PAN card, driving licence, passport, insurance ID card).

Extract the following fields. Return null for any field you cannot find:
- patient_name
- date_of_birth (format: YYYY-MM-DD if possible)
- id_numbers (list of all ID numbers found — Aadhaar, PAN, passport, licence, etc.)
- policy_number (health-insurance policy / member ID)
- policy_details (any additional policy info such as insurer name, group number, etc.)
"""


def id_agent_node(state: PipelineState) -> dict:
    """Extract identity info and write to ``extraction_results["identity"]``."""
    classifications = state["page_classifications"]
    pages = state["pages"]

    target_page_nums = [c.page_number for c in classifications if c.document_type == DocumentType.IDENTITY]

    if not target_page_nums:
        logger.info("ID Agent: no identity_document pages — skipping.")
        return {"extraction_results": {"identity": None}}

    subset = get_page_subset(pages, target_page_nums)
    page_block = "\n\n".join(f"--- PAGE {p.page_number} ---\n{p.text}" for p in subset)

    llm = get_llm()
    structured_llm = llm.with_structured_output(IdentityInfo)

    result: IdentityInfo = structured_llm.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract identity information from the following pages:\n\n{page_block}"},
        ]
    )

    logger.info("ID Agent extracted: patient=%s, ids=%s", result.patient_name, result.id_numbers)
    return {"extraction_results": {"identity": result.model_dump()}}
