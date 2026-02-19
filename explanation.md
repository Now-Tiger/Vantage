# LangGraph Pipeline Explanation

## 1. Workflow of LangGraph in This Project

The LangGraph workflow is built using `StateGraph` from langgraph. The pipeline flows as: START → Segregator (classifies all pages) → Conditional fan-out to extraction agents via `_route_to_agents()` → Each agent processes its relevant pages in parallel → Aggregator merges results → END. The workflow uses `Send` for dynamic fan-out, routing only to agents that have matching document types. The state is shared across all nodes via `PipelineState` TypedDict with a custom reducer for merging extraction results.

## 2. How the Segregator Agent Works

The segregator (`app/graph/nodes/segregator.py`) classifies every PDF page into one of 9 document types using an LLM with structured output. It receives the full list of pages from state, concatenates all page text with delimiters, and invokes the LLM using `SegregatorOutput` schema. The system prompt defines classification rules for types like `claim_forms`, `itemized_bill`, `discharge_summary`, `prescription`, etc. Each page gets a `PageClassification` object with `document_type`, `page_number`, and `confidence` score. Results are written to `page_classifications` in state.

## 3. How Extraction Agents Process Their Assigned Pages

Each extraction agent (bill_agent, discharge_agent, id_agent) follows the same pattern: filter pages by document type from `page_classifications`, get a subset using `get_page_subset()`, concatenate the text, and invoke the LLM with a domain-specific system prompt. The bill_agent extracts line items and total amounts into `ItemizedBillInfo`. The discharge_agent extracts diagnosis, dates, physician info into `DischargeSummaryInfo`. The id_agent extracts patient name, DOB, ID numbers, policy details into `IdentityInfo`. Each writes its result to `extraction_results` dict in state using their respective keys.

## 4. Complete Process Flow

The complete flow: (1) Input PDF is parsed into pages with text, stored in state. (2) Segregator classifies all pages into document types. (3) `_route_to_agents()` determines which extraction agents are needed based on classifications. (4) Each needed agent runs in parallel, extracting domain-specific data. (5) All extraction results flow to the aggregator. (6) Aggregator combines classifications and extractions into a final structured output with claim_id, segregation results, identity, discharge_summary, and itemized_bill. (7) Final output is returned as `final_output` in state.
