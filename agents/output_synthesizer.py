"""
Output Synthesizer Module - DYNAMIC VERSION
Produces simple, honest, actionable output for ANY career path.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

from data.market_data import (
    get_role_requirements, get_callback_rate, get_salary_range,
    is_role_supported, suggest_similar_roles
)

class OutputSynthesizer:
    """
    Synthesizes all agent outputs into a clean, actionable format.
    Works with ANY target role.
    """

    def __init__(self):
        self.uncertainty_threshold = 0.6

    def synthesize(self, 
                   assessment: dict,
                   gap_analysis: any,
                   paths: List[any],
                   current_week: int = 0,
                   weekly_tasks: Optional[List] = None,
                   uncertainty_flags: Optional[List[str]] = None) -> str:
        """
        Main synthesis method for ANY role.
        """
        output = []

        target_role = gap_analysis.role if gap_analysis else "unknown"
        req = get_role_requirements(target_role)
        role_display = req.role_name.replace("_", " ").title() if req else target_role.replace("_", " ").title()

        # Header
        output.append("=" * 60)
        output.append(f"CAREERGPS - YOUR {role_display.upper()} NAVIGATION REPORT")
        output.append("=" * 60)
        output.append("")

        # Section 1: Where You Are (Honest Assessment)
        output.append("📍 WHERE YOU ARE")
        output.append("-" * 40)

        skills = assessment.get("skills", {})
        contradictions = assessment.get("contradictions", [])
        critical_gaps = assessment.get("critical_gaps", [])
        trust_score = assessment.get("overall_trust_score", 0.0)

        for skill_name, evidence in skills.items():
            self_rating = evidence.self_reported
            evidence_rating = evidence.evidence_based
            final = evidence.final_rating

            if evidence.contradiction_flag:
                output.append(f"  ⚠️  {skill_name.upper()}: You said {self_rating}/5, evidence shows {evidence_rating}/5")
                output.append(f"      → FINAL: {final}/5 (TRUST EVIDENCE, NOT SELF-ASSESSMENT)")
            else:
                output.append(f"  ✅ {skill_name.upper()}: {final}/5")

        if contradictions:
            output.append("")
            output.append("  🚨 SELF-ASSESSMENT GAPS DETECTED:")
            for c in contradictions:
                output.append(f"     • {c.skill_name}: Overrated by {c.self_reported - c.evidence_based} points")

        if critical_gaps:
            output.append("")
            output.append("  🔴 CRITICAL GAPS:")
            for gap in critical_gaps[:5]:
                output.append(f"     • {gap.replace('_', ' ').title()}")

        output.append("")

        # Section 2: Where You Can Go (Market Reality)
        output.append(f"🎯 WHERE YOU CAN GO: {role_display}")
        output.append("-" * 40)

        if not gap_analysis.is_role_known:
            output.append(f"  ⚠️  '{target_role}' is not in our role database.")
            similar = suggest_similar_roles(target_role)
            if similar:
                output.append(f"  Consider these similar roles instead:")
                for s in similar:
                    s_req = get_role_requirements(s)
                    if s_req:
                        output.append(f"     • {s.replace('_', ' ').title()} ({s_req.role_category})")
            output.append("")

        if paths:
            best_path = paths[0]

            output.append(f"  RECOMMENDED PATH: {best_path.path_type.value.upper()}")
            output.append(f"  Success Probability: {best_path.success_probability:.0%}")
            output.append(f"  Timeline: {best_path.total_duration_months} months")
            output.append("")
            output.append(f"  💡 WHY: {best_path.reasoning}")
            output.append("")

            if best_path.salary_trajectory:
                output.append("  💰 SALARY TRAJECTORY:")
                for role, salary in best_path.salary_trajectory:
                    output.append(f"     • {role.replace('_', ' ').title()}: ₹{salary} LPA")

            output.append("")

            if best_path.risks:
                output.append("  ⚡ RISKS TO WATCH:")
                for risk in best_path.risks[:3]:
                    output.append(f"     • {risk}")

            if len(paths) > 1:
                output.append("")
                output.append("  🔄 ALTERNATIVE PATHS:")
                for i, path in enumerate(paths[1:], 1):
                    output.append(f"     {i}. {path.path_type.value.title()}: {path.total_duration_months} months, {path.success_probability:.0%} success")
                    if path.reasoning:
                        output.append(f"        ({path.reasoning[:80]}...)")

        output.append("")

        # Section 3: What To Do This Week (3 Tasks)
        output.append("📋 YOUR 3 TASKS THIS WEEK")
        output.append("-" * 40)

        if weekly_tasks:
            for i, task in enumerate(weekly_tasks, 1):
                output.append(f"  {i}. {task.description}")
                output.append(f"     → Expected: {task.expected_outcome}")
                output.append("")
        else:
            output.append("  1. Complete skill diagnostic assessment")
            output.append("  2. Set up portfolio/GitHub with first project")
            output.append("  3. Research 5 real job descriptions for your target role")

        # Uncertainty flags
        if uncertainty_flags:
            output.append("")
            output.append("⚠️  UNCERTAINTY NOTICE")
            output.append("-" * 40)
            output.append("The system has limited confidence in the following:")
            for flag in uncertainty_flags:
                output.append(f"  • {flag}")
            output.append("Recommendations may change as more data becomes available.")

        # Footer
        output.append("")
        output.append("=" * 60)
        output.append("CareerGPS | Evidence-Based Career Navigation")
        output.append("Supports 25+ roles across Engineering, Data, Design, Product, DevRel, Business")
        output.append("Data sourced from real 2026 job market | No fabricated claims")
        output.append("=" * 60)

        return "\n".join(output)

    def generate_weekly_checkin(self, 
                                week: int,
                                report: any,
                                next_tasks: List) -> str:
        """
        Generate a weekly check-in report.
        """
        output = []

        output.append(f"📅 WEEK {week} CHECK-IN")
        output.append("-" * 40)
        output.append("")

        emoji = {
            "compliance": "⚠️",
            "motion": "🔄",
            "real_progress": "✅",
            "breakthrough": "🚀"
        }.get(report.progress_type.value, "➡️")

        output.append(f"{emoji} Progress Type: {report.progress_type.value.replace('_', ' ').title()}")
        output.append("")

        output.append(f"Tasks Completed: {len(report.tasks_completed)}")
        output.append(f"Tasks Missed: {len(report.tasks_missed)}")
        output.append("")

        if report.skills_gained:
            output.append("Skills Applied: " + ", ".join(report.skills_gained))
        if report.skills_stagnant:
            output.append("Skills Not Yet Applied: " + ", ".join(report.skills_stagnant))
        output.append("")

        ms = report.market_signals
        output.append("Market Signals:")
        output.append(f"  Applications: {ms['applications_sent']}")
        output.append(f"  Responses: {ms['responses_received']}")
        output.append(f"  Response Rate: {ms['response_rate']:.1%}")
        output.append("")

        if report.red_flags:
            output.append("🚨 Alerts:")
            for flag in report.red_flags:
                output.append(f"  • {flag}")
            output.append("")

        output.append("💡 SYSTEM RECOMMENDATION:")
        output.append(report.recommendation)
        output.append("")

        output.append("📋 NEXT WEEK'S 3 TASKS:")
        for i, task in enumerate(next_tasks, 1):
            output.append(f"  {i}. {task.description}")

        return "\n".join(output)

    def generate_honest_assessment_summary(self, assessment: dict, 
                                           target_role: str,
                                           college_tier: str) -> str:
        """
        Generate a one-screen honest summary for ANY role.
        """
        skills = assessment.get("skills", {})
        contradictions = assessment.get("contradictions", [])

        req = get_role_requirements(target_role)
        role_display = req.role_name.replace("_", " ").title() if req else target_role.replace("_", " ").title()

        output = []
        output.append(f"HONEST ASSESSMENT: {role_display}")
        output.append("=" * 50)
        output.append("")

        callback_rate = get_callback_rate(target_role, 
            __import__('data.market_data', fromlist=['CollegeTier']).CollegeTier(college_tier) if college_tier in ['tier_1', 'tier_2', 'tier_3'] else __import__('data.market_data', fromlist=['CollegeTier']).CollegeTier.TIER_3
        )

        output.append(f"Your current estimated callback rate for {role_display}: {callback_rate:.1%}")
        if callback_rate > 0:
            output.append(f"This means ~{int(1/callback_rate)} applications per interview callback")
        output.append("")

        output.append("SKILL REALITY CHECK:")
        for skill_name, evidence in skills.items():
            if evidence.contradiction_flag:
                output.append(f"  ❌ {skill_name}: Overrated. Actual: {evidence.evidence_based}/5")
            elif evidence.evidence_based < 2:
                output.append(f"  ⚠️  {skill_name}: Weak ({evidence.evidence_based}/5). Needs work.")
            else:
                output.append(f"  ✅ {skill_name}: Solid ({evidence.evidence_based}/5)")

        output.append("")
        output.append("This is not a judgment. This is data.")
        output.append("Every gap listed above is closable. The question is: are you willing to do the work?")

        return "\n".join(output)
