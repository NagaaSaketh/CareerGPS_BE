"""
LLM-Based Orchestrator for CareerGPS using Claude with Tool Calling.

Claude acts as the reasoning brain. The existing agents (SkillAssessor,
MarketMapper, PathPlanner) are exposed as callable tools. Claude decides
what to analyze, in what order, and writes the final report itself.

Streams SSE-compatible event dicts for real-time frontend display.
"""

import json
import os
from typing import AsyncGenerator, Dict, Any

import anthropic

from agents.skill_assessor import SkillAssessor
from agents.path_planner import MarketMapper
from data.market_data import (
    get_role_requirements, CollegeTier, normalize_role_name
)
from data.mock_jobs import generate_mock_jobs

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic JSON schema format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "assess_skills",
        "description": (
            "Assess the user's current skill levels using GitHub repository data, "
            "resume evidence, and diagnostic scores. Returns per-skill ratings "
            "(self-reported vs evidence-based), contradiction flags, and critical gaps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "profile": {
                    "type": "object",
                    "description": "Full user profile dict (target_role, github, resume, self_assessment, etc.)"
                }
            },
            "required": ["profile"]
        }
    },
    {
        "name": "analyze_career_gap",
        "description": (
            "Analyze the gap between the user's current skills and target role requirements. "
            "Returns list of missing skills, experience gap in months, and framework gaps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "current_skills": {
                    "type": "object",
                    "description": "Dict of skill_name -> rating (1-5)"
                },
                "experience_months": {"type": "integer"},
                "target_role": {"type": "string"},
                "college_tier": {
                    "type": "string",
                    "enum": ["tier_1", "tier_2", "tier_3"]
                }
            },
            "required": ["current_skills", "experience_months", "target_role", "college_tier"]
        }
    },
    {
        "name": "generate_career_paths",
        "description": (
            "Generate 2-3 strategic career paths (Direct, Stepping Stone, Alternative) "
            "with timelines in months, success probabilities, and actionable steps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "current_skills": {"type": "object"},
                "experience_months": {"type": "integer"},
                "target_role": {"type": "string"},
                "college_tier": {"type": "string"},
                "current_state": {"type": "string"},
                "location": {"type": "string"}
            },
            "required": ["current_skills", "experience_months", "target_role", "college_tier"]
        }
    },
    {
        "name": "lookup_role",
        "description": (
            "Look up detailed requirements for a specific career role from the market database. "
            "Returns required skills, minimum experience, salary range, hiring difficulty, "
            "and callback rates by college tier."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "role_name": {"type": "string"}
            },
            "required": ["role_name"]
        }
    },
    {
        "name": "fetch_market_jobs",
        "description": (
            "Fetch recent job listings for a role from the market database. "
            "Useful for grounding advice in real hiring signals."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "role_name": {"type": "string"},
                "location": {"type": "string", "description": "City or 'India'"}
            },
            "required": ["role_name"]
        }
    }
]

# ---------------------------------------------------------------------------
# System prompt (cached)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are CareerGPS, an evidence-based AI career advisor for Indian tech professionals.

You have access to tools that analyze user profiles, assess skills from real evidence (GitHub, resumes, diagnostics), map career gaps, and generate strategic paths.

Your analysis process:
1. Call lookup_role first to understand what the target role actually demands
2. Call assess_skills to get honest, evidence-backed skill ratings
3. Call analyze_career_gap to quantify the gap precisely
4. Call generate_career_paths to explore strategic options
5. Optionally call fetch_market_jobs to ground advice in real hiring signals

After using the tools, write a report with exactly three sections:

═══════════════════════════════════════
WHERE YOU ARE
═══════════════════════════════════════
Honest current-state assessment. Compare self-reported vs evidence ratings for key skills.
Call out contradictions (where self-rating exceeds evidence). List critical gaps.

═══════════════════════════════════════
WHERE YOU CAN GO
═══════════════════════════════════════
The best career path with: timeline in months, expected salary range (LPA), success probability.
Be specific about what stands between them and the goal.

═══════════════════════════════════════
YOUR 3 TASKS THIS WEEK
═══════════════════════════════════════
Exactly 3 tasks with clear expected outcomes. Format:
  1. [Task type: BUILD/LEARN/APPLY] Task description → Expected outcome

Rules:
- Be direct. Do not sugarcoat gaps.
- Every claim must trace to tool output.
- If evidence contradicts self-report, say so explicitly.
- Tier-3 college? Address the credential reality, don't hide it.
- IMPORTANT: Do NOT wrap any section content in code fences (```). Write all content as plain markdown — headers, bold, bullet lists, tables directly in the text. No ``` blocks anywhere in the report.
- Do NOT output any preamble or thinking text before the first ═══ section divider."""


# ---------------------------------------------------------------------------
# Tool executor — wraps existing deterministic agents
# ---------------------------------------------------------------------------

def _parse_college_tier(tier_str: str) -> CollegeTier:
    mapping = {
        "tier_1": CollegeTier.TIER_1,
        "tier1": CollegeTier.TIER_1,
        "tier_2": CollegeTier.TIER_2,
        "tier2": CollegeTier.TIER_2,
        "tier_3": CollegeTier.TIER_3,
        "tier3": CollegeTier.TIER_3,
    }
    return mapping.get(str(tier_str).lower(), CollegeTier.TIER_3)


def execute_tool(name: str, inputs: dict, profile: dict) -> dict:
    """Route Claude's tool calls to existing agent implementations."""

    if name == "assess_skills":
        assessor = SkillAssessor()
        target_profile = inputs.get("profile", profile)
        result = assessor.generate_full_assessment(target_profile)
        skills = {
            k: {
                "self_reported": v.self_reported,
                "evidence_based": v.evidence_based,
                "contradiction": v.contradiction_flag,
                "gaps": v.gaps
            }
            for k, v in result["skills"].items()
        }
        return {
            "skills": skills,
            "trust_score": result.get("overall_trust_score", 0),
            "critical_gaps": result.get("critical_gaps", []),
            "contradiction_count": len(result.get("contradictions", []))
        }

    elif name == "analyze_career_gap":
        mapper = MarketMapper()
        college_tier = _parse_college_tier(inputs.get("college_tier", "tier_3"))
        gap = mapper.analyze_gap(
            inputs["current_skills"],
            inputs["experience_months"],
            inputs["target_role"],
            college_tier
        )
        return {
            "missing_skills": gap.missing_skills,
            "experience_gap_months": gap.experience_gap_months,
            "framework_gaps": gap.framework_gaps,
            "system_design_gap": gap.system_design_gap,
            "credential_penalty": gap.credential_penalty,
            "is_role_known": gap.is_role_known
        }

    elif name == "generate_career_paths":
        mapper = MarketMapper()
        college_tier = _parse_college_tier(inputs.get("college_tier", "tier_3"))
        paths = mapper.generate_paths(
            inputs["current_skills"],
            inputs["experience_months"],
            inputs["target_role"],
            college_tier,
            inputs.get("current_state", "unknown"),
            inputs.get("location", "india")
        )
        return {
            "paths": [
                {
                    "type": p.path_type.value,
                    "timeline_months": p.total_duration_months,
                    "success_probability": p.success_probability,
                    "reasoning": p.reasoning,
                    "risks": p.risks[:3],
                    "steps": p.steps[:3],
                    "salary_trajectory": [
                        {"milestone": m, "lpa": s} for m, s in p.salary_trajectory
                    ]
                }
                for p in paths
            ]
        }

    elif name == "lookup_role":
        role_name = normalize_role_name(inputs["role_name"])
        req = get_role_requirements(role_name)
        if not req:
            return {"error": f"Role '{inputs['role_name']}' not found in database"}
        return {
            "role": req.role_name,
            "category": req.role_category,
            "required_skills": req.required_skills,
            "preferred_skills": req.preferred_skills,
            "framework_tools": req.framework_tools,
            "min_experience_months": req.min_experience_months,
            "salary_range_lpa": list(req.salary_range_lpa),
            "hiring_difficulty": req.hiring_difficulty,
            "callback_rates": {
                "tier_1": req.tier_1_callback_rate,
                "tier_2": req.tier_2_callback_rate,
                "tier_3": req.tier_3_callback_rate
            },
            "typical_rejection_reasons": req.typical_rejection_reasons[:3]
        }

    elif name == "fetch_market_jobs":
        jobs = generate_mock_jobs(
            inputs["role_name"],
            inputs.get("location", "India"),
            count=3
        )
        return {
            "jobs": [
                {
                    "title": j.get("title"),
                    "company": j.get("company"),
                    "location": j.get("location"),
                    "skills_found": j.get("skills_found", [])[:5]
                }
                for j in jobs[:3]
            ]
        }

    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Human-readable labels & summaries for the frontend trace UI
# ---------------------------------------------------------------------------

def _tool_label(tool_name: str) -> str:
    labels = {
        "assess_skills": "Assessing skills from evidence",
        "analyze_career_gap": "Mapping market gap",
        "generate_career_paths": "Building career paths",
        "lookup_role": "Reading role requirements",
        "fetch_market_jobs": "Checking market signals",
    }
    return labels.get(tool_name, tool_name.replace("_", " ").title())


def _tool_summary(tool_name: str, result: dict) -> str:
    if "error" in result:
        return f"Warning: {result['error']}"
    if tool_name == "assess_skills":
        gaps = len(result.get("critical_gaps", []))
        contradictions = result.get("contradiction_count", 0)
        trust = result.get("trust_score", 0)
        return f"{gaps} critical gaps · {contradictions} contradictions · {trust:.0%} evidence trust"
    if tool_name == "analyze_career_gap":
        missing = len(result.get("missing_skills", []))
        exp_gap = result.get("experience_gap_months", 0)
        return f"{missing} missing skills · {exp_gap}mo experience gap"
    if tool_name == "generate_career_paths":
        paths = result.get("paths", [])
        if paths:
            best = paths[0]
            return f"{len(paths)} paths · best: {best['type']} ({best['timeline_months']}mo, {best['success_probability']:.0%} success)"
        return "No paths generated"
    if tool_name == "lookup_role":
        salary = result.get("salary_range_lpa", [0, 0])
        difficulty = result.get("hiring_difficulty", "?")
        return f"{difficulty} difficulty · ₹{salary[0]}-{salary[1]} LPA"
    if tool_name == "fetch_market_jobs":
        return f"{len(result.get('jobs', []))} live job signals found"
    return "Done"


# ---------------------------------------------------------------------------
# Main async generator — yields SSE event dicts
# ---------------------------------------------------------------------------

async def run_agentic_analysis(profile: dict) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run Claude-orchestrated career analysis.

    Yields SSE event dicts:
      {"type": "tool_start", "tool": str, "label": str}
      {"type": "tool_end",   "tool": str, "summary": str}
      {"type": "text_delta", "text": str}
      {"type": "done",       "structured_data": dict}
      {"type": "error",      "message": str}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield {"type": "error", "message": "ANTHROPIC_API_KEY not set"}
        return

    client = anthropic.Anthropic(api_key=api_key)

    messages = [
        {
            "role": "user",
            "content": (
                f"Please analyze this user profile and generate a career report:\n\n"
                f"```json\n{json.dumps(profile, indent=2, default=str)}\n```"
            )
        }
    ]

    tool_results_accumulated: Dict[str, Any] = {}
    max_iterations = 8  # safety cap on tool-call loops

    for _ in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}  # prompt caching
                }
            ],
            tools=TOOLS,
            messages=messages
        )

        tool_uses = []

        for block in response.content:
            if block.type == "text" and block.text:
                # Stream the final report word by word for the typewriter effect
                words = block.text.split(" ")
                for i, word in enumerate(words):
                    suffix = " " if i < len(words) - 1 else ""
                    yield {"type": "text_delta", "text": word + suffix}

            elif block.type == "tool_use":
                tool_uses.append(block)
                yield {
                    "type": "tool_start",
                    "tool": block.name,
                    "label": _tool_label(block.name)
                }

                # Execute the tool (sync — existing agents are synchronous)
                result = execute_tool(block.name, block.input, profile)
                tool_results_accumulated[block.name] = result

                yield {
                    "type": "tool_end",
                    "tool": block.name,
                    "summary": _tool_summary(block.name, result)
                }

        # If Claude used tools, feed results back and continue the loop
        if tool_uses and response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_result_blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": t.id,
                    "content": json.dumps(
                        tool_results_accumulated.get(t.name, {}),
                        default=str
                    )
                }
                for t in tool_uses
            ]
            messages.append({"role": "user", "content": tool_result_blocks})
        else:
            # Claude finished — no more tool calls
            yield {"type": "done", "structured_data": tool_results_accumulated}
            return

    # Hit iteration cap — emit done with whatever we have
    yield {"type": "done", "structured_data": tool_results_accumulated}
