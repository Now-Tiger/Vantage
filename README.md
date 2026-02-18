# Vantage

AI-powered claim document processing service. Upload a PDF claim, and the system classifies each page and extracts structured data using a multi-agent LangGraph pipeline.

## How It Works

```
POST /api/process (claim_id + PDF)
           │
   Segregator Agent ─── LLM classifies each page into 9 document types
           │
   ┌───────┼────────────┐   (parallel, only invoked if matching pages exist)
   │       │            │
 ID    Discharge   Itemized
Agent    Agent     Bill Agent
   │       │            │
   └───────┼────────────┘
           │
    Aggregator ─── merges results into a single JSON response
```

**Segregator** classifies pages into: `claim_forms`, `cheque_or_bank_details`, `identity_document`, `itemized_bill`, `discharge_summary`, `prescription`, `investigation_report`, `cash_receipt`, `other`.

**Three extraction agents** run in parallel on their assigned pages:

- **ID Agent** — patient name, DOB, ID numbers, policy details
- **Discharge Summary Agent** — diagnosis, admit/discharge dates, physician info
- **Itemized Bill Agent** — line items with costs, total amount

## Tech Stack

- **FastAPI** — async API server
- **LangGraph** — orchestrates the multi-agent workflow (StateGraph + Send fan-out)
- **LangChain** — LLM abstraction (OpenAI / Anthropic)
- **pdfplumber** — text extraction from PDF pages
- **Docker Compose** — containerised deployment with PostgreSQL

## Quick Start

```bash
# Build service
make build

# Start services
make up

# View logs
make logs

# Stop services
make down

# Connect to database
make psql
```

## Setup

### Prerequisites

- Python 3.13+ and [uv](https://github.com/astral-sh/uv)
- Docker & Docker Compose (for containerised run)
- An OpenAI or Anthropic API key

### 1. Environment variables

Copy and fill in the `.env` file. The key variables:

```
LLM_PROVIDER=openai          # or "anthropic"
LLM_MODEL=gpt-4o             # model name
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MAX_PDF_SIZE_MB=20
LANGGRAPH_RECURSION_LIMIT=25
```

### 2. Run locally

```bash
uv sync                              # install dependencies
uvicorn app.main:app --reload        # start on http://localhost:8000
```

### 3. Run with Docker

```bash
make build && make up                # build image & start services
make logs                            # tail API logs
```

### 4. Test the endpoint

```bash
curl -X POST http://localhost:8000/api/process \
  -F "claim_id=CLM-001" \
  -F "file=@/path/to/claim.pdf"
```

### Response returned

```json
{
  "claim_id": "claim-20260218-608502",
  "segregation": [
    {
      "page_number": 1,
      "document_type": "claim_forms",
      "confidence": 0.95
    },
    {
      "page_number": 2,
      "document_type": "cheque_or_bank_details",
      "confidence": 0.9
    },
    {
      "page_number": 3,
      "document_type": "identity_document",
      "confidence": 0.85
    },
    {
      "page_number": 4,
      "document_type": "discharge_summary",
      "confidence": 0.98
    },
    {
      "page_number": 5,
      "document_type": "prescription",
      "confidence": 0.99
    },
    {
      "page_number": 6,
      "document_type": "investigation_report",
      "confidence": 0.95
    },
    {
      "page_number": 7,
      "document_type": "cash_receipt",
      "confidence": 0.9
    },
    {
      "page_number": 8,
      "document_type": "other",
      "confidence": 0.7
    },
    {
      "page_number": 9,
      "document_type": "itemized_bill",
      "confidence": 0.99
    },
    {
      "page_number": 10,
      "document_type": "itemized_bill",
      "confidence": 0.95
    },
    {
      "page_number": 11,
      "document_type": "investigation_report",
      "confidence": 0.95
    },
    {
      "page_number": 12,
      "document_type": "investigation_report",
      "confidence": 0.95
    },
    {
      "page_number": 13,
      "document_type": "other",
      "confidence": 0.85
    },
    {
      "page_number": 14,
      "document_type": "other",
      "confidence": 0.8
    },
    {
      "page_number": 15,
      "document_type": "other",
      "confidence": 0.75
    },
    {
      "page_number": 16,
      "document_type": "other",
      "confidence": 0.7
    },
    {
      "page_number": 17,
      "document_type": "other",
      "confidence": 0.8
    },
    {
      "page_number": 18,
      "document_type": "other",
      "confidence": 0.75
    }
  ],
  "identity": {
    "patient_name": "JOHN MICHAEL SMITH",
    "date_of_birth": "1985-03-15",
    "id_numbers": ["ID-987-654-321"],
    "policy_number": null,
    "policy_details": {
      "issuer": "Department of Motor Vehicles",
      "issue_date": "2023-01-15",
      "expiry_date": "2033-01-15"
    }
  },
  "discharge_summary": {
    "diagnosis": ["Community Acquired Pneumonia (CAP)"],
    "admission_date": "2025-01-20",
    "discharge_date": "2025-01-25",
    "physician_name": "Dr. Sarah Johnson",
    "physician_details": {
      "designation": "MD"
    },
    "summary": "Patient admitted with fever, cough, and shortness of breath. Chest X-ray confirmed right lower lobe pneumonia. Started on IV antibiotics (Ceftriaxone 1g daily). Patient showed gradual improvement with resolution of fever by day 3. Oxygen saturation improved to 96% on room air. Repeat chest X-ray showed improvement."
  },
  "itemized_bill": {
    "items": [
      {
        "description": "Room Charges - Semi-Private (5 days)",
        "quantity": 5,
        "unit_price": 200,
        "amount": 1000
      },
      {
        "description": "Admission Fee",
        "quantity": 1,
        "unit_price": 150,
        "amount": 150
      },
      {
        "description": "Emergency Room Services",
        "quantity": 1,
        "unit_price": 500,
        "amount": 500
      },
      {
        "description": "Physician Consultation - Dr. Sarah Johnson",
        "quantity": 5,
        "unit_price": 150,
        "amount": 750
      },
      {
        "description": "Chest X-Ray",
        "quantity": 2,
        "unit_price": 120,
        "amount": 240
      },
      {
        "description": "CT Scan - Chest",
        "quantity": 1,
        "unit_price": 800,
        "amount": 800
      },
      {
        "description": "Complete Blood Count (CBC)",
        "quantity": 3,
        "unit_price": 45,
        "amount": 135
      },
      {
        "description": "Blood Culture Test",
        "quantity": 2,
        "unit_price": 80,
        "amount": 160
      },
      {
        "description": "Arterial Blood Gas Analysis",
        "quantity": 1,
        "unit_price": 95,
        "amount": 95
      },
      {
        "description": "IV Fluids - Normal Saline",
        "quantity": 10,
        "unit_price": 25,
        "amount": 250
      },
      {
        "description": "Injection - Ceftriaxone 1g",
        "quantity": 5,
        "unit_price": 30,
        "amount": 150
      },
      {
        "description": "Injection - Paracetamol",
        "quantity": 6,
        "unit_price": 8,
        "amount": 48
      },
      {
        "description": "Nebulization Treatment",
        "quantity": 4,
        "unit_price": 35,
        "amount": 140
      },
      {
        "description": "Oxygen Therapy (per hour)",
        "quantity": 48,
        "unit_price": 5,
        "amount": 240
      },
      {
        "description": "Nursing Care (per day)",
        "quantity": 5,
        "unit_price": 100,
        "amount": 500
      },
      {
        "description": "ICU Monitoring Equipment",
        "quantity": 2,
        "unit_price": 200,
        "amount": 400
      },
      {
        "description": "Physiotherapy Session",
        "quantity": 3,
        "unit_price": 60,
        "amount": 180
      },
      {
        "description": "Medical Supplies & Consumables",
        "quantity": 1,
        "unit_price": 250,
        "amount": 250
      },
      {
        "description": "Laboratory Processing Fee",
        "quantity": 1,
        "unit_price": 75,
        "amount": 75
      },
      {
        "description": "Pharmacy Dispensing Fee",
        "quantity": 1,
        "unit_price": 50,
        "amount": 50
      },
      {
        "description": "Subtotal",
        "quantity": null,
        "unit_price": null,
        "amount": 6113
      },
      {
        "description": "Tax (5%)",
        "quantity": null,
        "unit_price": null,
        "amount": 305.65
      },
      {
        "description": "Total Amount",
        "quantity": null,
        "unit_price": null,
        "amount": 6418.65
      },
      {
        "description": "Insurance Payment (80%)",
        "quantity": null,
        "unit_price": null,
        "amount": -5134.92
      },
      {
        "description": "Patient Responsibility (20%)",
        "quantity": null,
        "unit_price": null,
        "amount": 1283.73
      },
      {
        "description": "Amoxicillin 500mg Capsules",
        "quantity": 21,
        "unit_price": 1.5,
        "amount": 31.5
      },
      {
        "description": "Acetaminophen 500mg Tablets",
        "quantity": 20,
        "unit_price": 0.8,
        "amount": 16
      },
      {
        "description": "Cetirizine 10mg Tablets",
        "quantity": 10,
        "unit_price": 0.9,
        "amount": 9
      },
      {
        "description": "Omeprazole 20mg Capsules",
        "quantity": 14,
        "unit_price": 1.2,
        "amount": 16.8
      },
      {
        "description": "Albuterol Inhaler",
        "quantity": 1,
        "unit_price": 35,
        "amount": 35
      },
      {
        "description": "Vitamin D3 1000 IU",
        "quantity": 30,
        "unit_price": 0.4,
        "amount": 12
      },
      {
        "description": "Probiotic Capsules",
        "quantity": 30,
        "unit_price": 0.85,
        "amount": 25.5
      },
      {
        "description": "Saline Nasal Spray",
        "quantity": 1,
        "unit_price": 8.5,
        "amount": 8.5
      },
      {
        "description": "Antiseptic Mouthwash",
        "quantity": 1,
        "unit_price": 12,
        "amount": 12
      },
      {
        "description": "Digital Thermometer",
        "quantity": 1,
        "unit_price": 15,
        "amount": 15
      },
      {
        "description": "Medication Counseling",
        "quantity": 1,
        "unit_price": 25,
        "amount": 25
      },
      {
        "description": "Home Delivery Service",
        "quantity": 1,
        "unit_price": 10,
        "amount": 10
      },
      {
        "description": "Subtotal",
        "quantity": null,
        "unit_price": null,
        "amount": 216.3
      },
      {
        "description": "Discount (10%)",
        "quantity": null,
        "unit_price": null,
        "amount": -21.63
      },
      {
        "description": "Tax (6%)",
        "quantity": null,
        "unit_price": null,
        "amount": 11.68
      },
      {
        "description": "TOTAL DUE",
        "quantity": null,
        "unit_price": null,
        "amount": 206.35
      }
    ],
    "total_amount": 6418.65
  }
}
```

## API

| Method | Path           | Description                                          |
| ------ | -------------- | ---------------------------------------------------- |
| `POST` | `/api/process` | Process a PDF claim (multipart: `claim_id` + `file`) |
| `GET`  | `/health`      | Health check                                         |

## Project Structure

```
app/
├── main.py                  # FastAPI app entry point
├── api/routes.py            # /api/process endpoint
├── core/config.py           # Pydantic settings (.env)
├── llm/provider.py          # LLM client (OpenAI / Anthropic)
├── models/schema.py         # Pydantic models (request, response, extraction types)
├── services/pdf.py          # Parallel PDF text extraction
└── graph/
    ├── state.py             # LangGraph PipelineState (TypedDict + reducers)
    ├── workflow.py           # Graph wiring (START → segregator → agents → aggregator → END)
    └── nodes/
        ├── segregator.py    # Page classification agent
        ├── id_agent.py      # Identity document extraction
        ├── discharge_agent.py # Discharge summary extraction
        ├── bill_agent.py    # Itemized bill extraction
        └── aggregator.py    # Merges all results into final output
```

## License

MIT
