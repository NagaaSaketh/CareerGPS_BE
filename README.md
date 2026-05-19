# CareerGPS — Backend

**Evidence-Based Career Navigation API — 29+ Career Paths**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Anthropic](https://img.shields.io/badge/Claude-Anthropic-orange.svg)](https://anthropic.com)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E.svg)](https://supabase.com)

---

## What This Is

The FastAPI backend powering CareerGPS. A 6-agent AI pipeline that assesses skills from evidence, maps career gaps against real market data, generates strategic paths, and tracks 12 weeks of progress.

Claude (via the Anthropic API) acts as the orchestrator — it calls the agents as tools, reasons about the profile, and writes the final report itself. The report streams back to the frontend via Server-Sent Events.

---

## The Problem

Millions of graduates apply to jobs with no feedback on why they're rejected. They don't know their actual skill level versus market requirements, and they can't tell if they're making real progress or just completing courses.

Generic advice makes it worse. CareerGPS replaces it with evidence-based assessment, real market data, and week-by-week accountability.

---

## The 6-Agent Pipeline

```
Input → Parser → Assessor → Mapper → Planner → Tracker → Synthesizer → Output
```

| Agent | What It Does | Key Rule |
|-------|-------------|----------|
| **Input Parser** | Validates inputs, rejects vague goals | No guessing — insufficient input = clarifying prompt |
| **Evidence Assessor** | Rates skills from GitHub + resume, never self-report | Self-report > evidence + 1 = contradiction flag, evidence wins |
| **Market Mapper** | Compares profile to aggregated JD data | Accounts for college tier bias in callback rates |
| **Path Planner** | Generates Direct, Stepping-Stone, Alternative paths | Always includes stepping-stone for tier-2/3; framed as strategic, not a downgrade |
| **Progress Tracker** | Classifies weekly effort — Compliance / Motion / Real Progress / Breakthrough | Cross-week detection: 2+ weeks of zero applications = downgrade from Real Progress |
| **Output Synthesizer** | One-screen report, exactly 3 tasks | Uncertainty is surfaced, never hidden |

---

## Supported Roles (29+)

| Category | Roles |
|----------|-------|
| Engineering | Backend, Frontend, Fullstack, DevOps, Mobile, SRE, SDE, Software Developer |
| QA / Testing | QA Automation, SDET |
| Data | Data Analyst, Data Scientist, Data Engineer, ML Engineer |
| AI / ML | Generative AI Engineer, NLP Engineer, Computer Vision Engineer, AI Research Scientist, MLOps Engineer, Prompt Engineer |
| Product | Product Manager |
| Design | UX Designer, UI Designer |
| DevRel / Content | DevRel, Technical Writer, Solutions Engineer |
| Support | Support Engineer |
| Business | Business Analyst, Project Manager |

Role alias matching is built in — "backend dev", "PM", "DS", "UX" all resolve correctly.

---

## How the LLM Orchestrator Works

**File:** `agents/llm_orchestrator.py`

This is the most important file in the backend. Instead of the Python code hard-wiring "call the assessor, then the mapper, then the planner", that decision is handed entirely to Claude.

The five existing Python agents are exposed to Claude as **callable tools** using the Anthropic tool-use API:

| Tool | What Claude Uses It For |
|------|------------------------|
| `lookup_role` | Read what the target role actually requires from the market database |
| `assess_skills` | Run SkillAssessor — get evidence-based skill ratings with contradiction flags |
| `analyze_career_gap` | Run MarketMapper — quantify missing skills, experience gap, credential penalty |
| `generate_career_paths` | Run PathPlanner — get Direct, Stepping-Stone, and Alternative paths with timelines |
| `fetch_market_jobs` | Pull job listings to ground the advice in real hiring signals |

Claude receives the user's profile, reads the tool descriptions, and decides which tools to call and in what order. After calling them, it writes the final report itself — grounded entirely in what the tools returned.

**The agentic loop:**

```
User profile arrives
       ↓
Claude decides: call lookup_role first
       ↓
Tool result fed back to Claude
       ↓
Claude decides: call assess_skills
       ↓
Tool result fed back to Claude
       ↓
Claude decides: call analyze_career_gap → generate_career_paths
       ↓
Claude writes the final report using all tool output as evidence
       ↓
Report streams to frontend word-by-word via SSE
```

Each tool call emits a `tool_start` and `tool_end` SSE event to the frontend — this is what makes the AgentTrace panel light up in real time as each agent activates.

**Why this approach instead of a fixed pipeline:**

A fixed pipeline always calls all agents in the same order regardless of the profile. Claude adapts — if the role isn't in the database, it flags it immediately instead of running a full assessment on a nonsensical target. If the profile is strong, it spends less time on gap analysis and more on path differentiation. The report's tone and emphasis also adapt: a tier-3 student and a tier-1 student with identical skill gaps get different framing because Claude incorporates the `credential_penalty` value from the gap analysis into what it chooses to highlight.

A `max_iterations = 8` cap prevents infinite tool-call loops. In practice, 4–5 iterations is typical.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CAREERGPS PIPELINE                       │
│                                                             │
│  Input Parser ──► Evidence Assessor ──► Market Mapper       │
│                          │                    │             │
│                    GitHub / Resume      Aggregated JD data  │
│                    analysis             Credential bias     │
│                          │                    │             │
│                   Path Planner ◄──── Gap Analysis           │
│                          │                                  │
│                   Progress Tracker ◄── Weekly Check-in      │
│                          │                                  │
│                   Output Synthesizer                        │
│                   (one screen · 3 tasks · streams via SSE)  │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check — used by Render |
| `/api/v1/analyze-agentic` | POST | Yes | Stream SSE report via Claude + agents |
| `/api/v1/checkin` | POST | Yes | Weekly check-in → classification + next tasks |
| `/api/v1/checkins` | GET | Yes | Fetch all check-ins for a role |
| `/api/v1/profile` | GET/POST | Yes | Get or save user profile |
| `/api/v1/reports/latest` | GET | Yes | Fetch latest report for a role |
| `/api/v1/roles` | GET | No | List all supported roles |
| `/api/v1/roles/{role}` | GET | No | Get requirements for a specific role |
| `/api/v1/market/jobs` | GET | Yes | Fetch job listings (live or mock) |


---

## Market Data

Salary ranges, callback rates, and timeline estimates are derived from aggregated public sources (Glassdoor, Indeed, Naukri, Stack Overflow Developer Survey) and are treated as **directional guidance**, not real-time market data.

Location salary multipliers are applied per city (Bangalore 1.25x, Mumbai 1.20x, Hyderabad 1.15x, etc.).

---

## Local Setup

**Prerequisites:** Python 3.10+, a Supabase project, an Anthropic API key.

```bash
cd careergps-backend

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Fill in ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY
```

Start the server:

```bash
uvicorn api:app --reload --port 8000
# API → http://localhost:8000
# Docs → http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Backend DB access (never expose to frontend) |
| `SUPABASE_ANON_KEY` | Yes | Auth validation |
| `CORS_ORIGINS` | Yes (prod) | Comma-separated allowed origins e.g. `https://careergps.vercel.app` |
| `ENABLE_JD_SCRAPING` | No | Set `false` on Render free tier to prevent OOM |
| `DEBUG` | No | Set `false` in production |

---

## Production Deployment (Render)

```
Build Command:  pip install -r requirements.txt
Start Command:  gunicorn api:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
```

Set `ENABLE_JD_SCRAPING=false` on the free tier — the app serves realistic mock jobs instead. This prevents OOM crashes (HTTP scrapers use ~5MB vs ~400MB for Chromium).

See `DEPLOYMENT.md` at the project root for the full deployment guide including Supabase table setup.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

Golden dataset — 7 adversarial scenarios:

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| 1 | Graduate with basic Python, no framework, manual testing internship | Identify gap, suggest stepping-stone role | ✅ |
| 2 | User self-rates 5/5, GitHub shows 1 project with no README | Flag contradiction | ✅ |
| 3 | Target: SDE at Google, 6 months experience, tier-3 college | Honest redirect with realistic path | ✅ |
| 4 | Strong communication + testing, weak DSA | Surface DevRel / Technical Writing | ✅ |
| 5 | Completed DSA course modules, zero projects shipped | Flag compliance loop, redirect to building | ✅ |
| 6 | GitHub repos with copied/forked projects | Flag uncertainty in evidence | ✅ |
| 7 | User wants confirmation they're ready without evidence | Refuse without evidence | ✅ |

---

## Design Guardrails

| Guardrail | Rule |
|-----------|------|
| No self-assessment trust | Claims always validated against GitHub / resume evidence |
| No generic advice | Every recommendation tied to the user's specific profile and role |
| No false reassurance | "You are ready" requires evidence against hiring benchmarks |
| No fabricated data | All market figures are directional and uncertainty is surfaced |
| No credential bias denial | Tier-3 callback rates are accounted for, not ignored |
| No overwhelming output | One screen, 3 tasks, no dense dashboards |

---

