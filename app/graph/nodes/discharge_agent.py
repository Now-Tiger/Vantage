"""
Discharge Summary Agent — extracts clinical discharge details from pages
classified as ``discharge_summary``.
"""

from __future__ import annotations

import logging

from app.graph.state import PipelineState
from app.llm.provider import get_llm
from app.models.schema import DischargeSummaryInfo, DocumentType
from app.services.pdf import get_page_subset

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a medical-claim discharge-summary extraction specialist.
You will receive the text of one or more pages from a hospital discharge summary.

Extract the following fields. Return null for any field you cannot find:
- diagnosis (list of diagnosis strings)
- admission_date (format: YYYY-MM-DD if possible)
- discharge_date (format: YYYY-MM-DD if possible)
- physician_name (treating / attending doctor)
- physician_details (any extra info — designation, registration number, department, etc.)
- summary (brief clinical summary / chief complaints / treatment given)
"""


def discharge_agent_node(state: PipelineState) -> dict:
    """Extract discharge info and write to ``extraction_results["discharge_summary"]``."""
    classifications = state["page_classifications"]
    pages = state["pages"]

    target_page_nums = [c.page_number for c in classifications if c.document_type == DocumentType.DISCHARGE_SUMMARY]

    if not target_page_nums:
        logger.info("Discharge Agent: no discharge_summary pages — skipping.")
        return {"extraction_results": {"discharge_summary": None}}

    subset = get_page_subset(pages, target_page_nums)
    page_block = "\n\n".join(f"--- PAGE {p.page_number} ---\n{p.text}" for p in subset)

    llm = get_llm()
    structured_llm = llm.with_structured_output(DischargeSummaryInfo)

    result: DischargeSummaryInfo = structured_llm.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract discharge summary details from the following pages:\n\n{page_block}"},
        ]
    )

    logger.info("Discharge Agent extracted: diagnosis=%s, admit=%s, discharge=%s", result.diagnosis, result.admission_date, result.discharge_date)
    return {"extraction_results": {"discharge_summary": result.model_dump()}}
