"""Persist and retrieve ProcessResponse from the normalised claim tables."""

from __future__ import annotations

import json
import logging

from app.db.connection import get_pool
from app.models.schema import (
    BillLineItem,
    DischargeSummaryInfo,
    DocumentType,
    IdentityInfo,
    ItemizedBillInfo,
    PageClassification,
    ProcessResponse,
)

logger = logging.getLogger(__name__)


async def save_claim_result(response: ProcessResponse) -> int:
    """
    Insert the full pipeline output into Postgres.

    Returns the auto-generated ``claims.id`` primary key.
    """
    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            # ── 1. claims ────────────────────────────────────────────
            claim_pk: int = await conn.fetchval(
                "INSERT INTO claims (claim_id) VALUES ($1) RETURNING id",
                response.claim_id,
            )

            # ── 2. page_classifications ──────────────────────────────
            if response.segregation:
                await conn.executemany(
                    """INSERT INTO page_classifications (claim_fk, page_number, document_type, confidence)
                       VALUES ($1, $2, $3, $4)""",
                    [(claim_pk, c.page_number, c.document_type.value, c.confidence) for c in response.segregation],
                )

            # ── 3. identity_extractions ──────────────────────────────
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

            # ── 4. discharge_summaries ───────────────────────────────
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

            # ── 5. itemized_bills + bill_line_items ──────────────────
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


async def fetch_claim_result(claim_id: str) -> ProcessResponse | None:
    """Reconstruct a full ``ProcessResponse`` from Postgres by claim_id."""
    pool = get_pool()

    async with pool.acquire() as conn:
        claim_row = await conn.fetchrow("SELECT id FROM claims WHERE claim_id = $1 ORDER BY created_at DESC LIMIT 1", claim_id)
        if claim_row is None:
            return None

        claim_pk: int = claim_row["id"]

        # ── page classifications ─────────────────────────────────
        pc_rows = await conn.fetch(
            "SELECT page_number, document_type, confidence FROM page_classifications WHERE claim_fk = $1 ORDER BY page_number",
            claim_pk,
        )
        segregation = [
            PageClassification(page_number=r["page_number"], document_type=DocumentType(r["document_type"]), confidence=float(r["confidence"]))
            for r in pc_rows
        ]

        # ── identity ─────────────────────────────────────────────
        id_row = await conn.fetchrow("SELECT * FROM identity_extractions WHERE claim_fk = $1", claim_pk)
        identity = (
            IdentityInfo(
                patient_name=id_row["patient_name"],
                date_of_birth=id_row["date_of_birth"],
                id_numbers=json.loads(id_row["id_numbers"]) if id_row["id_numbers"] else [],
                policy_number=id_row["policy_number"],
                policy_details=json.loads(id_row["policy_details"]) if id_row["policy_details"] else {},
            )
            if id_row
            else None
        )

        # ── discharge summary ────────────────────────────────────
        ds_row = await conn.fetchrow("SELECT * FROM discharge_summaries WHERE claim_fk = $1", claim_pk)
        discharge_summary = (
            DischargeSummaryInfo(
                diagnosis=json.loads(ds_row["diagnosis"]) if ds_row["diagnosis"] else [],
                admission_date=ds_row["admission_date"],
                discharge_date=ds_row["discharge_date"],
                physician_name=ds_row["physician_name"],
                physician_details=json.loads(ds_row["physician_details"]) if ds_row["physician_details"] else {},
                summary=ds_row["summary"],
            )
            if ds_row
            else None
        )

        # ── itemized bill + line items ───────────────────────────
        bill_row = await conn.fetchrow("SELECT id, total_amount FROM itemized_bills WHERE claim_fk = $1", claim_pk)
        itemized_bill: ItemizedBillInfo | None = None
        if bill_row:
            item_rows = await conn.fetch(
                "SELECT description, quantity, unit_price, amount FROM bill_line_items WHERE bill_fk = $1 ORDER BY id",
                bill_row["id"],
            )
            itemized_bill = ItemizedBillInfo(
                items=[
                    BillLineItem(
                        description=r["description"],
                        quantity=float(r["quantity"]) if r["quantity"] is not None else None,
                        unit_price=float(r["unit_price"]) if r["unit_price"] is not None else None,
                        amount=float(r["amount"]),
                    )
                    for r in item_rows
                ],
                total_amount=float(bill_row["total_amount"]) if bill_row["total_amount"] is not None else None,
            )

    return ProcessResponse(
        claim_id=claim_id,
        segregation=segregation,
        identity=identity,
        discharge_summary=discharge_summary,
        itemized_bill=itemized_bill,
    )
