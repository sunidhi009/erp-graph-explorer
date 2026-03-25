# AI Coding Session Log — ERP Graph Explorer
**Tool:** Claude (claude.ai)  
**Project:** ERP Graph Explorer — Order-to-Cash Intelligence Platform  
**GitHub:** https://github.com/sunidhi009/erp-graph-explorer  
**Live Demo:** https://erp-graph-explorer.vercel.app  

---

## Overview

I used Claude (claude.ai) as my primary AI coding partner throughout this project.
I made all architecture, product, and technology decisions.
Claude generated code based on my direction and helped debug issues.

This is exactly the workflow described in the FDE role — using AI tools to ship fast
while making sound engineering judgments.

---

## Architecture Decisions I Made (with Claude as thinking partner)

| Decision | What I Chose | Why |
|---|---|---|
| Database | SQLite | Zero setup, single file, fast JOINs for 5K records, easy to deploy |
| LLM Provider | Groq | Completely free, no credit card, higher rate limits than Gemini |
| Graph Library | HTML Canvas (custom) | Full control over force physics, zero dependencies |
| Backend Framework | FastAPI | Auto docs at /docs, Pydantic validation, faster than Flask |
| Frontend | React + Vite | Fast dev server, component-based, simple SPA |
| Backend Hosting | Render.com | Free tier, auto-deploys from GitHub |
| Frontend Hosting | Vercel | Free tier, best React/Vite support |

---

## Key Prompts and What They Produced

### 1. Data Loading
**My Prompt:**
"I have 49 JSONL files in 19 named folders representing SAP Order-to-Cash data.
Build data_loader.py that reads each folder into the correct SQLite table using
a FOLDER_MAP dictionary. Handle type conversions and duplicate records."

**Result:** data_loader.py — loaded all 19 entity types, 22,000+ records into SQLite

---

### 2. Graph Construction
**My Prompt:**
"Build graph_builder.py that creates nodes for each entity type (Customer, SalesOrder,
Delivery, BillingDocument, JournalEntry, Product, Plant, BusinessPartner) and edges
based on foreign key relationships. Assign colors and sizes by type."

**Result:** graph_builder.py — 541 nodes, 755 edges with correct relationships

---

### 3. LLM Integration
**My Prompt:**
"Build llm_handler.py using Groq API (OpenAI format). Include the full database schema
in the system prompt so the LLM can generate accurate SQL. Always return structured JSON:
{answer, sql, rows, referenced_ids, is_off_topic}. Add guardrails to reject non-ERP questions.
Add self-healing SQL retry when the generated SQL fails."

**Result:** llm_handler.py — schema-aware NL-to-SQL with guardrails and retry logic

---

### 4. Frontend
**My Prompt:**
"Build a React app with dark theme. Left panel: force-directed graph on HTML Canvas
with custom physics (node repulsion + edge attraction). Right panel: chat interface
with message history, SQL display, results table. Top: stats dashboard cards.
Bottom: legend. Single App.jsx file."

**Result:** App.jsx — complete UI, 800+ lines, no external graph library

---

### 5. Deployment
**My Prompt:**
"How do I deploy the FastAPI backend on Render.com and the React frontend on Vercel?
What environment variables do I need? How do I connect frontend to backend in production?"

**Result:** Live deployment at erp-graph-explorer.vercel.app + erp-graph-explorer.onrender.com

---

## Debugging Iterations — How I Used Claude

For every error, my workflow was:
1. Copy the exact error message
2. Paste it to Claude with the relevant code
3. Claude identified root cause
4. Applied fix → tested → if new error → repeated

### Error 1: Wrong DATA_DIR
- **Error:** Backend loaded from empty /data folder
- **Prompt:** "main.py is not passing DATA_DIR to init_database. Fix it."
- **Fix:** Added `data_dir=os.getenv('DATA_DIR')` parameter

### Error 2: Gemini 404 Not Found
- **Error:** `models/gemini-1.5-flash is not found`
- **Prompt:** "How do I list all available Gemini models for my API key?"
- **Fix:** Called `/v1/models` endpoint, found correct model name `gemini-2.0-flash`

### Error 3: Gemini 429 Rate Limit
- **Error:** `Too Many Requests` — 15 req/min limit hit immediately
- **Prompt:** "Gemini keeps rate limiting. What free LLM has higher limits?"
- **Fix:** Switched entirely to Groq API

### Error 4: Groq 400 Bad Request
- **Error:** `400 Bad Request` on Groq API
- **Root Cause I identified:** Gemini uses `contents` array format. Groq uses OpenAI `messages` format. I had copied the wrong format.
- **Prompt:** "Rewrite call_gemini() using OpenAI messages format for Groq"
- **Fix:** Complete rewrite of API call function

### Error 5: GitHub Push Blocked
- **Error:** `Repository rule violations — Push cannot contain secrets`
- **Prompt:** "GitHub blocked my push because API key is in code. Fix properly."
- **Fix:** Changed to `os.getenv()`, deleted `.git`, fresh commit

### Error 6: Environment Variable Lost on Reload
- **Error:** Groq API key not loading after uvicorn auto-reload
- **Root Cause:** `$env:` sets variable only for terminal session
- **Fix:** Used `os.getenv('GROQ_API_KEY', 'hardcoded-default')` as fallback

### Error 7-10: Port conflicts, database locked, main.jsx wrong content
- All debugged using same Claude iteration pattern

---

## What Was Built

- **Graph:** 541 nodes, 755 edges, 8 entity types, force-directed Canvas physics
- **Chat:** Natural language → Groq LLM → SQL → real SQLite data → answer
- **Guardrails:** Off-topic rejection tested: "Who is Elon Musk?" → Rejected
- **Analytics:** Top products by billing, broken flow detection
- **Trace API:** /api/trace/{billing_id} traces full O2C journey
- **Bonus:** Payments loaded, chat memory, self-healing SQL, node highlighting

---

## Session Statistics
- Messages exchanged: 200+ over 3 days
- Errors debugged: 10 major, multiple minor
- Files generated: 5 Python files, 2 React files, README, deployment config
- Total lines of code: ~1,500+
