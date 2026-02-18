"""
Itemized Bill Agent — extracts line-item charges and computes the total
from pages classified as ``itemized_bill``.
"""

from __future__ import annotations

import logging

from app.graph.state import PipelineState
from app.llm.provider import get_llm
from app.models.schema import DocumentType, ItemizedBillInfo
from app.services.pdf import get_page_subset

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a medical-claim itemized-bill extraction specialist.
You will receive the text of one or more pages from a hospital itemized bill.

Extract every line item and the overall total:
- items: list of objects, each with:
    - description (name of service / product)
    - quantity (number of units, null if not stated)
    - unit_price (per-unit cost, null if not stated)
    - amount (total charge for that line item)
- total_amount: the grand total of the bill.  If the document states a
  total, use that value.  Otherwise sum the individual item amounts.

Rules:
- Capture ALL line items even if some fields are missing.
- Monetary values should be plain numbers (no currency symbols).
- If a page contains subtotals or tax rows, include them as separate items.
"""


def bill_agent_node(state: PipelineState) -> dict:
    """Extract bill items and write to ``extraction_results["itemized_bill"]``."""
    classifications = state["page_classifications"]
    pages = state["pages"]

    target_page_nums = [c.page_number for c in classifications if c.document_type == DocumentType.ITEMIZED_BILL]

    if not target_page_nums:
        logger.info("Bill Agent: no itemized_bill pages — skipping.")
        return {"extraction_results": {"itemized_bill": None}}

    subset = get_page_subset(pages, target_page_nums)
    page_block = "\n\n".join(f"--- PAGE {p.page_number} ---\n{p.text}" for p in subset)

    llm = get_llm()
    structured_llm = llm.with_structured_output(ItemizedBillInfo)

    result: ItemizedBillInfo = structured_llm.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract all bill line items from the following pages:\n\n{page_block}"},
        ]
    )

    if result.total_amount is None and result.items:
        result.total_amount = sum(item.amount for item in result.items)

    logger.info("Bill Agent extracted %d item(s), total=%.2f", len(result.items), result.total_amount or 0)
    return {"extraction_results": {"itemized_bill": result.model_dump()}}
