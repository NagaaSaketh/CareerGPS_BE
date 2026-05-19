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

    def _get_week_theme(self, week: int, role_skills: List[str]) -> tuple:
        """
        Determine the theme for a given week using a 6-week cycle.
        Returns (theme_id, title, description, expected_outcome, target_skill).
        Skills rotate across cycles so users don't see the same tasks repeatedly.
        """
        n_skills = len(role_skills)
        cycle_index = week // 6  # which 6-week block we're in

        # Rotate skills across cycles so each 6-week block uses different skills
        skill_a = role_skills[(cycle_index * 3 + 0) % n_skills] if n_skills else "core"
        skill_b = role_skills[(cycle_index * 3 + 1) % n_skills] if n_skills else "secondary"
        skill_c = role_skills[(cycle_index * 3 + 2) % n_skills] if n_skills else "advanced"

        cycle_pos = week % 6

        if cycle_pos == 1:
            if week == 1:
                return (
                    "setup",
                    "Set up your project foundation",
                    "Initialize a repository, configure dependencies, and create the project structure. Focus on a clean scaffold with README and setup instructions.",
                    "Working repo with README and setup instructions",
                    skill_a,
                )
            else:
                return (
                    "setup",
                    "Set up a new project or major refactor",
                    "Start a new project or refactor the existing codebase. Apply learnings from the previous cycle to improve architecture and organization.",
                    "New repo or refactored codebase with clear structure",
                    skill_a,
                )
        elif cycle_pos == 2:
            return (
                "feature_a",
                f"Build a core {_fmt(skill_a)} feature",
                f"Implement a functional feature using {_fmt(skill_a)}. Write basic tests and commit incrementally.",
                f"{_fmt(skill_a)} feature committed with basic tests",
                skill_a,
            )
        elif cycle_pos == 3:
            return (
                "feature_b",
                f"Integrate {_fmt(skill_b)}",
                f"Add a second core capability using {_fmt(skill_b)}. Ensure it connects cleanly with existing features.",
                f"{_fmt(skill_b)} integration working with existing features",
                skill_b,
            )
        elif cycle_pos == 4:
            return (
                "quality",
                "Add tests and documentation",
                "Write tests for recent features, handle edge cases, and document APIs or usage patterns.",
                "Tests written, docs added, edge cases handled",
                skill_a,
            )
        elif cycle_pos == 5:
            return (
                "deploy",
                "Deploy and automate",
                "Deploy the project to a live environment. Set up CI/CD or automated testing pipelines.",
                "Live deployment with automation pipeline",
                skill_c,
            )
        else:  # cycle_pos == 0 (weeks 6, 12, 18...)
            return (
                "advanced",
                f"Build an advanced {_fmt(skill_c)} feature",
                f"Implement a complex {_fmt(skill_c)} feature that demonstrates depth. Include error handling and edge case coverage.",
                f"Advanced {_fmt(skill_c)} feature with error handling and edge cases",
                skill_c,
            )

    def generate_next_week_tasks(self, current_week: int,
                                path: any,
                                recent_reports: List[WeeklyReport],
                                target_role: str = "") -> List[Task]:
        """Generate next week's 3 tasks using a 6-week theme cycle + adaptive tasks 2 & 3."""
        next_week = current_week + 1
        tasks = []
        stagnation = self.detect_stagnation(recent_reports)

        role_req = get_role_requirements(target_role) if target_role else None
        role_skills = []
        if role_req:
            role_skills = (role_req.required_skills or []) + (role_req.preferred_skills or [])
        if not role_skills:
            role_skills = ["core_skill", "system_design", "problem_solving"]

        current = _get_task_inputs(recent_reports[-1]) if recent_reports else {}
        current_apps = _get_market_signals(recent_reports[-1]).get("applications_sent", 0) if recent_reports else 0
        current_responses = _get_market_signals(recent_reports[-1]).get("responses_received", 0) if recent_reports else 0
        current_interviews = _get_market_signals(recent_reports[-1]).get("interviews_attended", 0) if recent_reports else 0

        if stagnation and "STAGNATION" in stagnation:
            # Force corrective: must ship something tangible
            tasks.append(Task(
                task_id=f"w{next_week}_project",
                task_type=TaskType.PROJECT,
                description=f"Ship one {_fmt(role_skills[0])} feature. No tutorials — build and commit working code.",
                target_skill=role_skills[0],
                expected_outcome="Code committed to GitHub with README update",
                week=next_week
            ))
            tasks.append(Task(
                task_id=f"w{next_week}_apply",
                task_type=TaskType.APPLICATION,
                description="Apply to 3 roles. Reference your project in each application.",
                target_skill="job_application",
                expected_outcome="3 applications sent with project links",
                week=next_week
            ))
            tasks.append(Task(
                task_id=f"w{next_week}_review",
                task_type=TaskType.NETWORKING,
                description="Request a code review from one industry professional. Document actionable feedback.",
                target_skill="feedback_loop",
                expected_outcome="Actionable feedback received and documented",
                week=next_week
            ))

        elif stagnation and "BLACK HOLE" in stagnation:
            tasks.append(Task(
                task_id=f"w{next_week}_fix_project",
                task_type=TaskType.PROJECT,
                description="Fix the top 3 issues in your repository. Focus on README, tests, and error handling.",
                target_skill="code_quality",
                expected_outcome="README, tests, and error handling added",
                week=next_week
            ))
            tasks.append(Task(
                task_id=f"w{next_week}_resume",
                task_type=TaskType.PROJECT,
                description=f"Tailor your resume to 5 job descriptions for {_fmt(target_role)} roles.",
                target_skill="resume_writing",
                expected_outcome="Resume updated with JD-matched keywords",
                week=next_week
            ))
            tasks.append(Task(
                task_id=f"w{next_week}_mock",
                task_type=TaskType.INTERVIEW_PREP,
                description="Complete one mock interview and record it. Review to identify two improvement areas.",
                target_skill="interview_skills",
                expected_outcome="Recording reviewed, top 2 weaknesses identified",
                week=next_week
            ))

        else:
            # Task 1: Week-themed project task (rotating skills + progressive project)
            theme_id, title, description, expected, target_skill = self._get_week_theme(next_week, role_skills)
            tasks.append(Task(
                task_id=f"w{next_week}_{theme_id}",
                task_type=TaskType.PROJECT,
                description=description,
                target_skill=target_skill,
                expected_outcome=expected,
                week=next_week
            ))

            # Task 2: Adaptive application / interview / profile fix
            if current_interviews > 0:
                tasks.append(Task(
                    task_id=f"w{next_week}_interview",
                    task_type=TaskType.INTERVIEW_PREP,
                    description=f"Practice {_fmt(role_skills[0]) if role_skills else 'technical'} interview questions. Focus on areas where you struggled in recent rounds.",
                    target_skill="interview_skills",
                    expected_outcome="5 questions practiced with timed responses",
                    week=next_week
                ))
            elif current_apps >= 10 and current_responses == 0:
                tasks.append(Task(
                    task_id=f"w{next_week}_profile",
                    task_type=TaskType.PROJECT,
                    description="Have your resume and GitHub reviewed by two professionals. Implement the top feedback items.",
                    target_skill="profile_optimization",
                    expected_outcome="Top 5 improvements implemented",
                    week=next_week
                ))
            elif current_apps == 0:
                tasks.append(Task(
                    task_id=f"w{next_week}_apply",
                    task_type=TaskType.APPLICATION,
                    description="Apply to 5 roles with personalized notes that reference your project.",
                    target_skill="job_application",
                    expected_outcome="5 applications sent with project links",
                    week=next_week
                ))
            else:
                tasks.append(Task(
                    task_id=f"w{next_week}_apply",
                    task_type=TaskType.APPLICATION,
                    description="Apply to 3–5 roles with personalized cover notes.",
                    target_skill="job_application",
                    expected_outcome="Applications sent with project links",
                    week=next_week
                ))

            # Task 3: Adaptive practice / learning (fill the gap)
            if current.get("practice", 0) == 0:
                skill = role_skills[1] if len(role_skills) > 1 else "problem_solving"
                tasks.append(Task(
                    task_id=f"w{next_week}_practice",
                    task_type=TaskType.PRACTICE,
                    description=f"Solve 3 {_fmt(skill)} problems. Document your approach and optimize for efficiency.",
                    target_skill=skill,
                    expected_outcome="3 problems solved with optimal solutions",
                    week=next_week
                ))
            else:
                gap_skill = role_skills[2] if len(role_skills) > 2 else "fundamentals"
                tasks.append(Task(
                    task_id=f"w{next_week}_learn",
                    task_type=TaskType.LEARNING,
                    description=f"Study {_fmt(gap_skill)} for up to 2 hours. Apply the concept in a practical example immediately after.",
                    target_skill=gap_skill,
                    expected_outcome="Notes taken, one practical example built",
                    week=next_week
                ))

        return tasks[:3]
