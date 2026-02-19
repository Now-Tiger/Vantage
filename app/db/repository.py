"""Persist and retrieve ProcessResponse from the normalised claim tables."""

from __future__ import annotations

import json
import logging

from app.db.connection import get_pool
from app.models.schema import (
    BillLineItem,
    ClaimSummary,
    DischargeSummaryInfo,
    DocumentType,
    IdentityInfo,
    ItemizedBillInfo,
    PageClassification,
    ProcessResponse,
)

logger = logging.getLogger(__name__)


# Write
async def save_claim_result(response: ProcessResponse) -> int:
    """Insert the full pipeline output into Postgres in a single transaction."""
    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            claim_pk: int = await conn.fetchval(
                "INSERT INTO claims (claim_id) VALUES ($1) RETURNING id",
                response.claim_id,
            )

            if response.segregation:
                await conn.executemany(
                    """INSERT INTO page_classifications (claim_fk, page_number, document_type, confidence)
                       VALUES ($1, $2, $3, $4)""",
                    [(claim_pk, c.page_number, c.document_type.value, c.confidence) for c in response.segregation],
                )

            if response.identity:
                ident = response.identity
                await conn.execute(
                    """INSERT INTO identity_extractions
                       (claim_fk, patient_name, date_of_birth, id_numbers, policy_number, policy_details)
                       VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb)""",
                    claim_pk,
                    ident.patient_name,
                    ident.date_of_birth,
                    json.dumps(ident.id_numbers),
                    ident.policy_number,
                    json.dumps(ident.policy_details),
                )

            if response.discharge_summary:
                ds = response.discharge_summary
                await conn.execute(
                    """INSERT INTO discharge_summaries
                       (claim_fk, diagnosis, admission_date, discharge_date,
                        physician_name, physician_details, summary)
                       VALUES ($1, $2::jsonb, $3, $4, $5, $6::jsonb, $7)""",
                    claim_pk,
                    json.dumps(ds.diagnosis),
                    ds.admission_date,
                    ds.discharge_date,
                    ds.physician_name,
                    json.dumps(ds.physician_details),
                    ds.summary,
                )

            if response.itemized_bill:
                bill = response.itemized_bill
                bill_pk: int = await conn.fetchval(
                    """INSERT INTO itemized_bills (claim_fk, total_amount)
                       VALUES ($1, $2) RETURNING id""",
                    claim_pk,
                    bill.total_amount,
                )
                if bill.items:
                    await conn.executemany(
                        """INSERT INTO bill_line_items
                           (bill_fk, description, quantity, unit_price, amount)
                           VALUES ($1, $2, $3, $4, $5)""",
                        [(bill_pk, it.description, it.quantity, it.unit_price, it.amount) for it in bill.items],
                    )

    logger.info("Saved claim result pk=%d for claim_id=%s", claim_pk, response.claim_id)
    return claim_pk


# Single-query fetch (1 round-trip)

_FETCH_ONE_SQL = """
SELECT
    c.claim_id,
    COALESCE(
        (SELECT json_agg(json_build_object(
            'page_number', pc.page_number,
            'document_type', pc.document_type,
            'confidence', pc.confidence
        ) ORDER BY pc.page_number)
        FROM page_classifications pc WHERE pc.claim_fk = c.id),
        '[]'::json
    ) AS segregation,

    (SELECT row_to_json(t) FROM (
        SELECT patient_name, date_of_birth, id_numbers, policy_number, policy_details
        FROM identity_extractions WHERE claim_fk = c.id
    ) t) AS identity,

    (SELECT row_to_json(t) FROM (
        SELECT diagnosis, admission_date, discharge_date,
               physician_name, physician_details, summary
        FROM discharge_summaries WHERE claim_fk = c.id
    ) t) AS discharge_summary,

    (SELECT json_build_object(
        'total_amount', ib.total_amount,
        'items', COALESCE(
            (SELECT json_agg(json_build_object(
                'description', bli.description,
                'quantity', bli.quantity,
                'unit_price', bli.unit_price,
                'amount', bli.amount
            ) ORDER BY bli.id)
            FROM bill_line_items bli WHERE bli.bill_fk = ib.id),
            '[]'::json
        )
    ) FROM itemized_bills ib WHERE ib.claim_fk = c.id) AS itemized_bill

FROM claims c
WHERE c.claim_id = $1
ORDER BY c.created_at DESC
LIMIT 1;
"""


def _parse_row(row) -> ProcessResponse:
    """Hydrate a ProcessResponse from a single aggregated DB row."""
    seg_raw = row["segregation"] if isinstance(row["segregation"], list) else json.loads(row["segregation"])
    segregation = [
        PageClassification(page_number=s["page_number"], document_type=DocumentType(s["document_type"]), confidence=float(s["confidence"]))
        for s in seg_raw
    ]

    id_raw = row["identity"]
    if id_raw and isinstance(id_raw, str):
        id_raw = json.loads(id_raw)
    identity = IdentityInfo(**id_raw) if id_raw else None

    ds_raw = row["discharge_summary"]
    if ds_raw and isinstance(ds_raw, str):
        ds_raw = json.loads(ds_raw)
    discharge_summary = DischargeSummaryInfo(**ds_raw) if ds_raw else None

    bill_raw = row["itemized_bill"]
    if bill_raw and isinstance(bill_raw, str):
        bill_raw = json.loads(bill_raw)
    itemized_bill = None
    if bill_raw:
        itemized_bill = ItemizedBillInfo(
            total_amount=float(bill_raw["total_amount"]) if bill_raw["total_amount"] is not None else None,
            items=[BillLineItem(**it) for it in bill_raw.get("items", [])],
        )

    return ProcessResponse(
        claim_id=row["claim_id"],
        segregation=segregation,
        identity=identity,
        discharge_summary=discharge_summary,
        itemized_bill=itemized_bill,
    )


async def fetch_claim_result(claim_id: str) -> ProcessResponse | None:
    """Fetch a full claim in a single DB round-trip."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_FETCH_ONE_SQL, claim_id)
    if row is None:
        return None
    return _parse_row(row)


# List all claims
_LIST_SQL = """
SELECT claim_id, status, created_at
FROM claims
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;
"""

_COUNT_SQL = "SELECT count(*) FROM claims;"


async def fetch_all_claims(limit: int = 20, offset: int = 0) -> tuple[list[ClaimSummary], int]:
    """Return paginated claim summaries and total count."""
    pool = get_pool()
    async with pool.acquire() as conn:
        total: int = await conn.fetchval(_COUNT_SQL)
        rows = await conn.fetch(_LIST_SQL, limit, offset)

    items = [
        ClaimSummary(claim_id=r["claim_id"], status=r["status"], created_at=r["created_at"])
        for r in rows
    ]
    return items, total
