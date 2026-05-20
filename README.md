# GreenPack EPR Compliance Service

A Python/FastAPI backend that helps GreenPack Industries comply with India's EPR (Extended Producer Responsibility) plastic-packaging rules. Three endpoints: monthly declaration intake, ERP reconciliation with LLM narrative, and a RAG-powered compliance Q&A.

---

## Demo Video

**Loom:** https://www.loom.com/share/bc956977bcd745b9a81d8dba951343c6

---

## Stack Choices

| Concern | Choice | Why |
|---|---|---|
| **Framework** | FastAPI | Async, typed, auto-generates OpenAPI docs — ideal for API-first work |
| **LLM** | Llama 3.2 1b via Ollama (local) | Completely free, no API key, runs on-device — zero cloud cost, no data leaves the machine |
| **Embedding model** | `all-MiniLM-L6-v2` (sentence-transformers) | Free, runs locally, 384-dim vectors — sufficient for a 5-doc corpus |
| **Vector store** | ChromaDB (persistent) | Zero infra to run, Python-native, persists to disk so re-indexing only happens once |
| **Storage** | SQLite | No server setup, ACID guarantees, built into Python |
| **AI coding assistant** | Claude Code (Anthropic CLI) | Used throughout — scaffolding, reconciliation logic, RAG chunking, corpus documents |

---

## Why Ollama Instead of Claude / OpenAI / Gemini

The task brief explicitly states:
> *"To avoid all spend, run a local model with Ollama — that is exactly the workflow we use."*

I chose Ollama with `llama3.2:1b` for these reasons:

1. **Zero cost** — no API key, no credit card, no free-tier limits to hit during evaluation
2. **Runs offline** — the evaluator can clone and run this without any external account setup
3. **Privacy** — no data sent to any cloud provider
4. **Matches the company's own workflow** — the brief says this is what Innotechwise uses day-to-day

The `openai` Python package is used purely as a client library — it is pointed at `http://localhost:11434` (Ollama's local server), not at OpenAI's servers. No OpenAI account or key is needed.

---

## Architecture Overview

```
POST /submit
  └─ Pydantic validation (no LLM) → SQLite

GET /summary/{producer_id}/{month}
  └─ SQLite → deterministic reconciliation → Llama 3.2 narrative (Ollama, local)

POST /ask
  └─ Question → all-MiniLM-L6-v2 embedding → ChromaDB retrieves top-4 chunks
              → Llama 3.2 answers using only retrieved chunks (Ollama, local)
```

**Key judgment calls:**
- `/submit` has **zero LLM calls** — validation is deterministic; an LLM adds latency, cost, and unpredictability for no benefit
- `/summary` LLM handles **narrative only** — all numbers come from deterministic Python
- `/ask` uses a strict RAG prompt — if the answer is not in the corpus the model returns `"I do not know based on the provided documents."` to prevent hallucination

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Tanmayjagnade/Innotechwise_Screening_task.git
cd Innotechwise_Screening_task
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Install Ollama and pull the model

Download Ollama from https://ollama.com/download, then:

```bash
ollama pull llama3.2:1b
```

No API key needed — everything runs locally and free.

### 3. Run the server

```bash
python main.py
```

The server starts at `http://localhost:8000`.
First startup downloads the `all-MiniLM-L6-v2` embedding model (~90 MB) and indexes the five corpus documents into ChromaDB. Subsequent startups are fast.

Interactive API docs: `http://localhost:8000/docs`

---

## Running the Demo

```bash
# Mac/Linux
bash demo.sh

# Windows PowerShell
.\demo.ps1
```

---

## Endpoints

### `POST /submit`
Submit GreenPack's monthly plastic declaration. Pure deterministic validation — no LLM.

```json
{
  "producer_id": "GREENPACK-001",
  "month": "2026-04",
  "declared_quantities_kg": {
    "rigid_plastic": 12000,
    "flexible_plastic": 8500,
    "multilayer_plastic": 3200
  }
}
```

**Validates:** required fields present, YYYY-MM month format, no negative quantities.

---

### `GET /summary/{producer_id}/{month}`

Reconciles the stored declaration against `data/erp_feed.csv`. Flags any category with >5% deviation. Returns structured reconciliation + LLM-generated narrative.

```
GET /summary/GREENPACK-001/2026-04
```

---

### `POST /ask`

RAG Q&A over five EPR policy documents.

```json
{ "question": "What are the EPR targets for multilayer plastic in FY 2026-27?" }
```

Returns `answer` + `citations` (document name + section).
Returns `"I do not know based on the provided documents."` for out-of-scope questions.

**Sample questions to try:**
- `"What are the EPR registration requirements for plastic producers?"`
- `"What is the penalty for missing the annual return deadline?"`
- `"What is the difference between rigid and multilayer plastic?"`
- `"When must EPR certificates be surrendered?"`

---

## Knowledge Base (RAG Corpus)

Five mock policy documents in `data/corpus/` — fabricated but based on real Indian government rules:

| File | Based On |
|---|---|
| `doc1_cpcb_epr_guidelines_2022.txt` | CPCB EPR Guidelines 2022 — cpcb.nic.in/extended-producer-responsibility |
| `doc2_plastic_waste_management_rules_2016.txt` | Plastic Waste Management Rules 2016 — MoEF&CC notification GSR 320(E) |
| `doc3_epr_registration_and_targets.txt` | CPCB portal guidance + 2021 PWM Amendment Rules |
| `doc4_epr_compliance_calendar.txt` | CPCB filing timelines — eprplastic.cpcb.gov.in |
| `doc5_plastic_category_definitions.txt` | CPCB plastic category definitions from 2022 EPR guidelines |

These cover: registration steps, annual targets (%), penalties, compliance deadlines, plastic category definitions. 29 chunks indexed into ChromaDB at startup.

> These are mock documents for demonstration. For actual compliance, consult the official CPCB portal.

---

## Mock ERP Feed

`data/erp_feed.csv` simulates a real ERP export (SAP/Oracle style). April 2026 data is deliberately set so `flexible_plastic` has a 6.6% gap (declared 8,500 kg vs procured 9,100 kg) — this triggers the >5% flag and demonstrates the reconciliation feature.

---

## One Thing I Would Do Differently

With another day I would replace the flat ChromaDB collection with **per-document metadata filtering** — adding a topic classifier as a first step would let the retriever filter to the right document before semantic search, cutting hallucination risk and improving citation precision on multi-topic questions.

---

## Project Structure

```
greenpack-epr-service/
├── main.py                  # FastAPI app, 3 endpoints
├── models.py                # Pydantic request/response models
├── database.py              # SQLite storage
├── reconcile.py             # ERP reconciliation + Llama narrative
├── rag.py                   # ChromaDB indexing + RAG Q&A
├── data/
│   ├── erp_feed.csv         # Mock ERP procurement data
│   └── corpus/              # 5 EPR policy documents (RAG knowledge base)
│       ├── doc1_cpcb_epr_guidelines_2022.txt
│       ├── doc2_plastic_waste_management_rules_2016.txt
│       ├── doc3_epr_registration_and_targets.txt
│       ├── doc4_epr_compliance_calendar.txt
│       └── doc5_plastic_category_definitions.txt
├── requirements.txt
├── .gitignore
├── demo.sh                  # Bash demo script
├── demo.ps1                 # PowerShell demo script
└── README.md
```
