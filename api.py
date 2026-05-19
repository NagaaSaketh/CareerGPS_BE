"""
CareerGPS FastAPI Backend
Exposes the CareerGPS agent pipeline as REST endpoints for the React frontend.
"""

import os
import sys
import logging
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.orchestrator import CareerGPS
from data.market_data import (
    get_all_roles, get_roles_by_category, is_role_supported,
    normalize_role_name, suggest_similar_roles, get_role_requirements,
    get_role_categories, get_salary_range, get_callback_rate,
    CollegeTier, estimate_timeline, get_stepping_stone_suggestions
)
from data.live_market_data import get_data_provenance
from data.mock_jobs import generate_mock_jobs
from scrapers.jd_scraper import MarketSnapshot, refresh_market_data
import db

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CareerGPS API",
    description="Evidence-based career navigation API supporting 25+ roles.",
    version="1.0.0"
)

# CORS for React frontend — configurable via env
# In development, allow all localhost ports. In production, restrict to your domain.
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    cors_origins = [o.strip() for o in cors_origins_env.split(",")]
else:
    # Dev fallback: allow common React dev ports
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class GitHubInput(BaseModel):
    url: str = ""
    accessible: bool = False
    num_repos: int = 0
    total_commits: int = 0
    languages: Dict[str, int] = Field(default_factory=dict)
    has_readme: bool = False
    has_tests: bool = False
    has_error_handling: bool = False
    avg_function_length: int = 50
    max_function_length: int = 150


class InternshipInput(BaseModel):
    has_internship: bool = False
    type: str = "none"
    duration_months: int = 0


class ProjectInput(BaseModel):
    technologies_used: List[str] = Field(default_factory=list)
    deployed: bool = False


class ResumeInput(BaseModel):
    internship: InternshipInput = Field(default_factory=InternshipInput)
    projects: List[ProjectInput] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    cgpa: float = 7.0
    college_tier: str = "tier_3"
    resume_text: str = Field(default="", description="Raw resume text for parsing")


class ProfileRequest(BaseModel):
    target_role: str = Field(..., description="Target career role (e.g., backend_engineer, data_scientist)")
    college_tier: str = Field(default="tier_3", description="tier_1, tier_2, or tier_3")
    location: str = Field(default="pune", description="Preferred work location")
    experience_months: int = Field(default=0, ge=0)
    current_state: str = Field(default="unknown", description="Current career state")
    self_assessment: Dict[str, int] = Field(default_factory=dict, description="Skill self-ratings 1-5")
    github: GitHubInput = Field(default_factory=GitHubInput)
    resume: ResumeInput = Field(default_factory=ResumeInput)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class TaskHoursInput(BaseModel):
    learning: int = Field(default=0, ge=0)
    project: int = Field(default=0, ge=0)
    practice: int = Field(default=0, ge=0)
    application: int = Field(default=0, ge=0)


class WeeklyCheckinRequest(BaseModel):
    week: int = Field(..., ge=1, le=52)
    tasks_completed: List[str] = Field(default_factory=list)
    applications_sent: int = Field(default=0, ge=0)
    responses_received: int = Field(default=0, ge=0)
    interviews_attended: int = Field(default=0, ge=0)
    target_role: str = Field(..., description="Target career role")
    task_hours: Optional[TaskHoursInput] = None


class RoleInfo(BaseModel):
    role_name: str
    role_category: str
    display_name: str
    min_experience_months: int
    required_skills: List[str]
    preferred_skills: List[str]
    framework_tools: List[str]
    salary_range_lpa: tuple
    hiring_difficulty: str
    tier_3_callback_rate: float


class TaskItem(BaseModel):
    number: int
    title: str
    description: str
    expected: str
    completed: bool = False


class PathItem(BaseModel):
    type: str
    timeline: int
    salary: str
    probability: float
    reasoning: str
    risks: List[str]
    steps: List[Dict[str, Any]] = []


class SkillItem(BaseModel):
    self: int
    evidence: int
    gaps: List[str]


class StructuredReport(BaseModel):
    title: str
    skills: Dict[str, SkillItem]
    contradictions: List[Dict[str, Any]]
    criticalGaps: List[str]
    salary: str
    callbackRate: float
    timeline: int
    difficulty: str
    paths: List[PathItem]
    tasks: List[TaskItem]
    uncertainty_flags: List[str] = []
    data_provenance: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    report: str
    target_role: str
    role_known: bool
    structured_data: Optional[StructuredReport] = None


class WeeklyCheckinResponse(BaseModel):
    checkin_report: str
    week: int
    progress_type: str = ""
    recommendation: str = ""
    red_flags: List[str] = []
    next_tasks: List[TaskItem] = []


class RoleSuggestionResponse(BaseModel):
    role: str
    display_name: str
    similar_roles: List[str]
    role_known: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    roles_supported: int
    live_scraping_enabled: bool = True


class MarketDataProvenance(BaseModel):
    role: str
    source: str
    freshness: str
    confidence: float
    scraped_at: Optional[str]
    uncertainty_flags: List[str]


class MarketSnapshotResponse(BaseModel):
    role: str
    location: str
    scraped_at: str
    sources: List[str]
    total_jobs_scraped: int
    top_skills: List[List]
    salary_range_lpa: Optional[Tuple[float, float]]
    experience_range_months: Tuple[int, int]
    hiring_volume_indicator: str
    top_companies: List[str]
    data_quality_score: float
    uncertainty_flags: List[str]


class ResumeUploadResponse(BaseModel):
    filename: str
    resume_text: str
    word_count: int
    extracted_skills: List[str]
    message: str


class JobListing(BaseModel):
    source: str
    title: str
    company: str
    location: str
    description: str
    url: str
    skills_found: List[str]
    salary_lpa: Optional[Tuple[float, float]] = None
    experience_months: Tuple[int, int] = (0, 0)


class JobsResponse(BaseModel):
    role: str
    location: str
    total_jobs: int
    jobs: List[JobListing]
    scraped_at: str
    sources_used: List[str]
    note: str


# =============================================================================
# AUTH HELPER
# =============================================================================

async def require_auth(request: Request) -> str:
    """Dependency to extract and verify the current user's JWT."""
    return await db.get_current_user(request)


# =============================================================================
# STRUCTURED REPORT BUILDER
# =============================================================================

def _build_structured_report(process_result: dict) -> Optional[StructuredReport]:
    """Build structured report from process_profile result for frontend consumption."""
    if not process_result or not process_result.get("valid"):
        return None

    assessment = process_result.get("assessment", {})
    gap = process_result.get("gap")
    paths = process_result.get("paths", [])
    target_role = process_result.get("target_role", "")
    initial_tasks = process_result.get("initial_tasks", [])
    profile = process_result.get("profile", {})

    req = get_role_requirements(target_role)
    role_display = req.role_name.replace("_", " ").title() if req else target_role.replace("_", " ").title()

    # Build skills dict
    skills = {}
    for skill_name, evidence in assessment.get("skills", {}).items():
        skills[skill_name] = SkillItem(
            self=evidence.self_reported,
            evidence=evidence.evidence_based,
            gaps=evidence.gaps
        )

    # Build contradictions
    contradictions = []
    for c in assessment.get("contradictions", []):
        contradictions.append({
            "skill": c.skill_name,
            "self": c.self_reported,
            "evidence": c.evidence_based,
            "message": f"You rated {c.skill_name} {c.self_reported}/5 but evidence shows {c.evidence_based}/5."
        })

    # Market stats
    location = profile.get("location", "pune")
    college_tier_str = profile.get("college_tier", "tier_3")
    college_tier = CollegeTier(college_tier_str) if college_tier_str in ["tier_1", "tier_2", "tier_3"] else CollegeTier.TIER_3

    salary_range = get_salary_range(target_role, location, college_tier) if req else (0.0, 0.0)
    callback_rate = get_callback_rate(target_role, college_tier) if req else 0.05
    timeline = estimate_timeline(college_tier_str, profile.get("current_state", "unknown"), target_role)
    if timeline < 0:
        timeline = 12

    # Build paths
    path_items = []
    for i, p in enumerate(paths):
        salary_str = ""
        if p.salary_trajectory:
            last_salary = p.salary_trajectory[-1][1]
            salary_str = f"₹{last_salary:.1f} LPA"
        else:
            salary_str = f"₹{salary_range[1]:.1f} LPA"

        path_items.append(PathItem(
            type=p.path_type.value.replace("_", " ").title(),
            timeline=p.total_duration_months,
            salary=salary_str,
            probability=p.success_probability,
            reasoning=p.reasoning,
            risks=p.risks[:3],
            steps=p.steps
        ))

    def _task_title(t) -> str:
        """Generate a short, precise title from a Task."""
        type_verb = {
            "project": "Build",
            "practice": "Practice",
            "learning": "Learn",
            "application": "Apply",
            "interview_prep": "Prepare",
        }.get(t.task_type.value if hasattr(t.task_type, "value") else str(t.task_type), "Do")
        skill = t.target_skill.replace("_", " ").title()
        if t.task_type.value == "project":
            return f"{type_verb} a {skill} project"
        elif t.task_type.value == "practice":
            return f"{type_verb} {skill} exercises"
        elif t.task_type.value == "learning":
            return f"{type_verb} {skill} fundamentals"
        elif t.task_type.value == "application":
            return f"{type_verb} to 3 {skill} roles"
        elif t.task_type.value == "interview_prep":
            return f"{type_verb} for {skill} interviews"
        return f"{type_verb} {skill}"

    # Build tasks
    task_items = []
    for i, t in enumerate(initial_tasks[:3], 1):
        task_items.append(TaskItem(
            number=i,
            title=_task_title(t),
            description=t.description,
            expected=t.expected_outcome,
            completed=False
        ))

    return StructuredReport(
        title=role_display,
        skills=skills,
        contradictions=contradictions,
        criticalGaps=assessment.get("critical_gaps", [])[:5],
        salary=f"₹{salary_range[0]:.1f} - {salary_range[1]:.1f} LPA",
        callbackRate=callback_rate,
        timeline=timeline,
        difficulty=req.hiring_difficulty.title() if req else "Unknown",
        paths=path_items,
        tasks=task_items,
        uncertainty_flags=process_result.get("uncertainty_flags", [])
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/", response_model=Dict[str, str])
def root():
    return {
        "message": "CareerGPS API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
def health():
    scraping_enabled = os.getenv("ENABLE_JD_SCRAPING", "true").lower() in ("true", "1", "yes")
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        roles_supported=len(get_all_roles()),
        live_scraping_enabled=scraping_enabled
    )


class SaveProfileRequest(BaseModel):
    target_role: str = ""
    college_tier: str = "tier_3"
    location: str = "pune"
    experience_months: int = 0
    current_state: str = "no_coding"
    self_assessment: dict = {}
    github_url: str = ""


@app.post("/api/v1/profile")
def save_user_profile(req: SaveProfileRequest, auth_user: dict = Depends(require_auth)):
    """Save or update the authenticated user's profile from form submission."""
    user_id = auth_user["id"]
    user_email = auth_user.get("email", "")
    try:
        db.upsert_profile(user_id, {
            "full_name": user_email,
            "college_tier": req.college_tier,
            "location": req.location,
            "experience_months": req.experience_months,
            "current_state": req.current_state,
            "selected_role": req.target_role,
            "self_assessment": req.self_assessment,
            "github_url": req.github_url,
        })
        return {"saved": True}
    except Exception as e:
        logger.warning(f"Failed to save profile: {e}")
        raise HTTPException(status_code=500, detail="Profile save failed")


@app.get("/api/v1/profile")
def get_user_profile(auth_user: dict = Depends(require_auth)):
    """Fetch the authenticated user's profile."""
    user_id = auth_user["id"]
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "id": profile.get("id"),
        "full_name": profile.get("full_name"),
        "college_tier": profile.get("college_tier"),
        "location": profile.get("location"),
        "experience_months": profile.get("experience_months", 0),
        "current_state": profile.get("current_state"),
        "selected_role": profile.get("selected_role"),
        "updated_at": profile.get("updated_at"),
    }


@app.get("/api/v1/roles", response_model=List[str])
def list_roles():
    """List all supported career roles."""
    return get_all_roles()


@app.get("/api/v1/roles/categories", response_model=List[str])
def list_categories():
    """List all role categories."""
    return get_role_categories()


@app.get("/api/v1/roles/category/{category}", response_model=List[str])
def roles_by_category(category: str):
    """Get roles filtered by category (e.g., engineering, data, design)."""
    roles = get_roles_by_category(category.lower())
    if not roles:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    return roles


@app.get("/api/v1/roles/{role_name}", response_model=RoleInfo)
def get_role(role_name: str):
    """Get detailed requirements for a specific role."""
    req = get_role_requirements(role_name)
    if not req:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")
    return RoleInfo(
        role_name=req.role_name,
        role_category=req.role_category,
        display_name=req.role_name.replace("_", " ").title(),
        min_experience_months=req.min_experience_months,
        required_skills=req.required_skills,
        preferred_skills=req.preferred_skills,
        framework_tools=req.framework_tools,
        salary_range_lpa=req.salary_range_lpa,
        hiring_difficulty=req.hiring_difficulty,
        tier_3_callback_rate=req.tier_3_callback_rate,
    )


@app.get("/api/v1/roles/search/{query}", response_model=RoleSuggestionResponse)
def search_role(query: str):
    """Search for a role by name. Returns the normalized role and similar suggestions."""
    normalized = normalize_role_name(query)
    known = is_role_supported(query)
    similar = suggest_similar_roles(query)
    return RoleSuggestionResponse(
        role=normalized,
        display_name=normalized.replace("_", " ").title(),
        similar_roles=similar,
        role_known=known
    )


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze_profile(profile: ProfileRequest, auth_user: dict = Depends(require_auth)):
    """
    Analyze a user profile and generate a career navigation report.
    Requires authentication.
    """
    user_id = auth_user["id"]
    user_email = auth_user.get("email", "")
    try:
        profile_dict = profile.model_dump()
        gps = CareerGPS()
        result = gps.process_profile(profile_dict)

        if not result.get("valid"):
            return AnalysisResponse(
                report=result["report_text"],
                target_role=normalize_role_name(profile.target_role),
                role_known=is_role_supported(profile.target_role),
                structured_data=None
            )

        structured = _build_structured_report(result)

        # Persist to Supabase
        try:
            db.upsert_profile(user_id, {
                "full_name": user_email,
                "college_tier": profile_dict.get("college_tier", "tier_3"),
                "location": profile_dict.get("location", "pune"),
                "experience_months": profile_dict.get("experience_months", 0),
                "current_state": profile_dict.get("current_state", "unknown"),
            })

            structured_dict = structured.model_dump() if structured else {}
            db.save_report(
                user_id=user_id,
                target_role=result["target_role"],
                report_text=result["report_text"],
                structured_data=structured_dict
            )
        except Exception as db_err:
            logger.warning(f"Failed to persist report to Supabase: {db_err}")

        return AnalysisResponse(
            report=result["report_text"],
            target_role=normalize_role_name(profile.target_role),
            role_known=is_role_supported(profile.target_role),
            structured_data=structured
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")


@app.post("/api/v1/analyze-agentic")
async def analyze_profile_agentic(profile: ProfileRequest, auth_user: dict = Depends(require_auth)):
    """
    LLM-powered agentic career analysis using Claude with tool calling.
    Streams Server-Sent Events showing Claude's reasoning trace and final report.

    SSE event types:
      {"type": "tool_start", "tool": str, "label": str}
      {"type": "tool_end",   "tool": str, "summary": str}
      {"type": "text_delta", "text": str}
      {"type": "done",       "structured_data": dict}
      {"type": "error",      "message": str}
    """
    from agents.llm_orchestrator import run_agentic_analysis
    profile_dict = profile.model_dump()

    async def generate():
        try:
            async for event in run_agentic_analysis(profile_dict):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as e:
            logger.exception("Agentic analysis failed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/v1/checkin", response_model=WeeklyCheckinResponse)
async def weekly_checkin(checkin: WeeklyCheckinRequest, auth_user: dict = Depends(require_auth)):
    user_id = auth_user["id"]
    target_role = (checkin.target_role or "").strip()
    if not target_role:
        raise HTTPException(status_code=400, detail="target_role is required")
    """
    Process a weekly check-in and generate the next week's tasks.
    Requires authentication.
    """
    try:
        # Load previous state from Supabase, filtered by role
        latest_report = db.get_latest_report(user_id, target_role)
        all_checkins = db.get_all_checkins(user_id, target_role)

        previous_state = {
            "paths": [],
            "target_role": target_role,
            "initial_tasks": [],
            "weekly_reports": [],
        }

        if latest_report and latest_report.get("structured_data"):
            sd = latest_report["structured_data"]
            # Keep the current request's target_role; don't let an old report
            # override it if the user has switched roles since then.
            # previous_state["target_role"] = latest_report.get("target_role", target_role)
            # Reconstruct paths from structured data
            for p in sd.get("paths", []):
                previous_state["paths"].append({
                    "steps": p.get("steps", []),
                })
            # Reconstruct initial tasks
            for t in sd.get("tasks", []):
                previous_state["initial_tasks"].append({
                    "task_id": f"w1_{t.get('title', '').lower().replace(' ', '_')}",
                    "task_type": "project",  # simplified
                    "description": t.get("description", ""),
                    "target_skill": "core_skill",
                    "expected_outcome": t.get("expected", ""),
                    "week": 1,
                    "completed": False,
                })

        # Reconstruct weekly reports from previous checkins
        for c in all_checkins:
            th = c.get("task_hours", {}) or {}
            previous_state["weekly_reports"].append({
                "week": c.get("week", 0),
                "tasks_completed": [],
                "tasks_missed": [],
                "progress_type": c.get("progress_type", "motion"),
                "skills_gained": [],
                "skills_stagnant": [],
                "market_signals": {
                    "applications_sent": c.get("applications_sent", 0),
                    "responses_received": c.get("responses_received", 0),
                    "interviews_attended": c.get("interviews_attended", 0),
                    "response_rate": c.get("responses_received", 0) / c.get("applications_sent", 1) if c.get("applications_sent", 0) > 0 else 0,
                },
                "red_flags": c.get("red_flags", []),
                "recommendation": c.get("recommendation", ""),
                "task_hours": th,
            })

        task_inputs = checkin.task_hours.model_dump() if checkin.task_hours else {}
        gps = CareerGPS()
        result = gps.weekly_checkin(
            week=checkin.week,
            tasks_completed=checkin.tasks_completed,
            applications_sent=checkin.applications_sent,
            responses_received=checkin.responses_received,
            interviews_attended=checkin.interviews_attended,
            previous_state=previous_state,
            task_inputs=task_inputs
        )

        # Serialize next_tasks for storage and response
        task_items = []
        for i, t in enumerate(result["next_tasks"][:3], 1):
            task_items.append(TaskItem(
                number=i,
                title=t.description.split(" - ")[0] if " - " in t.description else t.description,
                description=t.description,
                expected=t.expected_outcome,
                completed=False
            ))

        # Persist to Supabase
        db.save_checkin(user_id, checkin.week, {
            "tasks_completed": checkin.tasks_completed,
            "applications_sent": checkin.applications_sent,
            "responses_received": checkin.responses_received,
            "interviews_attended": checkin.interviews_attended,
            "checkin_report": result["checkin_text"],
            "next_tasks": [t.model_dump() for t in task_items],
            "progress_type": result["progress_type"],
            "recommendation": result["recommendation"],
            "red_flags": result["red_flags"],
            "target_role": target_role,
            "task_hours": task_inputs,
        })

        return WeeklyCheckinResponse(
            checkin_report=result["checkin_text"],
            week=checkin.week,
            progress_type=result["progress_type"],
            recommendation=result["recommendation"],
            red_flags=result["red_flags"],
            next_tasks=task_items
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Check-in failed")
        raise HTTPException(status_code=500, detail="Check-in failed. Please try again.")


@app.get("/api/v1/checkins")
def list_checkins(target_role: str = None, auth_user: dict = Depends(require_auth)):
    """List all check-ins for the authenticated user. Optionally filter by target_role."""
    user_id = auth_user["id"]
    checkins = db.get_all_checkins(user_id, target_role)
    return {
        "checkins": checkins,
        "count": len(checkins),
        "target_role": target_role,
    }


@app.get("/api/v1/checkins/roles")
def list_checkin_roles(auth_user: dict = Depends(require_auth)):
    """List all distinct target_roles the user has check-ins for."""
    user_id = auth_user["id"]
    roles = db.get_user_checkin_roles(user_id)
    return {"roles": roles}


@app.get("/api/v1/reports/roles")
def list_report_roles(auth_user: dict = Depends(require_auth)):
    """List all distinct target_roles the user has reports for."""
    user_id = auth_user["id"]
    roles = db.get_user_report_roles(user_id)
    return {"roles": roles}


@app.delete("/api/v1/checkins/{target_role}")
def delete_checkins(target_role: str, auth_user: dict = Depends(require_auth)):
    """Delete all check-ins AND reports for a specific target role."""
    user_id = auth_user["id"]
    db.delete_checkins_by_role(user_id, target_role)
    db.delete_reports_by_role(user_id, target_role)
    return {"deleted": True, "target_role": target_role}


@app.get("/api/v1/reports/latest")
def get_latest_report_endpoint(target_role: str = None, auth_user: dict = Depends(require_auth)):
    """Fetch the most recent report for the authenticated user. Optionally filter by target_role."""
    user_id = auth_user["id"]
    report = db.get_latest_report(user_id, target_role)
    if not report:
        raise HTTPException(status_code=404, detail="No report found")
    return {
        "id": report["id"],
        "target_role": report.get("target_role"),
        "report_text": report.get("report_text"),
        "structured_data": report.get("structured_data"),
        "created_at": report.get("created_at"),
    }


class SaveReportRequest(BaseModel):
    target_role: str
    report_text: str
    structured_data: dict = {}


@app.post("/api/v1/reports/save")
def save_report_endpoint(req: SaveReportRequest, auth_user: dict = Depends(require_auth)):
    """Save an AI-generated (agentic) report to Supabase."""
    user_id = auth_user["id"]
    report_id = db.save_report(
        user_id=user_id,
        target_role=req.target_role,
        report_text=req.report_text,
        structured_data=req.structured_data,
    )
    return {"saved": True, "id": report_id}


@app.get("/api/v1/roles/{role_name}/timeline")
def get_role_timeline(role_name: str, college_tier: str = "tier_3", current_state: str = "no_coding"):
    """Get estimated timeline for a role transition."""
    timeline = estimate_timeline(college_tier, current_state, role_name)
    if timeline < 0:
        return {"role": role_name, "timeline_months": None, "note": "No timeline estimate available for this combination"}
    return {"role": role_name, "college_tier": college_tier, "current_state": current_state, "timeline_months": timeline}


@app.get("/api/v1/roles/{role_name}/stepping-stones")
def get_stepping_stones(role_name: str, current_state: str = "no_coding"):
    """Get stepping-stone role suggestions for a target role."""
    suggestions = get_stepping_stone_suggestions(role_name, current_state)
    return {
        "target_role": role_name,
        "current_state": current_state,
        "suggestions": suggestions
    }


@app.get("/api/v1/market/{role_name}/provenance", response_model=MarketDataProvenance)
def get_market_provenance(role_name: str, location: str = "India"):
    """
    Expose where the market data for a role came from.
    Shows whether data is live (scraped) or static, with confidence scores.
    """
    try:
        provenance = get_data_provenance(role_name, location)
        return MarketDataProvenance(
            role=role_name,
            source=provenance["source"],
            freshness=provenance["freshness"],
            confidence=provenance["confidence"],
            scraped_at=provenance.get("scraped_at"),
            uncertainty_flags=provenance.get("uncertainty_flags", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Provenance lookup failed")


@app.post("/api/v1/market/{role_name}/refresh")
def refresh_market_data_endpoint(role_name: str, location: str = "India"):
    """
    Force a refresh of live market data for a role+location.
    Triggers real-time scraping from LinkedIn, Indeed, Naukri, and Glassdoor.
    """
    try:
        snapshot = refresh_market_data(role_name, location, force_refresh=True)
        return MarketSnapshotResponse(
            role=snapshot.role,
            location=snapshot.location,
            scraped_at=snapshot.scraped_at,
            sources=snapshot.sources,
            total_jobs_scraped=snapshot.total_jobs_scraped,
            top_skills=snapshot.top_skills,
            salary_range_lpa=snapshot.salary_range_lpa,
            experience_range_months=snapshot.experience_range_months,
            hiring_volume_indicator=snapshot.hiring_volume_indicator,
            top_companies=snapshot.top_companies,
            data_quality_score=snapshot.data_quality_score,
            uncertainty_flags=snapshot.uncertainty_flags,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Market data refresh failed")


# Global flag: disable live scraping on low-memory deployments
SCRAPING_ENABLED = os.getenv("ENABLE_JD_SCRAPING", "true").lower() in ("true", "1", "yes")


def _build_job_listings(jobs_data: list, limit: int) -> tuple:
    """Convert raw job dicts to JobListing models."""
    job_listings = []
    sources_used = set()
    for j in jobs_data[:limit]:
        sources_used.add(j.get("source", "cached"))
        job_listings.append(JobListing(
            source=j.get("source", "cached"),
            title=j.get("title", "Untitled"),
            company=j.get("company", ""),
            location=j.get("location", ""),
            description=(j.get("description", "")[:300] + "..." if len(j.get("description", "")) > 300 else j.get("description", "")),
            url=j.get("url", ""),
            skills_found=j.get("skills_found", []),
            salary_lpa=tuple(j.get("salary_lpa", [])) if j.get("salary_lpa") else None,
            experience_months=tuple(j.get("experience_months", [0, 0])) if j.get("experience_months") else (0, 0),
        ))
    return job_listings, list(sources_used)


@app.get("/api/v1/market/{role_name}/jobs", response_model=JobsResponse)
def get_scraped_jobs(role_name: str, location: str = "India", limit: int = 5, live: bool = False):
    """
    Return job listings for a role + location.

    By default reads from the Supabase cache (fast).
    Set ?live=true to trigger real-time scraping (HTTP-only, no browser).
    On low-memory deployments, falls back to realistic mock data.
    """
    try:
        # If live=true and scraping is enabled, use stealth browser scraper
        if live and SCRAPING_ENABLED:
            logger.info(f"[Live Scrape] Starting for {role_name} in {location}")
            try:
                from scrapers.jsearch_scraper import JSearchScraper
                from dataclasses import asdict
                scraper = JSearchScraper()
                raw_jobs = scraper.search_jobs(role_name, location, limit=limit)

                if raw_jobs:
                    jobs_data = [asdict(j) for j in raw_jobs]
                    for j in jobs_data:
                        if j.get("salary_lpa") and isinstance(j["salary_lpa"], tuple):
                            j["salary_lpa"] = list(j["salary_lpa"])
                        if j.get("experience_months") and isinstance(j["experience_months"], tuple):
                            j["experience_months"] = list(j["experience_months"])

                    try:
                        db.save_market_snapshot(role_name, location, {
                            "jobs": jobs_data,
                            "salary_range_lpa": None,
                            "experience_range_months": [0, 60],
                            "top_skills": [],
                            "top_companies": list({j.get("company", "") for j in jobs_data if j.get("company")})[:5],
                            "hiring_volume_indicator": "medium",
                            "data_quality_score": 0.9,
                            "uncertainty_flags": [],
                        })
                    except Exception as cache_err:
                        logger.warning(f"Failed to save live scrape to cache: {cache_err}")

                    job_listings, sources_used = _build_job_listings(jobs_data, limit)
                    return JobsResponse(
                        role=role_name,
                        location=location,
                        total_jobs=len(job_listings),
                        jobs=job_listings,
                        scraped_at=datetime.now().isoformat(),
                        sources_used=sources_used,
                        note=f"Live jobs: {len(job_listings)} positions from {', '.join(set(sources_used))}.",
                    )
            except Exception as scrape_err:
                logger.warning(f"Live scrape failed, falling back to mock data: {scrape_err}")

        # Cache-first path (default)
        snapshot = db.get_market_snapshot(role_name, location)
        if snapshot and snapshot.get("jobs"):
            job_listings, sources_used = _build_job_listings(snapshot.get("jobs", []), limit)
            return JobsResponse(
                role=role_name,
                location=location,
                total_jobs=len(job_listings),
                jobs=job_listings,
                scraped_at=snapshot.get("scraped_at", datetime.now().isoformat()),
                sources_used=sources_used,
                note=f"Showing cached jobs from {snapshot.get('scraped_at', 'unknown')[:10]}. Click 'Scrape Jobs' for fresh listings.",
            )

        # Fallback: generate realistic mock jobs (deterministic per role+location)
        mock_jobs = generate_mock_jobs(role_name, location, count=limit)
        job_listings, sources_used = _build_job_listings(mock_jobs, limit)
        return JobsResponse(
            role=role_name,
            location=location,
            total_jobs=len(job_listings),
            jobs=job_listings,
            scraped_at=datetime.now().isoformat(),
            sources_used=["mock"],
            note=f"Showing realistic sample jobs for {role_name.replace('_', ' ').title()}. Live scraping is {'disabled' if not SCRAPING_ENABLED else 'currently unavailable'}.",
        )
    except Exception as e:
        logger.exception("Job fetch failed")
        raise HTTPException(status_code=500, detail="Job fetch failed")


@app.get("/api/v1/market/jobs/all", response_model=JobsResponse)
def get_all_cached_jobs(limit: int = 50):
    """
    Return ALL cached jobs from every market snapshot.
    This is what 'Get Cached Jobs' calls — it shows everything in the database.
    """
    try:
        snapshots = db.get_all_market_snapshots(limit=100)
        if not snapshots:
            return JobsResponse(
                role="all",
                location="all",
                total_jobs=0,
                jobs=[],
                scraped_at=datetime.now().isoformat(),
                sources_used=[],
                note="No cached jobs found in the database. Run the weekly refresh script or click 'Get Live Jobs'.",
            )

        job_listings = []
        sources_used = set()
        seen_urls = set()

        for snapshot in snapshots:
            for j in snapshot.get("jobs", []):
                url = j.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                sources_used.add(j.get("source", "cached"))
                job_listings.append(JobListing(
                    source=j.get("source", "cached"),
                    title=j.get("title", "Untitled"),
                    company=j.get("company", ""),
                    location=j.get("location", "India"),
                    description=j.get("description", "")[:300] + "..." if len(j.get("description", "")) > 300 else j.get("description", ""),
                    url=url,
                    skills_found=j.get("skills_found", []),
                    salary_lpa=tuple(j.get("salary_lpa", [])) if j.get("salary_lpa") else None,
                    experience_months=tuple(j.get("experience_months", [0, 0])) if j.get("experience_months") else (0, 0),
                ))

        return JobsResponse(
            role="all",
            location="all",
            total_jobs=len(job_listings),
            jobs=job_listings[:limit],
            scraped_at=datetime.now().isoformat(),
            sources_used=list(sources_used),
            note=f"Showing {len(job_listings[:limit])} cached jobs from {len(snapshots)} role/location combinations.",
        )
    except Exception as e:
        logger.exception("Failed to fetch all cached jobs")
        raise HTTPException(status_code=500, detail="Failed to fetch cached jobs")


@app.get("/api/v1/market/sources")
def list_data_sources():
    """List all configured market data sources and their status."""
    return {
        "sources": [
            {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs", "type": "scraper", "enabled": True},
            {"name": "Indeed India", "url": "https://in.indeed.com", "type": "scraper", "enabled": True},
            {"name": "Naukri", "url": "https://www.naukri.com", "type": "scraper", "enabled": True},
            {"name": "Glassdoor India", "url": "https://www.glassdoor.co.in", "type": "scraper", "enabled": True},
            {"name": "Static Database", "url": "internal", "type": "fallback", "enabled": True},
        ],
        "scraping_enabled": os.getenv("ENABLE_JD_SCRAPING", "true").lower() in ("true", "1", "yes"),
        "cache_ttl_hours": 24 * 7,  # weekly refresh
    }


@app.post("/api/v1/upload-resume", response_model=ResumeUploadResponse)
def upload_resume(file: UploadFile = File(...)):
    """
    Upload a resume PDF or DOCX file.
    Extracts text and identifies skills for the evidence-based assessor.
    """
    import io
    from scrapers.scraper_utils import normalize_skills

    allowed_extensions = {".pdf", ".docx"}
    ext = os.path.splitext(file.filename or "")[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {ext}. Only .pdf and .docx are allowed."
        )

    # File size limit (5MB)
    max_size = 5 * 1024 * 1024
    contents = file.file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Max size is 5MB.")

    try:
        resume_text = ""

        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(contents))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    resume_text += page_text + "\n"

        elif ext == ".docx":
            from docx import Document
            doc = Document(io.BytesIO(contents))
            for para in doc.paragraphs:
                resume_text += para.text + "\n"

        resume_text = resume_text.strip()
        word_count = len(resume_text.split())
        extracted_skills = normalize_skills(resume_text)

        return ResumeUploadResponse(
            filename=file.filename or "resume",
            resume_text=resume_text,
            word_count=word_count,
            extracted_skills=extracted_skills,
            message=f"Successfully extracted {word_count} words and {len(extracted_skills)} skills from {ext} file."
        )

    except Exception as e:
        logger.exception("Resume parsing failed")
        raise HTTPException(status_code=500, detail="Failed to parse resume")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
