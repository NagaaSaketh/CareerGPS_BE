"""
CareerGPS Main Orchestrator - DYNAMIC VERSION
Coordinates all agents for ANY user-specified career path.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from data.market_data import (
    CollegeTier, get_role_requirements, is_role_supported,
    normalize_role_name, suggest_similar_roles, get_all_roles,
    get_roles_by_category
)
from agents.skill_assessor import SkillAssessor, SkillEvidence
from agents.path_planner import MarketMapper, CareerPath, PathType
from agents.progress_tracker import ProgressTracker, Task, TaskType, WeeklyReport
from agents.output_synthesizer import OutputSynthesizer

class CareerGPS:
    """
    Main CareerGPS system - DYNAMIC.
    Works with ANY career path the user specifies.
    Stateless: all data is passed in and returned; no singleton session storage.
    """

    def __init__(self):
        self.assessor = SkillAssessor()
        self.mapper = MarketMapper()
        self.tracker = ProgressTracker()
        self.synthesizer = OutputSynthesizer()

    def process_profile(self, profile: dict) -> dict:
        """
        Main entry point - works with ANY target role.
        Returns a dict with all computed data for persistence.
        """
        # Step 1: Validate inputs
        validation = self._validate_input(profile)
        if not validation["valid"]:
            return {
                "valid": False,
                "report_text": self._format_validation_error(validation["errors"]),
                "profile": profile,
                "assessment": {},
                "gap": None,
                "paths": [],
                "target_role": profile.get("target_role", ""),
                "initial_tasks": [],
                "uncertainty_flags": [],
            }

        # Step 2: Check if role is supported
        target_role_str = profile.get("target_role", "")
        normalized_role = normalize_role_name(target_role_str)

        is_known = is_role_supported(target_role_str)
        similar_roles = []
        if not is_known:
            similar_roles = suggest_similar_roles(target_role_str)

        # Step 3: Evidence-based assessment
        assessment = self.assessor.generate_full_assessment(profile)

        # Step 4: Market mapping for ANY role
        current_skills = {k: v.final_rating for k, v in assessment["skills"].items()}
        target_role = normalized_role

        college_tier_str = profile.get("college_tier", "tier_3")
        college_tier = self._parse_college_tier(college_tier_str)

        current_experience = profile.get("experience_months", 0)
        current_state = profile.get("current_state", "unknown")
        location = profile.get("location", "pune")

        gap = self.mapper.analyze_gap(
            current_skills, current_experience, target_role, college_tier
        )

        # Step 5: Path planning for ANY role
        paths = self.mapper.generate_paths(
            current_skills, current_experience, target_role,
            college_tier, current_state, location
        )

        # Step 6: Generate initial weekly tasks (role-specific)
        initial_tasks = self._generate_initial_tasks(paths[0] if paths else None, assessment, target_role)

        # Step 7: Synthesize output
        uncertainty_flags = self._detect_uncertainty(assessment, profile, is_known, similar_roles)

        output = self.synthesizer.synthesize(
            assessment=assessment,
            gap_analysis=gap,
            paths=paths,
            current_week=0,
            weekly_tasks=initial_tasks,
            uncertainty_flags=uncertainty_flags
        )

        return {
            "valid": True,
            "report_text": output,
            "profile": profile,
            "assessment": assessment,
            "gap": gap,
            "paths": paths,
            "target_role": target_role,
            "initial_tasks": initial_tasks,
            "uncertainty_flags": uncertainty_flags,
        }

    def weekly_checkin(self,
                       week: int,
                       tasks_completed: List[str],
                       applications_sent: int = 0,
                       responses_received: int = 0,
                       interviews_attended: int = 0,
                       previous_state: dict = None,
                       task_inputs: dict = None) -> dict:
        """
        Process weekly check-in.
        Accepts previous state (paths, target_role, weekly_reports) and returns check-in data.
        task_inputs: {learning: hours, practice: hours, project: qty, application: qty}
        """
        previous_state = previous_state or {}
        paths = previous_state.get("paths", [])
        target_role = previous_state.get("target_role", "")
        weekly_reports = previous_state.get("weekly_reports", [])
        initial_tasks = previous_state.get("initial_tasks", [])
        task_inputs = task_inputs or {}

        # Rebuild tracker state from previous data
        tracker = ProgressTracker()
        # Register initial tasks so record_completion can find them
        if week == 1 and initial_tasks:
            tracker.add_weekly_plan(1, initial_tasks)
        # Register previous weeks' tasks if available
        for report in weekly_reports:
            if hasattr(report, "week"):
                tracker.add_weekly_plan(report.week, report.tasks_completed + report.tasks_missed)

        # Record completions
        for task_id in tasks_completed:
            tracker.record_completion(task_id)

        # Analyze week with quantitative inputs and trend context
        report = tracker.analyze_week(
            week=week,
            applications_sent=applications_sent,
            responses_received=responses_received,
            interviews_attended=interviews_attended,
            task_inputs=task_inputs,
            recent_reports=weekly_reports
        )

        # Generate next week's tasks (role-specific + input-adaptive)
        current_path = paths[0] if paths else None
        next_tasks = tracker.generate_next_week_tasks(
            week, current_path, weekly_reports + [report], target_role
        )

        # Synthesize check-in report
        checkin = self.synthesizer.generate_weekly_checkin(
            week=week,
            report=report,
            next_tasks=next_tasks
        )

        return {
            "checkin_text": checkin,
            "report": report,
            "next_tasks": next_tasks,
            "progress_type": report.progress_type.value if hasattr(report.progress_type, "value") else str(report.progress_type),
            "recommendation": report.recommendation,
            "red_flags": report.red_flags,
        }

    def _validate_input(self, profile: dict) -> dict:
        """Validate user input against guardrails."""
        errors = []

        # Check vague goals
        target = profile.get("target_role", "").lower().strip()
        if not target or target in ["get a job", "software job", "tech job", "job", "work"]:
            errors.append("Goal is too vague. Please specify exact role (e.g., 'backend engineer', 'data scientist', 'ux designer')")

        # Check minimum input
        has_github = bool(profile.get("github", {}).get("url"))
        has_resume = bool(profile.get("resume"))
        has_projects = bool(profile.get("resume", {}).get("projects"))

        if not (has_github or has_resume or has_projects):
            errors.append("Need at least one of: GitHub URL, resume, or project descriptions")

        # Check for fake GitHub
        github = profile.get("github", {})
        if github.get("url") and not github.get("accessible", True):
            errors.append("GitHub repository not accessible. Please verify URL or make public.")

        # Check unrealistic goals for known roles
        college_tier = profile.get("college_tier", "tier_3")
        experience = profile.get("experience_months", 0)

        # Only flag if role is known and clearly unrealistic
        known_unrealistic = [
            "sde at google", "google", "microsoft", "amazon", "meta", "facebook",
            "netflix", "apple", "sde 2", "senior engineer"
        ]
        if any(ur in target for ur in known_unrealistic) and college_tier == "tier_3" and experience < 24:
            errors.append(f"Target '{target}' at FAANG with tier-3 college and {experience} months is unrealistic. Consider intermediate steps or different target companies.")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _format_validation_error(self, errors: List[str]) -> str:
        """Format validation errors for user."""
        output = []
        output.append("❌ INPUT VALIDATION FAILED")
        output.append("=" * 50)
        output.append("")
        output.append("Before CareerGPS can help, please fix these issues:")
        output.append("")
        for i, error in enumerate(errors, 1):
            output.append(f"  {i}. {error}")
        output.append("")
        output.append("CareerGPS works with ANY career path, but needs specific information.")
        output.append("Examples of valid goals:")
        output.append("  • Backend Engineer")
        output.append("  • Data Scientist")
        output.append("  • UX Designer")
        output.append("  • Product Manager")
        output.append("  • DevOps Engineer")
        output.append("  • QA Automation")
        output.append("  • Technical Writer")
        output.append("  • Solutions Engineer")
        return "\n".join(output)

    def _parse_college_tier(self, tier_str: str) -> CollegeTier:
        """Parse string to CollegeTier."""
        mapping = {
            "tier_1": CollegeTier.TIER_1,
            "tier1": CollegeTier.TIER_1,
            "tier_2": CollegeTier.TIER_2,
            "tier2": CollegeTier.TIER_2,
            "tier_3": CollegeTier.TIER_3,
            "tier3": CollegeTier.TIER_3,
        }
        return mapping.get(tier_str.lower(), CollegeTier.TIER_3)

    def _generate_initial_tasks(self, path: Optional[CareerPath], assessment: dict, target_role: str) -> List[Task]:
        """Generate first week's 3 tasks - ROLE SPECIFIC."""
        tasks = []

        req = get_role_requirements(target_role)
        role_display = req.role_name.replace("_", " ").title() if req else target_role.replace("_", " ").title()

        if not path:
            return [
                Task("w1_diagnostic", TaskType.PRACTICE, f"Complete skill diagnostic for {role_display}", "assessment", "Diagnostic score", 1),
                Task("w1_portfolio", TaskType.PROJECT, f"Set up portfolio for {role_display}", "portfolio", "Public portfolio/GitHub", 1),
                Task("w1_research", TaskType.LEARNING, f"Research 5 real JDs for {role_display}", "market_research", "JD analysis notes", 1),
            ]

        focus_skills = path.steps[0].get("focus_skills", ["core_skill"]) if path.steps else ["core_skill"]

        # Role-specific first tasks
        if req:
            if req.role_category == "design":
                tasks.append(Task(
                    f"w1_{focus_skills[0]}",
                    TaskType.PROJECT,
                    f"Create 1 design case study for {role_display} portfolio",
                    focus_skills[0],
                    "Case study with process documentation",
                    1
                ))
            elif req.role_category == "data":
                tasks.append(Task(
                    f"w1_{focus_skills[0]}",
                    TaskType.PROJECT,
                    f"Complete 1 data project with visualization for {role_display}",
                    focus_skills[0],
                    "Notebook + dashboard + GitHub",
                    1
                ))
            elif req.role_category in ["devrel", "business"]:
                tasks.append(Task(
                    f"w1_{focus_skills[0]}",
                    TaskType.PROJECT,
                    f"Write 1 technical article / business analysis for {role_display}",
                    focus_skills[0],
                    "Published article / analysis document",
                    1
                ))
            else:
                # Default for engineering/QA/support
                tasks.append(Task(
                    f"w1_{focus_skills[0]}",
                    TaskType.PROJECT,
                    f"Build a small project using {focus_skills[0]} for {role_display} - deploy it",
                    focus_skills[0],
                    "Live project URL + GitHub repo",
                    1
                ))
        else:
            tasks.append(Task(
                f"w1_build",
                TaskType.PROJECT,
                f"Build portfolio piece for {role_display}",
                "portfolio",
                "Portfolio piece completed",
                1
            ))

        tasks.append(Task(
            "w1_gap_assess",
            TaskType.PRACTICE,
            f"Complete diagnostic for: {', '.join(focus_skills[1:3]) if len(focus_skills) > 1 else 'core skills'}",
            "diagnostic",
            "Score report with gaps identified",
            1
        ))

        tasks.append(Task(
            "w1_apply",
            TaskType.APPLICATION,
            f"Apply to 3 {role_display} roles (even if not ready) - get real feedback",
            "job_application",
            "3 applications with portfolio links",
            1
        ))

        return tasks

    def _detect_uncertainty(self, assessment: dict, profile: dict, is_role_known: bool, similar_roles: List[str]) -> List[str]:
        """Detect areas where system has low confidence."""
        flags = []

        if not is_role_known:
            flags.append(f"Role '{profile.get('target_role')}' not in database. Using closest match: {similar_roles[0] if similar_roles else 'unknown'}")

        trust_score = assessment.get("overall_trust_score", 0)
        if trust_score < 0.3:
            flags.append("Low evidence trust score. Recommendations based on limited verifiable data.")

        github = assessment.get("github_analysis")
        if github and not github.accessible:
            flags.append("GitHub not accessible. Skill assessment may be inaccurate.")

        if profile.get("experience_months", 0) == 0 and not profile.get("internship"):
            flags.append("No work experience detected. Timeline estimates have higher variance.")

        return flags


# Convenience function for direct usage
def run_careergps(profile: dict) -> str:
    """Quick start function."""
    gps = CareerGPS()
    result = gps.process_profile(profile)
    return result["report_text"]
