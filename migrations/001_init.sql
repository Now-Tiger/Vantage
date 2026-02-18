-- 001_init.sql — Claim processing pipeline schema

BEGIN;

-- Claims (parent record)
CREATE TABLE IF NOT EXISTS claims (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id      TEXT        NOT NULL,
    status        TEXT        NOT NULL DEFAULT 'processed',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_claims_claim_id ON claims (claim_id);

-- Page classifications
CREATE TABLE IF NOT EXISTS page_classifications (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_fk        BIGINT      NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    page_number     INT         NOT NULL,
    document_type   TEXT        NOT NULL,
    confidence      NUMERIC(4,3) NOT NULL,
    UNIQUE (claim_fk, page_number)
);

-- Identity extraction (1:1 per claim, nullable)
CREATE TABLE IF NOT EXISTS identity_extractions (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_fk         BIGINT  NOT NULL UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    patient_name     TEXT,
    date_of_birth    TEXT,
    id_numbers       JSONB   NOT NULL DEFAULT '[]',
    policy_number    TEXT,
    policy_details   JSONB   NOT NULL DEFAULT '{}'
);

-- Discharge summary extraction (1:1 per claim, nullable)
CREATE TABLE IF NOT EXISTS discharge_summaries (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_fk          BIGINT  NOT NULL UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    diagnosis         JSONB   NOT NULL DEFAULT '[]',
    admission_date    TEXT,
    discharge_date    TEXT,
    physician_name    TEXT,
    physician_details JSONB   NOT NULL DEFAULT '{}',
    summary           TEXT
);

-- Itemized bill extraction (1:1 per claim, nullable)
CREATE TABLE IF NOT EXISTS itemized_bills (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_fk      BIGINT   NOT NULL UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    total_amount  NUMERIC(12,2)
);

-- Bill line items (N per itemized_bill)
CREATE TABLE IF NOT EXISTS bill_line_items (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bill_fk       BIGINT        NOT NULL REFERENCES itemized_bills(id) ON DELETE CASCADE,
    description   TEXT          NOT NULL,
    quantity      NUMERIC(10,2),
    unit_price    NUMERIC(12,2),
    amount        NUMERIC(12,2) NOT NULL
);

COMMIT;
