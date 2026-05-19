"""
Dynamic Market Mapper & Path Planner
Works with ANY user-specified role, not just backend.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from data.market_data import (
    RoleRequirements, CollegeTier,
    get_role_requirements, get_callback_rate, get_salary_range,
    estimate_timeline, COLLEGE_TIER_IMPACT,
    get_stepping_stone_suggestions, suggest_similar_roles,
    is_role_supported, normalize_role_name
)

class PathType(Enum):
    DIRECT = "direct"
    STEPPING_STONE = "stepping_stone"
    ALTERNATIVE = "alternative"
    UNREALISTIC = "unrealistic"
    UNKNOWN_ROLE = "unknown_role"

@dataclass
class GapAnalysis:
    """Gap between current profile and ANY role requirements"""
    role: str
    role_display: str
    missing_skills: List[str]
    skill_gaps: Dict[str, Tuple[int, int]]
    experience_gap_months: int
    framework_gaps: List[str]
    system_design_gap: str
    credential_penalty: float
    is_role_known: bool

@dataclass
class CareerPath:
    """A viable career path for ANY role"""
    path_type: PathType
    steps: List[Dict]
    total_duration_months: int
    success_probability: float
    salary_trajectory: List[Tuple[str, float]]
    reasoning: str
    risks: List[str]
    alternative_if_failed: Optional[str] = None

class MarketMapper:
    """
    Maps user assessment to market reality for ANY role.
    """

    def __init__(self):
        pass  # Uses dynamic database

    def analyze_gap(self, current_skills: Dict[str, int], 
                  current_experience_months: int,
                  target_role: str,
                  college_tier: CollegeTier) -> GapAnalysis:
        """
        Analyze gap for ANY role.
        """
        req = get_role_requirements(target_role)

        if not req:
            # Unknown role - return minimal gap analysis
            return GapAnalysis(
                role=target_role,
                role_display=target_role.replace("_", " ").title(),
                missing_skills=["unknown_role_requirements"],
                skill_gaps={},
                experience_gap_months=0,
                framework_gaps=[],
                system_design_gap="unknown",
                credential_penalty=0.0,
                is_role_known=False
            )

        # Skill gaps
        missing_skills = []
        skill_gaps = {}

        for skill in req.required_skills:
            current = current_skills.get(skill, 0)
            required = 3  # Intermediate level typically required
            if current < required:
                missing_skills.append(skill)
                skill_gaps[skill] = (current, required)

        # Framework gaps
        framework_gaps = []
        for fw in req.framework_tools:
            if fw not in current_skills or current_skills.get(fw, 0) < 2:
                framework_gaps.append(fw)

        # Experience gap
        exp_gap = max(0, req.min_experience_months - current_experience_months)

        # System design gap
        current_sd = current_skills.get("system_design", 0)
        sd_map = {"none": 0, "basic": 1, "intermediate": 2, "advanced": 3}
        required_sd = sd_map.get(req.system_design_level, 0)
        sd_gap = "none" if current_sd >= required_sd else req.system_design_level

        # Credential penalty
        callback_rate = get_callback_rate(target_role, college_tier)
        tier_1_rate = get_callback_rate(target_role, CollegeTier.TIER_1)
        credential_penalty = 1.0 - (callback_rate / tier_1_rate) if tier_1_rate > 0 else 0.5

        return GapAnalysis(
            role=target_role,
            role_display=req.role_name.replace("_", " ").title(),
            missing_skills=missing_skills,
            skill_gaps=skill_gaps,
            experience_gap_months=exp_gap,
            framework_gaps=framework_gaps,
            system_design_gap=sd_gap,
            credential_penalty=credential_penalty,
            is_role_known=True
        )

    def check_realism(self, gap: GapAnalysis, target_role: str,
                      college_tier: str, current_state: str) -> Tuple[bool, str]:
        """
        Check if target is realistic for ANY role.
        """
        if not gap.is_role_known:
            return False, f"Role '{target_role}' not in database. Suggesting similar roles."

        req = get_role_requirements(target_role)
        if not req:
            return False, "Role requirements unknown"

        # Check experience gap
        if gap.experience_gap_months > 24:
            return False, f"Requires {gap.experience_gap_months} months more experience"

        # Check critical skill gaps
        critical_missing = gap.missing_skills[:5]  # Top 5 gaps
        if len(critical_missing) > 3:
            return False, f"Missing {len(critical_missing)} core skills"

        # Check framework gaps for roles that need them
        if len(gap.framework_gaps) > 2 and req.hiring_difficulty in ["hard", "very_hard"]:
            return False, f"No relevant framework/tool experience"

        # Check timeline
        timeline = estimate_timeline(college_tier, current_state, target_role)
        if timeline > 18:
            return False, f"Estimated {timeline} months to readiness"

        return True, f"{gap.role_display} is achievable with focused effort"

    def generate_paths(self, current_skills: Dict[str, int],
                      current_experience_months: int,
                      target_role: str,
                      college_tier: CollegeTier,
                      current_state: str,
                      location: str = "pune") -> List[CareerPath]:
        """
        Generate viable career paths for ANY role.
        """
        paths = []
        gap = self.analyze_gap(current_skills, current_experience_months, 
                              target_role, college_tier)

        req = get_role_requirements(target_role)

        # Handle unknown role
        if not gap.is_role_known:
            similar = suggest_similar_roles(target_role)
            paths.append(CareerPath(
                path_type=PathType.UNKNOWN_ROLE,
                steps=[{
                    "role": similar[0] if similar else target_role,
                    "duration_months": 6,
                    "focus_skills": [],
                    "milestones": ["Explore similar roles"]
                }],
                total_duration_months=6,
                success_probability=0.30,
                salary_trajectory=[],
                reasoning=f"'{target_role}' is not in our database. Consider these similar roles: {', '.join(similar)}.",
                risks=["Limited data for this specific role"]
            ))
            return paths

        is_realistic, reason = self.check_realism(gap, target_role, 
                                                   college_tier.value, current_state)

        salary_range = get_salary_range(target_role, location, college_tier)

        # Direct path (if realistic)
        if is_realistic:
            direct_timeline = estimate_timeline(
                college_tier.value, current_state, target_role
            )
            if direct_timeline < 0:
                direct_timeline = max(6, req.min_experience_months // 2)

            # Build milestones based on role-specific gaps
            milestones = []
            if gap.framework_gaps:
                milestones.append(f"Learn {gap.framework_gaps[0].replace('_', ' ').title()}")
            if gap.missing_skills:
                milestones.append(f"Master {gap.missing_skills[0].replace('_', ' ').title()}")
            if req.system_design_level != "none":
                milestones.append(f"Complete {req.system_design_level} system design")
            milestones.append("Build 2 portfolio projects")
            milestones.append("Deploy projects with CI/CD")

            paths.append(CareerPath(
                path_type=PathType.DIRECT,
                steps=[{
                    "role": target_role,
                    "duration_months": direct_timeline,
                    "focus_skills": gap.missing_skills[:5] if gap.missing_skills else req.required_skills[:5],
                    "milestones": milestones[:4]
                }],
                total_duration_months=direct_timeline,
                success_probability=0.35 if college_tier == CollegeTier.TIER_3 else 0.55,
                salary_trajectory=[(target_role, salary_range[1])],
                reasoning=f"Direct path to {gap.role_display} in {direct_timeline} months. "
                         f"Key gaps: {', '.join(gap.missing_skills[:3]) if gap.missing_skills else 'minimal'}. "
                         f"Credential penalty: {gap.credential_penalty:.0%}.",
                risks=[
                    f"{req.hiring_difficulty} competition level",
                    f"Only {get_callback_rate(target_role, college_tier):.1%} callback rate",
                    f"May need {int(1/get_callback_rate(target_role, college_tier))}+ applications per interview"
                ]
            ))

        # Stepping-stone paths (always for tier-2/3, or if direct is unrealistic)
        if college_tier in [CollegeTier.TIER_2, CollegeTier.TIER_3] or not is_realistic:
            stepping_suggestions = get_stepping_stone_suggestions(target_role, current_state)

            for suggestion in stepping_suggestions[:2]:  # Top 2 stepping stones
                stepping_role = suggestion["role"]
                stepping_req = get_role_requirements(stepping_role)
                if not stepping_req:
                    continue

                step1_timeline = suggestion["timeline_months"]
                step2_timeline = estimate_timeline(college_tier.value, stepping_role, target_role)
                if step2_timeline < 0:
                    step2_timeline = 12

                stepping_salary = get_salary_range(stepping_role, location, college_tier)

                paths.append(CareerPath(
                    path_type=PathType.STEPPING_STONE,
                    steps=[
                        {
                            "role": stepping_role,
                            "duration_months": step1_timeline,
                            "focus_skills": stepping_req.required_skills[:4],
                            "milestones": [
                                f"Get hired as {stepping_role.replace('_', ' ').title()}",
                                f"Learn {stepping_req.framework_tools[0].replace('_', ' ').title() if stepping_req.framework_tools else 'key tools'}",
                                "Build internal credibility"
                            ]
                        },
                        {
                            "role": target_role,
                            "duration_months": step2_timeline,
                            "focus_skills": gap.missing_skills[:5] if gap.missing_skills else req.required_skills[:5],
                            "milestones": [
                                "Internal transition or external application",
                                "Leverage company experience",
                                f"Target: {gap.role_display}"
                            ]
                        }
                    ],
                    total_duration_months=step1_timeline + step2_timeline,
                    success_probability=0.65 if college_tier == CollegeTier.TIER_3 else 0.75,
                    salary_trajectory=[
                        (stepping_role, stepping_salary[1]),
                        (target_role, salary_range[1])
                    ],
                    reasoning=f"{suggestion['reasoning']}. This path takes {step1_timeline + step2_timeline} months total "
                             f"but has higher success probability. You earn while learning.",
                    risks=[
                        f"Only {get_callback_rate(stepping_role, college_tier):.1%} callback rate for {stepping_role.replace('_', ' ').title()}",
                        "May get comfortable in intermediate role",
                        "Internal transition not guaranteed",
                        "Total time is longer but probability is higher"
                    ],
                    alternative_if_failed=stepping_role
                ))

        # Alternative paths based on hidden strengths
        # Check for communication strength → DevRel, PM, Solutions
        if current_skills.get("communication", 0) >= 3:
            if target_role not in ["devrel", "product_manager", "solutions_engineer", "technical_writer"]:
                for alt_role in ["devrel", "technical_writer", "solutions_engineer"]:
                    if alt_role != target_role:
                        alt_req = get_role_requirements(alt_role)
                        if alt_req:
                            alt_salary = get_salary_range(alt_role, location, college_tier)
                            alt_timeline = estimate_timeline(college_tier.value, current_state, alt_role)
                            if alt_timeline < 0:
                                alt_timeline = 4

                            paths.append(CareerPath(
                                path_type=PathType.ALTERNATIVE,
                                steps=[{
                                    "role": alt_role,
                                    "duration_months": alt_timeline,
                                    "focus_skills": alt_req.required_skills[:4],
                                    "milestones": [
                                        f"Build {alt_role.replace('_', ' ')} portfolio",
                                        "Apply to 5 roles",
                                        "Network in the community"
                                    ]
                                }],
                                total_duration_months=alt_timeline,
                                success_probability=0.50,
                                salary_trajectory=[(alt_role, alt_salary[1])],
                                reasoning=f"Your communication skills are strong. {alt_role.replace('_', ' ').title()} leverages this strength, "
                                         f"has less credential bias, and keeps career options open.",
                                risks=[
                                    "Smaller job market than core engineering",
                                    "May feel disconnected from pure technical work",
                                    "Requires consistent portfolio building"
                                ]
                            ))
                            break  # Only add one alternative

        # Check for design/visual strength → UX/UI
        if current_skills.get("visual_design", 0) >= 3 or current_skills.get("creativity", 0) >= 3:
            if target_role not in ["ux_designer", "ui_designer"]:
                for alt_role in ["ux_designer", "ui_designer"]:
                    if alt_role != target_role:
                        alt_req = get_role_requirements(alt_role)
                        if alt_req:
                            alt_salary = get_salary_range(alt_role, location, college_tier)
                            alt_timeline = estimate_timeline(college_tier.value, current_state, alt_role)
                            if alt_timeline < 0:
                                alt_timeline = 6

                            paths.append(CareerPath(
                                path_type=PathType.ALTERNATIVE,
                                steps=[{
                                    "role": alt_role,
                                    "duration_months": alt_timeline,
                                    "focus_skills": alt_req.required_skills[:4],
                                    "milestones": [
                                        "Build design portfolio (3 case studies)",
                                        "Complete 1 redesign challenge",
                                        "Apply to 5 design roles"
                                    ]
                                }],
                                total_duration_months=alt_timeline,
                                success_probability=0.45,
                                salary_trajectory=[(alt_role, alt_salary[1])],
                                reasoning=f"Your visual/creative skills suggest design could be a strong fit. {alt_role.replace('_', ' ').title()} "
                                         f"has lower credential barriers and values portfolio over degree.",
                                risks=[
                                    "Portfolio takes time to build",
                                    "Design roles have subjective evaluation",
                                    "May need to learn design tools"
                                ]
                            ))
                            break

        # Sort by success probability
        paths.sort(key=lambda p: p.success_probability, reverse=True)

        return paths
