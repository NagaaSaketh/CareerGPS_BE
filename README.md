# 🧭 CareerGPS

**Evidence-Based Career Navigation for Tier-2/3 Graduates — Now Supporting 29+ Career Paths**

> *Millions of graduates every year. No Navigation.*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/react-18+-61dafb.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What's New: Dynamic Career Paths

CareerGPS now supports **ANY career path** you choose — not just Backend Engineering.

### Supported Career Categories (29+ Roles)

| Category | Roles |
|----------|-------|
| 🔧 **Engineering** | Backend, Frontend, Fullstack, DevOps, Mobile, SRE, SDE, Software Developer |
| 🧪 **QA / Testing** | QA Automation, SDET |
| 📊 **Data** | Data Analyst, Data Scientist, Data Engineer, ML Engineer |
| 🤖 **AI / ML** | Generative AI Engineer, NLP Engineer, Computer Vision Engineer, AI Research Scientist, MLOps Engineer, Prompt Engineer |
| 📱 **Product** | Product Manager |
| 🎨 **Design** | UX Designer, UI Designer |
| 🎤 **DevRel / Content** | DevRel, Technical Writer, Solutions Engineer |
| 🎧 **Support** | Support Engineer |
| 📈 **Business** | Business Analyst, Project Manager |

### Three Ways to Choose Your Path

1. **Browse by Category** — Pick Engineering, Data, Design, etc.
2. **Search by Name** — Type "Data Scientist" or "PM" — we find the match
3. **Strength Explorer** — Tell us what you enjoy → we suggest roles

---

## 📖 Table of Contents

1. [The Problem](#the-problem)
2. [What CareerGPS Does](#what-careergps-does)
3. [Dynamic Role Support](#dynamic-role-support)
4. [System Architecture](#system-architecture)
5. [Market Data](#market-data)
6. [Installation](#installation)
7. [Usage](#usage)
8. [Golden Dataset Tests](#golden-dataset-tests)
9. [API Documentation](#api-documentation)
10. [Evaluation Criteria](#evaluation-criteria)
11. [Future Roadmap](#future-roadmap)
12. [Contributors](#contributors)

---

## 🎯 The Problem

**Priya's Story** (representative of many graduates annually):

- 22 years old, B.Tech CS from private college (NAAC B+, no brand recognition)
- 72% aggregate, basic Python, 1 internship (manual testing)
- 2 academic projects on GitHub with no README
- Target: Backend Engineer at product company
- Reality: 140 applications, 4 rejections, 0 callbacks
- **She does not know why she is being rejected**

**The Crisis:**
- India produces **millions of graduates/year**
- Many face **employability challenges**
- Graduate unemployment remains a **structural concern**
- Under-25 unemployment is particularly high
- A small fraction secure permanent salaried jobs within 1 year

**The Root Cause:** Not lack of ambition. **Lack of navigation.**

Every existing solution fails the same way:
- **YouTube:** Generic advice, doesn't know Priya's starting point
- **Coaching Institutes:** Fixed syllabus, no personalization
- **Placement Cells:** Optimize for placement %, not fit
- **Mentorship Platforms:** 30-min calls, no longitudinal tracking

---

## ✅ What CareerGPS Does

### 1. Evidence-Based Skill Assessment
- **NEVER trusts self-reported ratings**
- Evaluates using GitHub code analysis, resume parsing, diagnostic tasks
- Flags contradictions (e.g., user says Python 4/5, GitHub shows 1/5)
- Anchors assessment to real hiring benchmarks

### 2. Market-Aligned Path Mapping (Now for ANY Role)
- Compares profile vs. **aggregated job description data** for your chosen role
- Accounts for **credential bias** (tier-1 vs tier-3 callback rates)
- Identifies highest-impact gaps for your specific target
- Suggests realistic timelines (not aspirational ones)

### 3. Prioritized Execution Plans (Role-Specific)
- **Engineering roles:** Build projects, deploy, write tests
- **Data roles:** Build dashboards, competitions, SQL projects
- **Design roles:** Create case studies, redesign challenges, portfolios
- **DevRel roles:** Write articles, build community, create content
- **Business roles:** Case studies, process improvements, analysis projects
- Always ends with **3 clear tasks** — no vague plans

### 4. Real Progress Tracking (Not Compliance)
- Distinguishes:
  - ✅ **Real Progress:** Building projects, getting interviews
  - ⚠️ **Compliance:** Completing courses without application
  - 🔄 **Motion:** Applying without iteration
- Detects stagnation loops and breaks them

### 5. Adaptive Path Correction
- Recommends alternate or intermediate paths when needed
- Frames transitions as **strategic steps, not downgrades**
- Surfaces unexplored paths based on hidden strengths

---

## 🌟 Dynamic Role Support

### How It Works

```python
# Works with ANY role
profile = {
    "target_role": "data_scientist",  # or "ux_designer", "product_manager", etc.
    "college_tier": "tier_3",
    "location": "bangalore",
    # ... rest of profile
}

gps = CareerGPS()
report = gps.process_profile(profile)
```

### Role Alias Matching

Type any variation — we find the match:

| You Type | We Match To |
|----------|-------------|
| "backend" | Backend Engineer |
| "backend dev" | Backend Engineer |
| "PM" | Product Manager |
| "data scientist" | Data Scientist |
| "DS" | Data Scientist |
| "UX" | UX Designer |
| "QA" | QA Automation |
| "DevOps" | DevOps Engineer |
| "technical writer" | Technical Writer |

### Unknown Role Handling

If you type a role we don't know (e.g., "AI Researcher"):
- We flag it as unknown
- Suggest 3 closest alternatives (e.g., Data Scientist, ML Engineer, Data Engineer)
- Never guess or fabricate requirements

### Strength-Based Role Explorer

Not sure what to target? Tell us your strengths:

| Your Strength | Suggested Roles |
|---------------|---------------|
| Coding + Systems | Backend, DevOps, SRE |
| Coding + Design | Frontend, Mobile, Fullstack |
| Data + Coding | Data Scientist, Data Engineer, ML Engineer |
| Data (no coding) | Data Analyst, Business Analyst |
| Design (no coding) | UX Designer, UI Designer |
| Writing + Coding | DevRel, Technical Writer |
| People + Problems | Product Manager, Solutions Engineer |
| People (no tech) | Support Engineer, Business Analyst |

---

## ❌ What CareerGPS Must NOT Do

| Guardrail | Description |
|-----------|-------------|
| **No Self-Assessment Truth** | Never rely on user claims without validating against evidence |
| **No Generic Advice** | Avoid one-size-fits-all guidance ("learn DSA", "build projects") |
| **No False Reassurance** | Never say "you are ready" without evidence against hiring benchmarks |
| **No Fabricated Market Data** | All claims grounded in aggregated data or clearly marked uncertain |
| **No Credential Bias Denial** | Account for real-world hiring biases in recommendations |
| **No Overwhelming Output** | One-screen reports, 3 weekly tasks, no dense dashboards |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CAREERGPS PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ INPUT PARSER │───▶│ EVIDENCE     │───▶│ MARKET       │   │
│  │              │    │ ASSESSOR     │    │ MAPPER       │   │
│  │ - Validate   │    │              │    │              │   │
│  │ - Reject     │    │ - GitHub     │    │ - Aggregated │   │
│  │   vague      │    │   analysis   │    │   JD data    │   │
│  │   goals      │    │ - Resume     │    │ - Credential │   │
│  │ - Flag       │    │   parsing    │    │   bias       │   │
│  │   missing    │    │ - Diagnostic │    │ - Timeline   │   │
│  │   data       │    │   tasks      │    │   estimates  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ PATH PLANNER │◄───│ GAP ANALYSIS │◄───│ ROLE REQ DB  │   │
│  │              │    │              │    │ (21+ Roles)  │   │
│  │ - Direct     │    │ - Missing    │    │              │   │
│  │ - Stepping   │    │   skills     │    │              │   │
│  │   stone      │    │ - Experience │    │              │   │
│  │ - Alternative│    │   gap        │    │              │   │
│  └──────────────┘    │ - Framework  │    └──────────────┘   │
│         │            │   gaps       │                        │
│         ▼            └──────────────┘                        │
│  ┌──────────────┐                                            │
│  │ PROGRESS     │◄─────────────────────────────────────────┤
│  │ TRACKER      │                                            │
│  │              │    ┌──────────────┐                        │
│  │ - Compliance │◄───│ WEEKLY       │                        │
│  │   detection  │    │ CHECK-IN     │                        │
│  │ - Stagnation │    │              │                        │
│  │   alerts     │    │ - Tasks      │                        │
│  │ - Next week  │    │ - Evidence   │                        │
│  │   tasks      │    │ - Market     │                        │
│  └──────────────┘    │   signals    │                        │
│         │            └──────────────┘                        │
│         ▼                                                    │
│  ┌──────────────┐                                            │
│  │ OUTPUT       │                                            │
│  │ SYNTHESIZER  │                                            │
│  │              │                                            │
│  │ - One screen │                                            │
│  │ - 3 tasks    │                                            │
│  │ - Honest but │                                            │
│  │   encouraging│                                            │
│  └──────────────┘                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Agent Descriptions

| Agent | Responsibility | Key Design Decision |
|-------|---------------|---------------------|
| **Input Parser** | Validates inputs, rejects vague goals, flags missing evidence | If input is insufficient, system asks clarifying questions instead of guessing |
| **Evidence Assessor** | Analyzes GitHub, resume, diagnostics; never trusts self-report | Self-report > evidence + 1 point = contradiction flag; evidence wins |
| **Market Mapper** | Compares profile to aggregated JD requirements; accounts for credential bias | Uses directional salary and callback estimates per role and tier |
| **Path Planner** | Generates 2-3 viable paths with timelines and probabilities | Always includes stepping-stone path for tier-2/3; frames as strategic not downgrade |
| **Progress Tracker** | Distinguishes compliance from real progress; detects stagnation | 3 weeks of compliance = forced project task; 20 apps 0 responses = profile fix mode |
| **Output Synthesizer** | Produces one-screen output with 3 weekly tasks | Uncertainty is surfaced, not hidden; honesty preserves agency |

---

## 📊 Market Data

**Data Sources:**
- Glassdoor India Salary Data
- Indeed India Job Postings
- Naukri.com Job Listings
- BuiltIn Job Requirements Database
- Stack Overflow Developer Survey

> **Note:** All salary ranges, callback rates, and timeline estimates in CareerGPS are derived from aggregated public sources and should be treated as **directional guidance**, not precise, real-time market data. For production use, integrate live APIs.

### Sample: Backend Engineer - Pune (0-2 YOE)

| Metric | Directional Estimate |
|--------|---------------------|
| **Salary Range** | ₹5.5 - 9.0 LPA |
| **Min Experience** | 24 months |
| **Required Skills** | Python/Java/Go, REST APIs, SQL, Git, Docker |
| **Frameworks** | Django/FastAPI, Spring Boot, Express |
| **Hiring Difficulty** | Hard |
| **Tier-3 Callback Rate** | Low (~3% estimated) |

### Sample: Data Scientist - Bangalore (0-2 YOE)

| Metric | Directional Estimate |
|--------|---------------------|
| **Salary Range** | ₹7.0 - 12.0 LPA |
| **Min Experience** | 12 months |
| **Required Skills** | Python/R, Statistics, ML, SQL, Git |
| **Frameworks** | Scikit-learn, TensorFlow, PyTorch |
| **Hiring Difficulty** | Hard |
| **Tier-3 Callback Rate** | Low (~4% estimated) |

### Sample: UX Designer - Mumbai (0-2 YOE)

| Metric | Directional Estimate |
|--------|---------------------|
| **Salary Range** | ₹4.5 - 7.5 LPA |
| **Min Experience** | 0 months |
| **Required Skills** | User Research, Wireframing, Prototyping, Figma |
| **Frameworks** | Figma, Sketch, Adobe XD |
| **Hiring Difficulty** | Medium |
| **Tier-3 Callback Rate** | Moderate (~6% estimated) |

### Location Multipliers (Salary Adjustment)

| Location | Multiplier |
|----------|-----------|
| Bangalore | 1.25x |
| Mumbai | 1.20x |
| Hyderabad | 1.15x |
| Delhi NCR | 1.15x |
| Pune | 1.10x |
| Chennai | 1.05x |
| Tier 2 Cities | 0.85x |

---

## 🚀 Installation

### Prerequisites
- Python 3.9+
- pip
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/careergps.git
cd careergps

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r careergps-backend/requirements.txt

# Set up environment variables (optional)
cp careergps-backend/.env.example careergps-backend/.env
# Edit .env with your API keys if needed
```

### Dependencies
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pandas>=2.0.0
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## 💻 Usage

### Running the API Server

```bash
cd careergps-backend
uvicorn api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

Interactive docs at `http://localhost:8000/docs`

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | Analyze profile and generate career report |
| `/api/v1/checkin` | POST | Weekly progress check-in |
| `/api/v1/roles` | GET | List all supported roles |
| `/api/v1/roles/{role_name}` | GET | Get role requirements |
| `/api/v1/roles/search/{query}` | GET | Search for a role |
| `/api/v1/health` | GET | Health check |

### Using the API

```python
import requests

profile = {
    "target_role": "data_scientist",
    "college_tier": "tier_3",
    "location": "bangalore",
    "experience_months": 0,
    "current_state": "basic_python",
    "self_assessment": {
        "python": 3,
        "statistics": 2,
        "machine_learning": 1,
        "sql": 2,
        "communication": 3
    },
    "github": {
        "url": "",
        "accessible": False,
        "num_repos": 0
    },
    "resume": {
        "internship": {"has_internship": False, "type": "none", "duration_months": 0},
        "projects": [],
        "skills": ["python", "excel"],
        "cgpa": 7.5,
        "college_tier": "tier_3"
    },
    "diagnostics": {}
}

response = requests.post("http://localhost:8000/api/v1/analyze", json=profile)
report = response.json()["report"]
print(report)
```

---

## 🧪 Golden Dataset Tests

| # | Input | Expected Behavior | Status |
|---|-------|-------------------|--------|
| 1 | Priya's profile: 72%, no framework, basic Python | Identify gap, suggest QA automation as intermediate | ✅ |
| 2 | Student rates 5/5, GitHub shows 1 project no README | Flag self-assessment gap | ✅ |
| 3 | Target: SDE at Google, 6 months, tier-3 | Honest redirect | ✅ |
| 4 | Strong communication + testing, weak DSA | Surface DevRel / Technical Writing | ✅ |
| 5 | Completed DSA modules, zero projects | Flag compliance, redirect to building | ✅ |
| 6 | Fake GitHub with copied projects | Flag uncertainty | ✅ |
| 7 | "Just tell me I'm ready" | Refuse without evidence | ✅ |

### Running Tests

```bash
cd careergps-backend
python -m pytest tests/ -v
```

---

## 📚 API Documentation

### `CareerGPS.process_profile(profile: dict) -> str`

**Input:** User profile dictionary (works with ANY target_role)
**Output:** Formatted career navigation report

**Profile Schema:**
```json
{
  "target_role": "data_scientist",
  "college_tier": "tier_3",
  "location": "bangalore",
  "experience_months": 0,
  "current_state": "basic_python",
  "self_assessment": {
    "python": 3,
    "statistics": 2,
    "machine_learning": 1
  },
  "github": {
    "url": "string",
    "accessible": true,
    "num_repos": 0
  },
  "resume": {
    "internship": {"has_internship": false},
    "projects": [],
    "skills": ["python"],
    "cgpa": 7.5
  },
  "diagnostics": {}
}
```

### `CareerGPS.weekly_checkin(...)`

**Parameters:**
- `week`: int
- `tasks_completed`: List[str]
- `applications_sent`: int
- `responses_received`: int
- `interviews_attended`: int

**Output:** Weekly progress report + next week's 3 tasks

---

## 📏 Evaluation Criteria

| Criteria | How We Measure | Target |
|----------|---------------|--------|
| **Assessment Accuracy** | Agent's skill rating vs. recruiter evaluation | Match in 4/5 cases |
| **Path Relevance** | Suggested roles match real JDs for similar candidates | 80%+ accuracy |
| **Progress Detection** | Distinguish course completion from project building | 90%+ precision |
| **Honesty Engagement** | Honest feedback increases engagement | <15% drop-off |
| **Weekly Action Clarity** | 3 tasks are clear, doable, relevant | 3/5 users rate "very clear" |
| **Role Coverage** | System handles any valid role input | 29+ roles supported |

---

## 🔮 Future Roadmap

### Phase 2 (Next 3 months)
- [ ] GitHub API integration for real repo analysis
- [ ] Resume parsing with OCR
- [ ] LinkedIn profile integration
- [x] Real-time JD scraping from Naukri, LinkedIn, Indeed, Glassdoor (HTTP-only, no browser)
- [ ] Mock interview scoring with voice analysis
- [x] Added 8 AI/ML roles (GenAI, NLP, CV, AI Research, MLOps, Prompt Engineer, etc.)

### Phase 3 (6 months)
- [ ] ML model for callback rate prediction
- [ ] A/B testing for path recommendations
- [ ] Community mentorship matching
- [ ] Mobile app for daily check-ins
- [ ] Role transition analytics (e.g., Backend → Product Manager paths)

### Phase 4 (12 months)
- [ ] Integration with college placement cells
- [ ] Employer-facing candidate matching
- [ ] Pan-India graduate employment analytics dashboard
- [ ] International market support (US, UK, Singapore)

---

## 👥 Contributors

Built as part of an **Applied AI Capstone Series**.

**Design Philosophy:**
> "The best solutions are never the ones with the most features. They are the ones where you could point at any part of your system and say: 'This exists because of this constraint in the problem, and here is what would break if I removed it.'"

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- Applied AI Capstone framework
- **Glassdoor, Indeed, Naukri, BuiltIn** for market data references
- Every Priya who shared their story so we could build better

---

<div align="center">

**CareerGPS** — *Because every graduate deserves a map — for ANY path they choose.*

🧭

</div>
