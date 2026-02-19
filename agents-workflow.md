# Agents Workflow Documentation

This document provides a summary of each file in the `app/graph/` folder.

---

## File: app/graph/state.py

Defines `PipelineState`, a TypedDict that serves as the shared state for the LangGraph claim-processing pipeline. It includes fields for `claim_id`, `pages` (list of PageData), `page_classifications`, `extraction_results` (a merged dictionary), and `final_output`. A reducer function `_merge_dicts` is used to shallow-merge dictionaries for the extraction results.

---

## File: app/graph/workflow.py

Builds the complete LangGraph workflow for claim processing. It wires five nodes: segregator, id_agent, discharge_agent, bill_agent, and aggregator. The workflow starts with the segregator, then uses conditional routing to fan out to appropriate extraction agents based on page classifications. All agents feed into the aggregator, which produces the final output. A mapping `AGENT_FOR_DOC_TYPE` routes document types to their respective agents.

---

## File: app/graph/nodes/bill_agent.py

The Bill Agent extracts line-item charges and computes the total amount from pages classified as `itemized_bill`. It uses an LLM with structured output to parse hospital bill details into `ItemizedBillInfo` objects. The agent identifies relevant pages, combines their text, invokes the LLM, and calculates the total if not provided. Results are stored under `extraction_results["itemized_bill"]`.

---

## File: app/graph/nodes/aggregator.py

The Aggregator node combines all extraction agent results into the final structured output. It retrieves results from identity, discharge summary, and itemized bill extractions, then constructs a final dictionary containing claim_id, segregation data, and all three document types. Each result is validated against its corresponding Pydantic model before being added to the output.

---

## File: app/graph/nodes/segregator.py

The Segregator agent classifies every PDF page into one of nine document types: claim_forms, cheque_or_bank_details, identity_document, itemized_bill, discharge_summary, prescription, investigation_report, cash_receipt, and other. It uses an LLM with a structured output model (`SegregatorOutput`) to analyze page text and assign types with confidence scores. Results are stored in `page_classifications`.

---

## File: app/graph/nodes/discharge_agent.py

The Discharge Summary Agent extracts clinical details from pages classified as `discharge_summary`. It extracts fields like diagnosis, admission/discharge dates, physician name, physician details, and a clinical summary using an LLM with structured output. Relevant pages are filtered and combined before being processed, with results stored under `extraction_results["discharge_summary"]`.

---

## File: app/graph/nodes/id_agent.py

The ID Agent extracts identity and policy information from pages classified as `identity_document`. It uses an LLM to extract patient name, date of birth, ID numbers (Aadhaar, PAN, etc.), policy number, and policy details. The agent filters pages by document type, combines their text, invokes the LLM, and stores results under `extraction_results["identity"]`.
