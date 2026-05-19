"""
Supabase Database Client for CareerGPS
Handles auth verification, data persistence, and market snapshot queries.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import Request, HTTPException
from jose import jwt, JWTError
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """Return a Supabase client initialized with the service role key."""
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _supabase = create_client(url, key)
    return _supabase


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

async def get_current_user(request: Request) -> dict:
    """
    Extract and verify the JWT from the Authorization header.
    Returns a dict with the user's UUID (id) and email.
    Raises HTTPException 401 if token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        supabase = get_supabase()
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {
            "id": str(user.user.id),
            "email": user.user.email or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Auth verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def upsert_profile(user_id: str, profile_data: dict) -> None:
    """Insert or update a user profile."""
    supabase = get_supabase()
    # Fetch existing profile to preserve full_name if already set
    existing = None
    try:
        resp = supabase.table("profiles").select("full_name, selected_role").eq("id", user_id).single().execute()
        existing = resp.data
    except Exception:
        pass

    full_name = profile_data.get("full_name", "")
    if not full_name and existing and existing.get("full_name"):
        full_name = existing.get("full_name")

    payload = {
        "id": user_id,
        "full_name": full_name,
        "college_tier": profile_data.get("college_tier", "tier_3"),
        "location": profile_data.get("location", "pune"),
        "experience_months": profile_data.get("experience_months", 0),
        "current_state": profile_data.get("current_state", "unknown"),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if profile_data.get("selected_role"):
        payload["selected_role"] = profile_data["selected_role"]
    elif existing and existing.get("selected_role"):
        payload["selected_role"] = existing["selected_role"]

    supabase.table("profiles").upsert(payload).execute()


def get_profile(user_id: str) -> Optional[dict]:
    """Fetch a user profile by ID."""
    supabase = get_supabase()
    resp = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    return resp.data if resp.data else None


def set_selected_role(user_id: str, role: str) -> None:
    """Update the user's currently selected target role."""
    supabase = get_supabase()
    supabase.table("profiles").upsert({
        "id": user_id,
        "selected_role": role,
        "updated_at": datetime.utcnow().isoformat(),
    }).execute()


def get_selected_role(user_id: str) -> Optional[str]:
    """Fetch the user's currently selected target role."""
    supabase = get_supabase()
    try:
        resp = supabase.table("profiles").select("selected_role").eq("id", user_id).single().execute()
        return resp.data.get("selected_role") if resp.data else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def save_report(user_id: str, target_role: str, report_text: str, structured_data: dict) -> str:
    """Save a generated career report. Returns the report UUID."""
    supabase = get_supabase()
    resp = supabase.table("reports").insert({
        "user_id": user_id,
        "target_role": target_role,
        "report_text": report_text,
        "structured_data": structured_data,
    }).execute()
    return resp.data[0]["id"] if resp.data else ""


def get_latest_report(user_id: str, target_role: Optional[str] = None) -> Optional[dict]:
    """Fetch the most recent report for a user, optionally filtered by role."""
    supabase = get_supabase()
    query = (
        supabase.table("reports")
        .select("*")
        .eq("user_id", user_id)
    )
    if target_role:
        query = query.eq("target_role", target_role)
    resp = query.order("created_at", desc=True).limit(1).execute()
    return resp.data[0] if resp.data else None


def get_reports(user_id: str, limit: int = 10) -> List[dict]:
    """Fetch recent reports for a user."""
    supabase = get_supabase()
    resp = (
        supabase.table("reports")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


# ---------------------------------------------------------------------------
# Checkin helpers
# ---------------------------------------------------------------------------

def save_checkin(user_id: str, week: int, data: dict) -> None:
    """Upsert a weekly check-in."""
    supabase = get_supabase()
    cycle = data.get("cycle", 1)
    payload = {
        "user_id": user_id,
        "week": week,
        "cycle": cycle,
        "tasks_completed": data.get("tasks_completed", []),
        "applications_sent": data.get("applications_sent", 0),
        "responses_received": data.get("responses_received", 0),
        "interviews_attended": data.get("interviews_attended", 0),
        "checkin_report": data.get("checkin_report", ""),
        "next_tasks": data.get("next_tasks", []),
        "progress_type": data.get("progress_type", ""),
        "recommendation": data.get("recommendation", ""),
        "red_flags": data.get("red_flags", []),
        "updated_at": datetime.utcnow().isoformat(),
    }
    target_role = data.get("target_role")
    if target_role is not None:
        payload["target_role"] = target_role
    task_hours = data.get("task_hours")
    if task_hours is not None:
        payload["task_hours"] = task_hours

    # Upsert keyed on (user_id, target_role, cycle, week)
    try:
        supabase.table("checkins").upsert(payload, on_conflict="user_id,target_role,cycle,week").execute()
        return
    except Exception as e:
        err_str = str(e).lower()
        if not any(k in err_str for k in ("unique", "conflict", "constraint", "column", "does not exist")):
            raise
        logger.warning(f"upsert on (user_id,target_role,cycle,week) failed: {e}")

    # Fallback: delete-then-insert
    try:
        q = (
            supabase.table("checkins")
            .delete()
            .eq("user_id", user_id)
            .eq("week", week)
            .eq("cycle", cycle)
        )
        if target_role:
            q = q.eq("target_role", target_role)
        q.execute()
        supabase.table("checkins").insert(payload).execute()
        return
    except Exception as e:
        logger.error(f"delete+insert fallback also failed: {e}")
        raise


def get_checkin(user_id: str, week: int, target_role: str = None) -> Optional[dict]:
    """Fetch a specific weekly check-in. Optionally filter by target_role."""
    supabase = get_supabase()
    query = (
        supabase.table("checkins")
        .select("*")
        .eq("user_id", user_id)
        .eq("week", week)
    )
    if target_role:
        query = query.eq("target_role", target_role)
    resp = query.limit(1).execute()
    return resp.data[0] if resp.data else None


def get_all_checkins(user_id: str, target_role: str = None) -> List[dict]:
    """Fetch all check-ins for a user, ordered by week. Optionally filter by target_role."""
    supabase = get_supabase()
    query = (
        supabase.table("checkins")
        .select("*")
        .eq("user_id", user_id)
        .order("week", desc=False)
    )
    if target_role:
        try:
            resp = query.eq("target_role", target_role).execute()
            return resp.data or []
        except Exception as e:
            logger.warning(f"target_role filter failed: {e}")
            # target_role column may not exist; fall through to unfiltered
    resp = query.execute()
    return resp.data or []


def get_user_checkin_roles(user_id: str) -> List[str]:
    """Fetch all distinct target_roles the user has check-ins for."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("checkins")
            .select("target_role")
            .eq("user_id", user_id)
            .execute()
        )
        roles = set()
        for row in resp.data or []:
            if row.get("target_role"):
                roles.add(row["target_role"])
        return sorted(list(roles))
    except Exception:
        return []


def get_user_report_roles(user_id: str) -> List[str]:
    """Fetch all distinct target_roles the user has reports for."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("reports")
            .select("target_role")
            .eq("user_id", user_id)
            .execute()
        )
        roles = set()
        for row in resp.data or []:
            if row.get("target_role"):
                roles.add(row["target_role"])
        return sorted(list(roles))
    except Exception:
        return []


def delete_checkins_by_role(user_id: str, target_role: str) -> None:
    """Delete all check-ins for a user+role combination."""
    supabase = get_supabase()
    try:
        (
            supabase.table("checkins")
            .delete()
            .eq("user_id", user_id)
            .eq("target_role", target_role)
            .execute()
        )
    except Exception:
        # target_role column may not exist yet; nothing to delete
        pass


def delete_reports_by_role(user_id: str, target_role: str) -> None:
    """Delete all reports for a user+role combination."""
    supabase = get_supabase()
    try:
        (
            supabase.table("reports")
            .delete()
            .eq("user_id", user_id)
            .eq("target_role", target_role)
            .execute()
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Market snapshot helpers
# ---------------------------------------------------------------------------

def get_market_snapshot(role: str, location: str) -> Optional[dict]:
    """
    Fetch cached market snapshot for a role+location.
    Returns None if not found or expired.
    """
    supabase = get_supabase()
    resp = (
        supabase.table("market_snapshots")
        .select("*")
        .eq("role", role)
        .eq("location", location)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None

    snapshot = resp.data[0]
    # Check expiry — handle both tz-aware and naive datetimes
    expires = snapshot.get("expires_at")
    if expires:
        try:
            # Parse the expiry time; Supabase returns ISO 8601 with 'Z' or offset
            expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            # Use timezone-aware UTC now for comparison
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            if expires_dt < now_utc:
                return None
        except Exception:
            # If parsing fails, treat as not expired
            pass
    return snapshot


def get_all_market_snapshots(limit: int = 100) -> List[dict]:
    """Fetch all non-expired market snapshots."""
    supabase = get_supabase()
    resp = (
        supabase.table("market_snapshots")
        .select("*")
        .limit(limit)
        .execute()
    )
    if not resp.data:
        return []

    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    results = []
    for row in resp.data:
        expires = row.get("expires_at")
        if expires:
            try:
                expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                if expires_dt < now_utc:
                    continue
            except Exception:
                pass
        results.append(row)
    return results


def save_market_snapshot(role: str, location: str, data: dict) -> None:
    """Upsert a market snapshot, keyed on (role, location)."""
    supabase = get_supabase()
    payload = {
        "role": role,
        "location": location,
        "jobs": data.get("jobs", []),
        "salary_range_lpa": data.get("salary_range_lpa"),
        "experience_range_months": data.get("experience_range_months", [0, 0]),
        "top_skills": data.get("top_skills", []),
        "top_companies": data.get("top_companies", []),
        "hiring_volume_indicator": data.get("hiring_volume_indicator", "unknown"),
        "data_quality_score": data.get("data_quality_score", 0),
        "uncertainty_flags": data.get("uncertainty_flags", []),
        "scraped_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + __import__("datetime").timedelta(days=7)).isoformat(),
    }
    try:
        # Use on_conflict to update the existing row when (role, location) already exists
        supabase.table("market_snapshots").upsert(
            payload, on_conflict="role,location"
        ).execute()
    except Exception:
        # Fallback: delete existing and re-insert (handles clients that don't support on_conflict kwarg)
        supabase.table("market_snapshots").delete().eq("role", role).eq("location", location).execute()
        supabase.table("market_snapshots").insert(payload).execute()


# ---------------------------------------------------------------------------
# Serialization helpers for dataclasses
# ---------------------------------------------------------------------------

def task_to_dict(task) -> dict:
    """Convert a Task dataclass to a serializable dict."""
    from agents.progress_tracker import TaskType
    return {
        "task_id": task.task_id,
        "task_type": task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type),
        "description": task.description,
        "target_skill": task.target_skill,
        "expected_outcome": task.expected_outcome,
        "week": task.week,
        "completed": task.completed,
        "completion_date": task.completion_date.isoformat() if task.completion_date else None,
        "evidence": task.evidence,
    }


def weekly_report_to_dict(report) -> dict:
    """Convert a WeeklyReport dataclass to a serializable dict."""
    from agents.progress_tracker import ProgressType
    return {
        "week": report.week,
        "tasks_completed": [task_to_dict(t) for t in report.tasks_completed],
        "tasks_missed": [task_to_dict(t) for t in report.tasks_missed],
        "progress_type": report.progress_type.value if hasattr(report.progress_type, "value") else str(report.progress_type),
        "skills_gained": report.skills_gained,
        "skills_stagnant": report.skills_stagnant,
        "market_signals": report.market_signals,
        "red_flags": report.red_flags,
        "recommendation": report.recommendation,
    }
