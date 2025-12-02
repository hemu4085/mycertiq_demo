# MyCertiQ Demo — v1.0.0  
### AI-First Physician Licensing & CME Management Platform  
**Hybrid LLM + RAG + Metadata Knowledge Graph**

---

## 🚀 Overview

**MyCertiQ** is an AI-powered platform that helps physicians manage:

- Continuing Medical Education (CME)
- State & Federal Licensing Requirements
- Board Certifications
- CME Compliance Tracking
- Personalized CME Recommendations
- Travel-Aware and Lifestyle-Aware CME Search

This repository contains the **MyCertiQ Demo v1** implementation:

- FastAPI backend  
- Postgres + pgvector  
- Hybrid LLM Architecture  
- CME Metadata, Knowledge Chunks & Vector Search  
- Human-like CME Query API  
- React/Tailwind Frontend (initial scaffold)

This is the **foundation** for the full MyCertiQ Production System.

---

## 🧠 Hybrid LLM Architecture (Local + Cloud)

MyCertiQ uses a **two-tier LLM routing strategy**:

### **1️⃣ Local LLaMA 3 8B**  
Used for:
- Routine queries  
- Simple CME filtering  
- Summaries  
- Vector similarity rescoring  

### **2️⃣ Cloud LLaMA 3 70B / OpenAI / Claude**  
Used for:
- Complex multi-constraint reasoning  
- Human-like CME queries  
- Compliance reasoning  
- Personalized recommendations  
- Travel & family constraints  
- Metadata enrichment  

### **Routing Logic**
- If query = simple → local  
- If query = multi-step / legal / preference-based → cloud  
- All queries enriched with RAG (vector search)

---

## 🗄️ Backend Architecture (FastAPI + Postgres + pgvector)

mycertiq_demo/
│── app/
│ ├── main.py
│ ├── config.py
│ ├── database.py
│ ├── api/
│ │ ├── routes/
│ │ │ ├── ask_cme.py
│ │ │ ├── vector_search.py
│ │ │ ├── physicians.py
│ ├── models/
│ │ ├── cme_event.py
│ │ ├── physician.py
│ │ ├── embedding_store.py
│ │ ├── requirement_master.py
│ └── services/
│ ├── embeddings.py
│ ├── llm_router.py
│ ├── cme_human_query.py
│
└── data/
├── cme/
├── synthetic/
├── embeddings/


### Key Components
- **FastAPI** for API routing  
- **SQLAlchemy** ORM  
- **Postgres 16** with **pgvector**  
- Vector-based chunk embeddings  
- RAG pipeline  
- Human-like Natural Language CME query engine  

---

## 🧬 CME Metadata Knowledge Graph (v1)

Version 1 includes:

- CME Events  
- CME Providers  
- Topics (84-topic taxonomy)  
- CME–Topic Mappings  
- Knowledge Chunks  
- Physician Profiles  
- Licensing Requirements  
- CME Completion Ledger  
- Gap Engine (initial rules)

This serves as the foundation for:

- Personalized CME  
- Travel-Aware CME  
- Requirement-Aware CME  
- Preference-Based CME  

---

## ⚙️ Local Development Setup

### **1. Clone repo**
```bash
git clone git@github.com:hemu4085/mycertiq_demo.git
cd mycertiq_demo

2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

3. Run Postgres + pgvector

Requires local or Docker Postgres:

docker run -d \
  --name mycertiq_pg \
  -e POSTGRES_USER=mycertiq_user \
  -e POSTGRES_PASSWORD=mycertiq_dev \
  -e POSTGRES_DB=mycertiq_demo \
  -p 5432:5432 \
  ankane/pgvector:pg16

4. Initialize Database
psql -h localhost -U mycertiq_user -d mycertiq_demo -f schema.sql

5. Run API
uvicorn app.main:app --reload

🔍 Key API Endpoints (v1)
Endpoint	Description
POST /vector/search	Vector search over knowledge chunks
POST /ask_cme	Human-style CME question answering
GET /physician/{id}	Fetch physician profile
GET /cme/{id}	Return CME metadata
POST /embedding/create	Create embeddings for knowledge

All endpoints authenticated via API key (v1).

🌎 Screenshots (Placeholder for v1)

Add screenshots in future commits:

/screenshots
    ├── dashboard.png
    ├── cme_finder.png
    ├── human_query_result.png
    ├── metadata_explorer.png

🚧 Roadmap — v1 → v2
✔️ Completed in v1.0.0

GitHub repo setup

FastAPI backend scaffold

Postgres schema (CME + physicians + requirements)

RAG pipeline

Hybrid LLM routing

Vector search

Basic human-like CME query API

Tag v1.0.0 release

📈 Roadmap for v2.0.0 (Next Major Release)
1. Metadata Enrichment Expansion

Add lifestyle filters (travel, family, attractions, schedules)

Add structured JSONB metadata

Auto-enrichment pipeline

2. Human-Like CME Query v2

Multi-intent parsing

Preference-aware ranking

Family/travel/constraints reasoning

3. RAG Upgrade

Chunk-title context

Attribute-based vector retrieval

Hybrid BM25 + vector ranking

4. Frontend (React/Tailwind) Upgrade

CME Finder v2

Map view

Calendar view

Preference editor

5. Compliance Gap Engine v2

Rules engine

Physician-cycle summary

Automated CME matching to gaps

6. Provider Integration

One-click ingestion from CME providers

Synthetic + real CME data ingestion

7. LLM Orchestrator

MCP integration

Multi-step reasoning

Safety + hallucination mitigations

🏷️ Versioning

This repo follows:

main → stable

dev → active development

Tags:

v1.0.0 — initial release

v2.0.0 — next major release

👤 Author

Hemant Verma
Data Governance Lead / AI Architect
Founder — MyCertiQ
GitHub: https://github.com/hemu4085

📜 License

Proprietary — All rights reserved.
Contact the author for licensing or partnership inquiries.
