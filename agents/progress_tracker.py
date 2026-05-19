"""
Progress Tracker Module
Distinguishes COMPLIANCE (checking boxes) from REAL PROGRESS (skill application).
Enhanced with quantitative input analysis, trend-aware feedback, and role-specific tasks.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime, timedelta

try:
    from data.market_data import get_role_requirements
except ImportError:
    def get_role_requirements(role_name):
        return None


def _fmt(skill: str) -> str:
    """Convert snake_case skill names to Title Case for display."""
    if not skill:
        return skill
    return skill.replace("_", " ").title()


def _get_task_inputs(w):
    """Handle both WeeklyReport dataclass and plain dict from DB."""
    if isinstance(w, dict):
        return w.get("task_inputs", {}) or w.get("task_hours", {})
    return w.task_inputs


def _get_market_signals(w):
    if isinstance(w, dict):
        return w.get("market_signals", {})
    return w.market_signals


def _get_recommendation(w):
    if isinstance(w, dict):
        return w.get("recommendation", "")
    return w.recommendation


class TaskType(Enum):
    LEARNING = "learning"
    PRACTICE = "practice"
    PROJECT = "project"
    APPLICATION = "application"
    INTERVIEW_PREP = "interview_prep"
    NETWORKING = "networking"


class ProgressType(Enum):
    COMPLIANCE = "compliance"
    MOTION = "motion"
    REAL_PROGRESS = "real_progress"
    BREAKTHROUGH = "breakthrough"


@dataclass
class Task:
    task_id: str
    task_type: TaskType
    description: str
    target_skill: str
    expected_outcome: str
    week: int
    completed: bool = False
    completion_date: Optional[datetime] = None
    evidence: Optional[str] = None


@dataclass
class WeeklyReport:
    week: int
    tasks_completed: List[Task]
    tasks_missed: List[Task]
    progress_type: ProgressType
    skills_gained: List[str]
    skills_stagnant: List[str]
    market_signals: Dict[str, any]
    red_flags: List[str]
    recommendation: str
    task_inputs: Dict[str, int] = field(default_factory=dict)


class ProgressTracker:
    """
    Tracks real progress vs compliance using quantitative inputs and trend analysis.
    Input semantics:
      - learning: hours spent
      - practice: hours spent
      - project: quantity of tasks/features shipped
      - application: quantity of jobs applied to
    """

    def __init__(self):
        self.weekly_tasks: Dict[int, List[Task]] = {}
        self.completed_tasks: List[Task] = []
        self.skill_history: Dict[str, List[int]] = {}

    def add_weekly_plan(self, week: int, tasks: List[Task]):
        """Store weekly tasks, normalizing dicts to Task objects if needed."""
        normalized = []
        for t in tasks:
            if isinstance(t, dict):
                try:
                    task_type = TaskType(t.get('task_type', 'project')) if isinstance(t.get('task_type'), str) else TaskType.PROJECT
                except ValueError:
                    task_type = TaskType.PROJECT
                normalized.append(Task(
                    task_id=t.get('task_id', ''),
                    task_type=task_type,
                    description=t.get('description', ''),
                    target_skill=t.get('target_skill', ''),
                    expected_outcome=t.get('expected_outcome', ''),
                    week=t.get('week', week),
                    completed=t.get('completed', False),
                ))
            else:
                normalized.append(t)
        self.weekly_tasks[week] = normalized

    def record_completion(self, task_id: str, evidence: Optional[str] = None):
        for week, tasks in self.weekly_tasks.items():
            for task in tasks:
                if task.task_id == task_id:
                    task.completed = True
                    task.completion_date = datetime.now()
                    task.evidence = evidence
                    self.completed_tasks.append(task)
                    return True
        return False

    def analyze_week(self, week: int,
                     applications_sent: int = 0,
                     responses_received: int = 0,
                     interviews_attended: int = 0,
                     task_inputs: Optional[Dict[str, int]] = None,
                     recent_reports: Optional[List[WeeklyReport]] = None) -> WeeklyReport:
        """
        Analyze a week's progress using quantitative inputs and trend context.
        task_inputs keys: learning (hours), practice (hours), project (qty), application (qty)
        """
        task_inputs = task_inputs or {}
        recent_reports = recent_reports or []

        tasks = self.weekly_tasks.get(week, [])
        completed = [t for t in tasks if t.completed]
        missed = [t for t in tasks if not t.completed]

        lh = task_inputs.get("learning", 0)   # hours
        prh = task_inputs.get("practice", 0)  # hours
        pq = task_inputs.get("project", 0)    # quantity
        aq = applications_sent                 # quantity (from separate param)
        total = lh + prh + pq + aq

        # Quantitative progress classification
        has_project = pq >= 1
        has_practice = prh >= 1
        has_application = aq >= 1
        heavy_learning = lh >= 3
        only_learning = total > 0 and pq == 0 and prh == 0 and aq == 0

        # Count consecutive weeks with zero applications (including this week)
        no_app_streak = 0
        if aq == 0:
            no_app_streak = 1
            for w in reversed(recent_reports or []):
                if _get_market_signals(w).get("applications_sent", 0) == 0:
                    no_app_streak += 1
                else:
                    break

        if only_learning or (heavy_learning and pq == 0):
            progress_type = ProgressType.COMPLIANCE
        elif pq >= 2 and has_application:
            progress_type = ProgressType.BREAKTHROUGH
        elif pq >= 2 and not has_application and no_app_streak >= 2:
            # Good project output but no market testing for 2+ weeks → not real progress yet
            progress_type = ProgressType.MOTION
        elif pq >= 2 or (prh >= 2 and has_application):
            progress_type = ProgressType.REAL_PROGRESS
        else:
            progress_type = ProgressType.MOTION

        # Skills tracking
        skills_gained = []
        skills_stagnant = []
        for task in completed:
            if task.task_type in [TaskType.PROJECT, TaskType.PRACTICE]:
                if task.evidence:
                    skills_gained.append(task.target_skill)
                else:
                    skills_stagnant.append(task.target_skill)
            elif task.task_type == TaskType.LEARNING:
                skills_stagnant.append(task.target_skill)

        # Red flags
        red_flags = []
        if only_learning and lh >= 3:
            red_flags.append("compliance_without_application: Learning without building")
        if pq > 0 and aq == 0:
            red_flags.append("building_without_testing: Building but not applying")
        if applications_sent > 0 and responses_received == 0:
            if week > 2:
                red_flags.append("application_without_feedback: No responses from applications")
        if missed:
            red_flags.append(f"missed_tasks: {len(missed)} tasks not completed")

        # Generate trend-aware recommendation
        recommendation = self._generate_recommendation(
            progress_type, completed, missed, red_flags,
            applications_sent, responses_received, interviews_attended,
            task_inputs, recent_reports
        )

        return WeeklyReport(
            week=week,
            tasks_completed=completed,
            tasks_missed=missed,
            progress_type=progress_type,
            skills_gained=list(set(skills_gained)),
            skills_stagnant=list(set(skills_stagnant)),
            market_signals={
                "applications_sent": applications_sent,
                "responses_received": responses_received,
                "interviews_attended": interviews_attended,
                "response_rate": responses_received / applications_sent if applications_sent > 0 else 0
            },
            red_flags=red_flags,
            recommendation=recommendation,
            task_inputs=task_inputs
        )

    def _generate_recommendation(self, progress_type: ProgressType,
                                 completed: List[Task], missed: List[Task],
                                 red_flags: List[str],
                                 applications_sent: int,
                                 responses_received: int,
                                 interviews_attended: int,
                                 task_inputs: Dict[str, int],
                                 recent_reports: List[WeeklyReport]) -> str:
        """Generate concise, professional, trend-aware recommendation."""

        lh = task_inputs.get("learning", 0)
        prh = task_inputs.get("practice", 0)
        pq = task_inputs.get("project", 0)
        aq = applications_sent

        prev_weeks = recent_reports[-3:] if recent_reports else []
        prev_learning = sum(_get_task_inputs(w).get("learning", 0) for w in prev_weeks)
        prev_project = sum(_get_task_inputs(w).get("project", 0) for w in prev_weeks)
        prev_apps = sum(_get_market_signals(w).get("applications_sent", 0) for w in prev_weeks)
        prev_responses = sum(_get_market_signals(w).get("responses_received", 0) for w in prev_weeks)
        prev_interviews = sum(_get_market_signals(w).get("interviews_attended", 0) for w in prev_weeks)
        weeks_of_data = len(prev_weeks) + 1
        avg_prev_project = prev_project / max(len(prev_weeks), 1)

        paragraphs = []

        # Main progress assessment
        if progress_type == ProgressType.COMPLIANCE:
            if weeks_of_data >= 3 and prev_project == 0:
                paragraphs.append(
                    f"Your inputs this week show a learning-heavy pattern. "
                    f"You spent {lh} hours learning and completed {pq} project tasks. "
                    f"For {weeks_of_data} consecutive weeks, project work has been at zero. "
                    f"This is the most common trap that stalls progress. "
                    f"Shift your focus from consuming content to building something tangible."
                )
            else:
                paragraphs.append(
                    f"Your week was weighted toward learning. "
                    f"You spent {lh} hours on tutorials and courses but shipped {pq} project tasks. "
                    f"Knowledge without application does not show up in interviews. "
                    f"Dedicate at least half your time to building this week."
                )

        elif progress_type == ProgressType.MOTION:
            # Count no-app streak for context
            no_app_streak = 0
            if aq == 0:
                no_app_streak = 1
                for w in reversed(prev_weeks):
                    if _get_market_signals(w).get("applications_sent", 0) == 0:
                        no_app_streak += 1
                    else:
                        break

            if pq >= 2 and aq == 0 and no_app_streak >= 2:
                # Good building but no market testing for 2+ weeks — this is the key case to flag
                paragraphs.append(
                    f"You shipped {pq} project tasks this week — solid building output. "
                    f"But you have sent zero applications for {no_app_streak} weeks straight. "
                    f"Building without testing the market is guesswork. "
                    f"Your portfolio exists to open doors — start sending it out. "
                    f"Apply to at least 5 roles this week."
                )
            else:
                paragraphs.append(
                    f"You stayed active this week with {lh} learning hours, {pq} project tasks, "
                    f"{prh} practice hours, and {aq} applications. "
                )
                if pq == 0:
                    paragraphs[-1] += " However, you shipped zero project tasks. Employers need to see what you have built. Pick one feature and ship it."
                elif aq == 0:
                    paragraphs[-1] += " However, you did not apply to any jobs. Building without market testing is guesswork. Send at least 3 applications this week."
                else:
                    paragraphs[-1] += " To break into real progress, increase your project output to at least 2 tasks per week."

        elif progress_type == ProgressType.REAL_PROGRESS:
            trend = ""
            if prev_project > 0 and pq > avg_prev_project:
                trend = f" Your project output is up from your {avg_prev_project:.1f} weekly average."
            if aq == 0:
                # Good building but zero market testing
                paragraphs.append(
                    f"Good building week. You shipped {pq} project tasks.{trend} "
                    f"Your portfolio is growing — now start testing the market. "
                    f"Send at least 3 applications this week to turn this into real progress."
                )
            else:
                paragraphs.append(
                    f"Strong week. You shipped {pq} project tasks and applied to {aq} jobs.{trend} "
                    f"You are building skills and testing the market in parallel."
                )
                if responses_received == 0:
                    paragraphs[-1] += " You are applying but not hearing back yet. Keep the volume up and track which roles respond."
                else:
                    paragraphs[-1] += " Consistency beats intensity. Maintain this cadence."

        elif progress_type == ProgressType.BREAKTHROUGH:
            paragraphs.append(
                f"Excellent week. You shipped {pq} project tasks, practiced for {prh} hours, "
                f"and applied to {aq} jobs. This is the combination that produces results."
            )
            if responses_received > 0:
                paragraphs[-1] += f" You received {responses_received} responses. The market is validating your work."
            paragraphs.append("Do not break this streak. Protect your project time above all else.")

        # Application trend analysis
        total_apps = applications_sent + prev_apps
        total_responses = responses_received + prev_responses
        if total_apps >= 15 and total_responses == 0 and applications_sent > 0:
            paragraphs.append(
                f"Your application pipeline needs attention. You have sent {total_apps} total applications with zero responses. "
                f"This signals a resume or portfolio issue, not a volume problem. Stop applying and fix your profile first."
            )
        elif applications_sent >= 5 and responses_received == 0:
            paragraphs.append(
                f"No responses from {applications_sent} applications this week. "
                f"If this trend continues, your resume or portfolio is the bottleneck. Get feedback before sending more."
            )
        elif responses_received > 0:
            rate = (responses_received / applications_sent) * 100
            paragraphs.append(f"Response rate this week: {rate:.1f}% ({responses_received}/{applications_sent}).")

        # Interview trend
        if interviews_attended > 0:
            total_int = interviews_attended + prev_interviews
            paragraphs.append(
                f"You attended {interviews_attended} interview(s) this week, {total_int} total. "
                f"Focus on converting these into offers by reviewing your performance after each one."
            )
        elif prev_interviews >= 3 and interviews_attended == 0:
            paragraphs.append(
                "You had interviews in previous weeks but none scheduled this week. "
                "Keep your pipeline full while you prepare for the rounds you have."
            )

        return "\n\n".join(paragraphs) if paragraphs else "Continue your current plan."

    def detect_stagnation(self, weeks: List[WeeklyReport]) -> Optional[str]:
        if len(weeks) < 2:
            return None

        recent = weeks[-3:] if len(weeks) >= 3 else weeks

        # Compliance loop: learning hours but zero project quantity
        compliance_weeks = sum(
            1 for w in recent
            if _get_task_inputs(w).get("project", 0) == 0 and _get_task_inputs(w).get("practice", 0) == 0
            and _get_task_inputs(w).get("learning", 0) > 0
        )
        if compliance_weeks >= 2:
            return (
                "STAGNATION ALERT: Multiple weeks of learning without project output. "
                "You must ship something tangible this week. Zero tutorials. One shipped feature."
            )

        # Application black hole
        total_apps = sum(_get_market_signals(w).get("applications_sent", 0) for w in recent)
        total_responses = sum(_get_market_signals(w).get("responses_received", 0) for w in recent)
        if total_apps >= 15 and total_responses == 0:
            return (
                "APPLICATION BLACK HOLE: 15+ applications with zero responses. "
                "Your profile is not passing screening. Stop applying. Fix your resume and projects first."
            )

        # Interview loop
        total_interviews = sum(_get_market_signals(w).get("interviews_attended", 0) for w in recent)
        if total_interviews >= 3 and "interview" not in str(_get_recommendation(recent[-1])).lower():
            return (
                "INTERVIEW LOOP: Multiple interviews but no conversion. "
                "This is a skills gap, not luck. Focus on structured interview practice."
            )

        # Low activity
        total_hours = sum(sum(_get_task_inputs(w).values()) for w in recent)
        if total_hours < 5 and len(recent) >= 2:
            return (
                "LOW ACTIVITY: Less than 5 hours per week. At this pace, progress will take years. "
                "Commit to at least 10 focused hours this week."
            )

        return None

    def _get_week_theme(self, week: int, role_skills: List[str], cycle: int = 1) -> tuple:
        """
        Determine the theme for a given week using a 6-week cycle.
        Returns (theme_id, title, description, expected_outcome, target_skill).
        Skills rotate across cycles so users don't see the same tasks repeatedly.
        cycle=1 → foundational tasks; cycle=2+ → production-grade tasks.
        """
        n_skills = len(role_skills)
        cycle_index = week // 6  # which 6-week block we're in

        # Rotate skills across cycles so each 6-week block uses different skills
        skill_a = role_skills[(cycle_index * 3 + 0) % n_skills] if n_skills else "core"
        skill_b = role_skills[(cycle_index * 3 + 1) % n_skills] if n_skills else "secondary"
        skill_c = role_skills[(cycle_index * 3 + 2) % n_skills] if n_skills else "advanced"

        cycle_pos = week % 6
        build_on = f" Apply patterns from Cycle {cycle - 1} — raise the bar on code quality and test coverage." if cycle > 1 else ""

        if cycle_pos == 1:
            if week == 1:
                return (
                    "setup",
                    "Set up your project foundation",
                    "Initialize a repository, configure dependencies, and create the project structure. Focus on a clean scaffold with README and setup instructions.",
                    "Working repo with README and setup instructions",
                    skill_a,
                )
            return (
                "setup",
                f"Launch a new {_fmt(skill_a)} project — Cycle {cycle}",
                f"Start a more complex project with {_fmt(skill_a)} at its core.{build_on} Aim for a cleaner architecture, a CI config, and meaningful tests from day one.",
                f"New project with {_fmt(skill_a)}, README, CI config, and at least one passing test",
                skill_a,
            )
        elif cycle_pos == 2:
            complexity = "basic" if cycle == 1 else "production-grade"
            return (
                "feature_a",
                f"Build a {complexity} {_fmt(skill_a)} feature",
                f"Implement a {complexity} feature using {_fmt(skill_a)}. Write {'basic' if cycle == 1 else 'comprehensive'} tests and commit incrementally.{build_on}",
                f"{_fmt(skill_a)} feature committed with {'basic' if cycle == 1 else 'comprehensive'} tests",
                skill_a,
            )
        elif cycle_pos == 3:
            if cycle == 1:
                return (
                    "feature_b",
                    f"Learn {_fmt(skill_b)} fundamentals",
                    f"Study the core concepts of {_fmt(skill_b)} and build a minimal working example. Follow official docs or a focused tutorial — no production wiring yet.",
                    f"A basic {_fmt(skill_b)} example working locally with notes on what you learned",
                    skill_b,
                )
            return (
                "feature_b",
                f"Integrate {_fmt(skill_b)} with full error handling",
                f"Wire {_fmt(skill_b)} into your existing project. Handle all failure modes, add retry logic, and document the API surface.{build_on}",
                f"{_fmt(skill_b)} integrated with error handling and retry logic",
                skill_b,
            )
        elif cycle_pos == 4:
            if cycle == 1:
                return (
                    "quality",
                    f"Add tests for your {_fmt(skill_a)} feature",
                    f"Write unit tests for your {_fmt(skill_a)} implementation, handle edge cases, and add inline documentation for public functions.",
                    f"Tests written for {_fmt(skill_a)} feature, edge cases covered, public functions documented",
                    skill_a,
                )
            return (
                "quality",
                f"Performance profiling and hardening ({_fmt(skill_a)})",
                f"Profile your {_fmt(skill_a)} code for bottlenecks. Optimise the top two issues and add load or stress tests that cover edge cases.{build_on}",
                "Profiling report, two optimisations applied, stress tests added",
                skill_a,
            )
        elif cycle_pos == 5:
            if cycle == 1:
                return (
                    "deploy",
                    f"Deploy your {_fmt(skill_c)} project",
                    f"Deploy the {_fmt(skill_c)} project to a live environment. Set up a basic CI/CD or automated test pipeline.",
                    "Live deployment with automation pipeline",
                    skill_c,
                )
            return (
                "deploy",
                f"Deploy with monitoring and {_fmt(skill_c)} observability",
                f"Re-deploy with structured logging, error alerting, and a basic {_fmt(skill_c)} health dashboard.{build_on} Simulate a failure and verify the alert fires.",
                "Live deployment with logging, alerting, and a health dashboard",
                skill_c,
            )
        else:  # cycle_pos == 0 (weeks 6, 12, 18...)
            return (
                "advanced",
                f"Build a{'  complex' if cycle > 1 else ' working'} {_fmt(skill_c)} feature",
                f"Implement a {'complex' if cycle > 1 else 'working'} {_fmt(skill_c)} feature that demonstrates understanding. Include error handling{', performance considerations,' if cycle > 1 else ''} and edge case coverage.{build_on}",
                f"{_fmt(skill_c)} feature with error handling{', optimised paths,' if cycle > 1 else ''} and edge cases",
                skill_c,
            )

    def generate_next_week_tasks(self, current_week: int,
                                path: any,
                                recent_reports: List[WeeklyReport],
                                target_role: str = "",
                                cycle: int = 1) -> List[Task]:
        """Generate next week's 3 tasks. Uses Claude for normal weeks; hardcoded
        corrective tasks for stagnation/black-hole; template fallback if Claude fails."""
        next_week = current_week + 1
        stagnation = self.detect_stagnation(recent_reports)

        role_req = get_role_requirements(target_role) if target_role else None
        role_skills = []
        if role_req:
            role_skills = (role_req.required_skills or []) + (role_req.preferred_skills or [])
        if not role_skills:
            role_skills = ["core_skill", "system_design", "problem_solving"]

        current_apps = _get_market_signals(recent_reports[-1]).get("applications_sent", 0) if recent_reports else 0
        current_responses = _get_market_signals(recent_reports[-1]).get("responses_received", 0) if recent_reports else 0
        current_interviews = _get_market_signals(recent_reports[-1]).get("interviews_attended", 0) if recent_reports else 0

        # --- Corrective interventions: hardcoded, not Claude-generated ---
        if stagnation and "STAGNATION" in stagnation:
            return [
                Task(
                    task_id=f"w{next_week}_project",
                    task_type=TaskType.PROJECT,
                    description=f"Ship one {_fmt(role_skills[0])} feature. No tutorials — build and commit working code to GitHub.",
                    target_skill=role_skills[0],
                    expected_outcome="Working feature committed to GitHub with README update",
                    week=next_week
                ),
                Task(
                    task_id=f"w{next_week}_apply",
                    task_type=TaskType.APPLICATION,
                    description=f"Apply to 3 {_fmt(target_role)} roles. Reference your project in each application.",
                    target_skill="job_application",
                    expected_outcome="3 applications sent with project links",
                    week=next_week
                ),
                Task(
                    task_id=f"w{next_week}_review",
                    task_type=TaskType.NETWORKING,
                    description="Request a code review from one industry professional. Document actionable feedback and implement at least one suggestion.",
                    target_skill="feedback_loop",
                    expected_outcome="Actionable feedback received, documented, and at least one item implemented",
                    week=next_week
                ),
            ]

        if stagnation and "BLACK HOLE" in stagnation:
            return [
                Task(
                    task_id=f"w{next_week}_fix_project",
                    task_type=TaskType.PROJECT,
                    description=f"Fix the top 3 quality issues in your {_fmt(target_role)} portfolio repository: README, tests, and error handling.",
                    target_skill="code_quality",
                    expected_outcome="README complete, basic tests added, error handling improved",
                    week=next_week
                ),
                Task(
                    task_id=f"w{next_week}_resume",
                    task_type=TaskType.PROJECT,
                    description=f"Tailor your resume to 5 real {_fmt(target_role)} job descriptions. Match keywords exactly.",
                    target_skill="resume_writing",
                    expected_outcome="Resume updated with JD-matched keywords for 5 roles",
                    week=next_week
                ),
                Task(
                    task_id=f"w{next_week}_mock",
                    task_type=TaskType.INTERVIEW_PREP,
                    description=f"Complete one mock {_fmt(target_role)} interview and record it. Review the recording to identify your top 2 weaknesses.",
                    target_skill="interview_skills",
                    expected_outcome="Recording reviewed, top 2 weaknesses identified with an improvement plan",
                    week=next_week
                ),
            ]

        # --- Normal weeks: Claude-generated with silent fallback ---
        try:
            return self._generate_tasks_with_claude(
                next_week, cycle, target_role, role_skills, recent_reports
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Claude task generation failed (week={next_week}, cycle={cycle}): {e}. Using fallback."
            )
            return self._generate_fallback_tasks(
                next_week, cycle, role_skills, target_role,
                current_apps, current_responses, current_interviews
            )

    def _generate_tasks_with_claude(
        self,
        next_week: int,
        cycle: int,
        target_role: str,
        role_skills: List[str],
        recent_reports: list,
    ) -> List[Task]:
        """Call Claude to generate 3 role-specific, week/cycle-aware tasks. Raises on any failure."""
        import os
        import json as _json
        import re as _re
        import anthropic as _anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        # Build checkin history string (last 4 weeks)
        history_lines = []
        for r in recent_reports[-4:]:
            th = _get_task_inputs(r)
            ms = _get_market_signals(r)
            week_num = r.get("week", "?") if isinstance(r, dict) else getattr(r, "week", "?")
            pt = (r.get("progress_type", "motion") if isinstance(r, dict) else getattr(r, "progress_type", "motion"))
            history_lines.append(
                f"Week {week_num}: learning={th.get('learning', 0)}h, "
                f"project_tasks={th.get('project', 0)}, "
                f"practice={th.get('practice', 0)}h, "
                f"applications={ms.get('applications_sent', 0)}, "
                f"responses={ms.get('responses_received', 0)}, "
                f"interviews={ms.get('interviews_attended', 0)} "
                f"→ {pt.replace('_', ' ').title()}"
            )
        history = "\n".join(history_lines) if history_lines else "No previous check-ins yet."

        cycle_context = (
            "Cycle 1 (foundational): focus on learning the basics and building working features. "
            "Keep scope small. Applying is encouraged but volume matters less than quality of output."
            if cycle == 1 else
            f"Cycle {cycle} (production-grade): user has completed {cycle - 1} full 12-week cycle(s). "
            "Raise the bar — production code quality, error handling, observability, higher application volume."
        )

        week_phase = (
            "early weeks (1–3): project setup, first features, learning fundamentals"
            if next_week <= 3 else
            "mid weeks (4–8): integration, testing, documentation, consistent applying"
            if next_week <= 8 else
            "late weeks (9–12): deployment, polishing, interview prep, increasing application volume"
        )

        role_display = _fmt(target_role)
        skills_display = ", ".join(_fmt(s) for s in role_skills[:8])

        prompt = f"""You are a career advisor generating weekly tasks for a job seeker targeting a {role_display} role.

Week: {next_week} | Cycle: {cycle} | Phase: {week_phase}
Required skills for {role_display}: {skills_display}
{cycle_context}

Their check-in history:
{history}

Generate exactly 3 tasks for Week {next_week}. Rules:
- Task 1: A project/build task tied to a specific skill from the {role_display} skill list above. Must be hands-on, not a tutorial.
- Task 2: A market signal task (applying, interview prep, or profile fix) — base it on their actual application history above.
- Task 3: A learning or practice task that targets a gap visible in their history.
- Every task must name the role ({role_display}) or a specific skill from the list — no generic advice.
- Tasks must be different from each other and appropriate for Week {next_week} of Cycle {cycle}.

Return ONLY a valid JSON array, no explanation, no markdown:
[
  {{"number": 1, "title": "...", "description": "...", "expected": "..."}},
  {{"number": 2, "title": "...", "description": "...", "expected": "..."}},
  {{"number": 3, "title": "...", "description": "...", "expected": "..."}}
]
title: ≤10 words. description: 1–2 sentences. expected: one concrete deliverable."""

        client = _anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        raw = _re.sub(r"^```[a-z]*\n?", "", raw, flags=_re.MULTILINE)
        raw = _re.sub(r"\n?```$", "", raw, flags=_re.MULTILINE)
        # Extract the JSON array
        match = _re.search(r"\[.*\]", raw, _re.DOTALL)
        if not match:
            raise ValueError(f"No JSON array found in Claude response: {raw[:200]}")

        data = _json.loads(match.group())
        if len(data) != 3:
            raise ValueError(f"Expected 3 tasks, got {len(data)}")

        task_types = [TaskType.PROJECT, TaskType.APPLICATION, TaskType.LEARNING]
        tasks = []
        for i, item in enumerate(data[:3]):
            tasks.append(Task(
                task_id=f"w{next_week}_ai_{item['number']}",
                task_type=task_types[i],
                description=item["description"],
                target_skill=role_skills[i] if i < len(role_skills) else "core_skill",
                expected_outcome=item["expected"],
                week=next_week,
            ))
        return tasks

    def _generate_fallback_tasks(
        self,
        next_week: int,
        cycle: int,
        role_skills: List[str],
        target_role: str,
        current_apps: int,
        current_responses: int,
        current_interviews: int,
    ) -> List[Task]:
        """Role-specific, week/cycle-aware fallback tasks when Claude is unavailable."""
        role_display = _fmt(target_role)
        skill_a = role_skills[0] if role_skills else "core skill"
        skill_b = role_skills[1] if len(role_skills) > 1 else skill_a
        skill_c = role_skills[2] if len(role_skills) > 2 else skill_b
        complexity = "production-grade" if cycle > 1 else "working"
        build_note = f" Apply patterns from Cycle {cycle - 1} — raise the bar on code quality." if cycle > 1 else ""

        # Task 1: role-skill-specific project task from week theme
        theme_id, _, description, expected, target_skill = self._get_week_theme(next_week, role_skills, cycle=cycle)
        task1 = Task(
            task_id=f"w{next_week}_{theme_id}",
            task_type=TaskType.PROJECT,
            description=description,
            target_skill=target_skill,
            expected_outcome=expected,
            week=next_week,
        )

        # Task 2: role-specific market signal task
        if current_interviews > 0:
            task2 = Task(
                task_id=f"w{next_week}_interview",
                task_type=TaskType.INTERVIEW_PREP,
                description=f"Practice {_fmt(skill_a)} interview questions for {role_display} roles. Focus on areas where you felt least confident.",
                target_skill="interview_skills",
                expected_outcome="5 questions answered with timed responses documented",
                week=next_week,
            )
        elif current_apps >= 10 and current_responses == 0:
            task2 = Task(
                task_id=f"w{next_week}_profile",
                task_type=TaskType.PROJECT,
                description=f"Audit your {role_display} resume and GitHub. Have two professionals review it and implement the top feedback.",
                target_skill="profile_optimization",
                expected_outcome="Top 5 resume and GitHub improvements implemented",
                week=next_week,
            )
        elif current_apps == 0:
            task2 = Task(
                task_id=f"w{next_week}_apply",
                task_type=TaskType.APPLICATION,
                description=f"Apply to 5 {role_display} positions on LinkedIn and Naukri. Reference your {_fmt(skill_b)} project in each application.",
                target_skill="job_application",
                expected_outcome=f"5 {role_display} applications sent with project links",
                week=next_week,
            )
        else:
            task2 = Task(
                task_id=f"w{next_week}_apply",
                task_type=TaskType.APPLICATION,
                description=f"Apply to 3–5 {role_display} roles with personalized cover notes highlighting your {_fmt(skill_b)} experience.",
                target_skill="job_application",
                expected_outcome="Applications sent with role-specific cover notes",
                week=next_week,
            )

        # Task 3: role-specific learning task
        practice_depth = "advanced" if cycle > 1 else "foundational"
        task3 = Task(
            task_id=f"w{next_week}_learn",
            task_type=TaskType.LEARNING,
            description=f"Study {_fmt(skill_c)} {practice_depth} concepts for 2 hours using official documentation. Build one practical {role_display} example immediately after.{build_note}",
            target_skill=skill_c,
            expected_outcome=f"Notes on {_fmt(skill_c)} {practice_depth} concepts, one working example committed",
            week=next_week,
        )

        return [task1, task2, task3]
