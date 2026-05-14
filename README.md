# CreditFlow · Debt Recovery Email Agent

**Automated, LLM-powered email generation for overdue invoice collections with built-in compliance, audit trails, and escalation safeguards.**

---

## 📋 Project Overview

CreditFlow is an intelligent debt recovery automation system that:

- **Generates tone-appropriate emails** for overdue invoices using Google Gemini 1.5 Flash LLM
- **Implements escalation stages** (Stage 1–4 → Manual Review) with configurable messaging tones
- **Maintains full audit trails** via SQLite for regulatory compliance
- **Provides dual interfaces**: RESTful API (FastAPI) + Interactive UI (Streamlit)
- **Blocks automated escalation** at 30+ days overdue, requiring manual review
- **Supports dry-run mode** for safe testing and preview before sending

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-stage Escalation** | Stage 1 (Friendly) → Stage 4 (Stern) with escalation logic |
| **LLM Email Generation** | Gemini 1.5 Flash with strict JSON response mode for reliability |
| **Audit Logging** | SQLite-backed compliance trail for every action |
| **Dry-Run Mode** | Preview and test emails without dispatch |
| **Manual Review Block** | Hard stop at 30+ days overdue to prevent aggressive collection |
| **CORS-Protected API** | FastAPI with configurable frontend origin |
| **Data Validation** | Pydantic schemas for type safety and API contract enforcement |

---

## � Links

- **GitHub Repository**: https://github.com/puranpalsingh/finance-agent
- **Demo Video**: https://drive.google.com/file/d/1tVsE1gDxpWapcTNlv_yqo_rzhW8-FiHf/view?usp=sharing

---

## �🚀 Setup Instructions

### Prerequisites

- **Python 3.10+**
- **Google Gemini API Key** (for LLM email generation)
- **SMTP credentials** (optional, for production email dispatch)

### Installation

1. **Clone and navigate to the project:**
   ```bash
    git clone https://github.com/puranpalsingh/finance-agent
   ```

2. **Create a Python virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env  # or create manually
   ```

   **Required variables** (`.env`):
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Running the Application

#### **Option 1: Streamlit UI** (Interactive Dashboard)
```bash
streamlit run streamlit_app.py
```
Accessible at: `http://localhost:8501`

#### **Option 2: FastAPI Server** (REST API)
```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
API docs available at: `http://localhost:8000/docs`

---

## 🏗️ Agent Architecture

### System Diagram

```
┌──────────────────────────────────────────────────────────┐
│                     User Interface Layer                  │
├───────────────────┬──────────────────────────────────────┤
│  Streamlit UI     │      FastAPI REST API                │
│  (localhost:8501) │      (localhost:8000)                │
└────────┬──────────┴────────────────┬─────────────────────┘
         │                           │
         └───────────────┬───────────┘
                         │
         ┌───────────────▼───────────────┐
         │   Email Agent Orchestrator    │
         │   (email_agent.py)            │
         │  - Stage validation           │
         │  - Escalation blocking        │
         │  - Workflow coordination      │
         └───────┬─────────────┬─────────┘
                 │             │
      ┌──────────▼──┐   ┌──────▼─────────┐
      │   Gemini    │   │   Audit Logger │
      │   LLM       │   │   (SQLite)     │
      │   Email     │   │   Compliance   │
      │  Generator  │   │   Trail        │
      └──────┬──────┘   └────────────────┘
             │
      ┌──────▼──────────┐
      │  Email Sender   │
      │  (SMTP Mock)    │
      │  - Dry-run mode │
      │  - Logging      │
      └─────────────────┘

         Data Flow:
    CSV → Pandas → Pydantic → Agent → LLM → Email → Log
```

### Component Overview

| Component | Role | Tech Stack |
|-----------|------|-----------|
| **Email Agent** | Orchestrates invoice→email→send workflow | Python |
| **Email Generator** | Calls Gemini LLM with stage-specific prompts | `google-generativeai` |
| **Email Sender** | Simulates SMTP dispatch, logs output | Python SMTP (mocked) |
| **Audit Logger** | Persists all actions for compliance | SQLite3 |
| **Data Ingestion** | Parses CSV invoices, enriches with days_overdue | Pandas |
| **FastAPI Server** | Exposes REST endpoints for integration | FastAPI |
| **Streamlit UI** | Interactive dashboard for manual operations | Streamlit |

### Data Flow

1. **CSV Upload/Load** → `parse_csv_file()` (Pandas)
2. **Compute Status** → Days overdue, escalation stage
3. **Validate Stage** → Block if "Escalated" (30+ days overdue)
4. **Generate Email** → Call Gemini with stage-specific system instruction
5. **Audit Log** → Record to SQLite (timestamp, stage, tone, status)
6. **Send (or Dry-run)** → Simulate SMTP dispatch
7. **Return Response** → Subject, body, audit_id, manual_review flag

---

## 🤖 LLM & Framework Choices

### Gemini 1.5 Flash – Rationale

| Criterion | Choice | Why |
|-----------|--------|-----|
| **Model** | Google Gemini 1.5 Flash | Fast, cost-effective, excellent JSON mode support |
| **Response Format** | Strict JSON (`application/json`) | Guaranteed structured output; enables reliable parsing |
| **Temperature** | 0.4 (low) | Consistent, professional tone; reduces hallucination |
| **Max Tokens** | Implicit (< 1000 for emails) | Efficient and predictable costs |

**Benefits:**
- ✅ **Rapid inference** (~1–2s per email)
- ✅ **Cost-effective** (~$0.075/M input, $0.30/M output tokens)
- ✅ **Built-in safety** with system instructions and guardrails
- ✅ **Reliable JSON parsing** eliminates string-manipulation brittleness

### Framework Stack – Rationale

| Layer | Framework | Why |
|-------|-----------|-----|
| **API Server** | FastAPI | Type-safe, auto-generated OpenAPI docs, built-in CORS |
| **Data Validation** | Pydantic | Runtime schema validation, JSON serialization |
| **UI** | Streamlit | Rapid prototyping, no frontend code required |
| **Data Processing** | Pandas | Efficient CSV parsing, vectorized operations |
| **Database** | SQLite | Zero-setup audit trail, ACID transactions, compliance-ready |

**Advantages:**
- 🔒 **Type safety** (Pydantic) prevents injection attacks
- 📊 **Structured logging** (SQLite) enables audit and compliance reviews
- 🎯 **Minimal infrastructure** (no external DB, SMTP mocking)
- 🔄 **Easy testing** (dry-run mode, simulated sends)

---

## 🔐 Security Mitigations

### 1. **Escalation Hard Block**
- **Risk**: Aggressive over-collection on severely overdue invoices
- **Mitigation**: Any invoice 30+ days overdue is marked "Escalated" and **blocked from automation**; requires manual review
- **Code**: [`agents/email_agent.py`](agents/email_agent.py#L15-L31)

```python
if stage == "Escalated":
    return {
        "send_status": "blocked_escalated",
        "manual_review": True,
        "message": "Manual Review Required — this invoice has exceeded 30 days overdue."
    }
```

### 2. **LLM Guardrails**
- **Risk**: LLM may generate threatening or illegal collection language
- **Mitigation**: 
  - Stage-specific system instructions enforce tone boundaries
  - Guardrail instruction appended to all prompts
  - Low temperature (0.4) reduces deviation from prompt intent
- **Code**: [`prompts/email_prompts.py`](prompts/email_prompts.py)

```python
GUARDRAIL_INSTRUCTION = """
You MUST NOT:
- Make threats or use aggressive language
- Violate FDCPA regulations
- Disclose debt to third parties without consent
- Make false claims about legal action
"""
```

### 3. **Full Audit Trail**
- **Risk**: No accountability for actions taken
- **Mitigation**: Every email generation, tone choice, and send attempt is logged to SQLite with:
  - Timestamp (UTC)
  - Invoice details
  - Escalation stage
  - Email tone applied
  - Send status (sent, dry_run, blocked_escalated)
- **Queries**: All logs queryable by date, invoice, stage
- **Code**: [`services/audit_logger.py`](services/audit_logger.py)

### 4. **Dry-Run Mode**
- **Risk**: Accidental dispatch to customers
- **Mitigation**: Default behavior is `dry_run=True`; all emails logged to console without SMTP dispatch
- **Code**: [`services/email_sender.py`](services/email_sender.py#L25-L30)

### 5. **Input Validation (Pydantic)**
- **Risk**: Malformed data, injection attacks
- **Mitigation**: All API payloads validated against strict schemas
  - `InvoiceComputed` ensures valid dates, numeric amounts
  - `EmailGenerationRequest` enforces required fields
- **Code**: [`models/schemas.py`](models/schemas.py)

### 6. **CORS Protection**
- **Risk**: Cross-site requests from unauthorized origins
- **Mitigation**: FastAPI CORS middleware restricted to `FRONTEND_ORIGIN` env var
- **Code**: [`main.py`](main.py#L35-L40)



### 7. **Environment Variable Isolation**
- **Risk**: API keys, credentials hardcoded in source
- **Mitigation**: All secrets loaded from `.env` via `python-dotenv`; `.env` excluded from version control
- **Code**: [`main.py`](main.py#L10)

```python
from dotenv import load_dotenv
load_dotenv()
_API_KEY = os.getenv("GEMINI_API_KEY", "")
```

### 8. **Simulated Email Dispatch** (No Real SMTP)
- **Risk**: Accidental production sends during development
- **Mitigation**: Email sender mocks SMTP; all sends logged to console, never dispatched
- **Note**: Production deployment requires SMTP credential management and explicit `dry_run=False` toggle
- **Code**: [`services/email_sender.py`](services/email_sender.py#L14)

### 9. **Stage-Specific Prompt Engineering**
- **Risk**: Inconsistent tone, off-brand messaging
- **Mitigation**: Four escalation stages, each with distinct system instruction
  - Stage 1: "Warm & Friendly" (first notice)
  - Stage 2: "Polite but Firm" (second notice)
  - Stage 3: "Formal & Serious" (third notice)
  - Stage 4: "Stern & Urgent" (final notice before escalation)
- **Code**: [`prompts/email_prompts.py`](prompts/email_prompts.py)

---

## 📁 Project Structure

```
finance-email-agent/
├── main.py                      # FastAPI entry point
├── streamlit_app.py             # Streamlit UI
├── requirements.txt             # Dependencies
├── style.css                    # Streamlit styling
├── .env.example                 # Environment template
├── README.md                    # This file
│
├── agents/
│   ├── __init__.py
│   └── email_agent.py           # Orchestrator: validate → generate → send → log
│
├── models/
│   ├── __init__.py
│   └── schemas.py               # Pydantic models for API contracts
│
├── prompts/
│   ├── __init__.py
│   └── email_prompts.py         # Stage-specific system instructions & guardrails
│
├── services/
│   ├── __init__.py
│   ├── data_ingestion.py        # CSV parsing, invoice enrichment
│   ├── email_generator.py       # Gemini LLM integration
│   ├── email_sender.py          # Simulated SMTP dispatch
│   └── audit_logger.py          # SQLite compliance logging
│
└── data/
    ├── invoices.csv             # Sample invoice data
    └── audit.db                 # SQLite audit trail (auto-created)
```

---

## 🧪 Testing

### Quick Test (Streamlit UI)
```bash
streamlit run streamlit_app.py
# Upload data/invoices.csv
# Select an invoice → click "Generate Email"
# Verify output in Streamlit + console logs
```

### API Test (cURL)
```bash
# Get all invoices
curl http://localhost:8000/api/invoices

# Generate email
curl -X POST http://localhost:8000/api/generate-email \
  -H "Content-Type: application/json" \
  -d '{"invoice": {"invoice_no": "INV001", ...}}'

# View audit logs
curl http://localhost:8000/api/audit-logs
```

### Dry-Run Mode (Default)
All email sends are simulated and logged to console:
```
═══════════════════════════════════════════════════
  📧 SIMULATED EMAIL DRY RUN
═══════════════════════════════════════════════════
  Status   : dry_run
  To       : customer@example.com
  Subject  : We Noticed Your Invoice is Due
  Time     : 2026-05-14T10:30:45.123456
  Body Preview: Dear John Smith, We hope this message finds you well...
═══════════════════════════════════════════════════
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/invoices` | Fetch all invoices with escalation status |
| `POST` | `/api/generate-email` | Generate email for an invoice (no dispatch) |
| `POST` | `/api/send-email` | Send email + audit log (supports dry_run flag) |
| `GET` | `/api/audit-logs` | Retrieve all audit records (queryable by date, stage) |
| `GET` | `/api/sent-today` | Count of emails sent today |
| `POST` | `/api/upload-csv` | Upload custom CSV file |

---

## 🛠️ Development

### Adding a New Escalation Stage
1. Define stage in [`prompts/email_prompts.py`](prompts/email_prompts.py) under `STAGE_PROMPTS`
2. Add system instruction with tone and guardrails
3. Update Streamlit UI color/tone mappings
4. Re-run tests

### Customizing LLM Behavior
- **Temperature**: Adjust in [`services/email_generator.py`](services/email_generator.py#L48) (0.0–1.0)
- **System Instructions**: Edit [`prompts/email_prompts.py`](prompts/email_prompts.py)
- **Response Format**: Modify JSON schema validation in email generation

### Database Queries
```bash
sqlite3 data/audit.db
SELECT * FROM audit_log WHERE stage='Escalated' ORDER BY timestamp DESC;
```

---

## 📝 License

Internal Use Only

---

## 📞 Support

For issues or questions:
1. Check `.env` configuration
2. Verify Gemini API key is active
3. Review audit logs: `sqlite3 data/audit.db "SELECT * FROM audit_log LIMIT 10;"`
4. Check console output for LLM errors or validation failures

---