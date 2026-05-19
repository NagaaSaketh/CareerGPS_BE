"""
Live Market Data Integration Module
Bridges static market data with real-time JD scraping.

When live data is available and fresh, it augments or overrides static data.
When scrapers fail, it gracefully falls back to the hardcoded database.

This module is the single source of truth for "where does our market data come from?"
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from data.market_data import (
    RoleRequirements, CollegeTier, ROLE_DATABASE,
    get_role_requirements as _static_get_role_requirements,
    get_callback_rate as _static_get_callback_rate,
    get_salary_range as _static_get_salary_range,
)

logger = logging.getLogger(__name__)

# Feature flag: Enable live scraping?
ENABLE_JD_SCRAPING = os.getenv("ENABLE_JD_SCRAPING", "true").lower() in ("true", "1", "yes")


@dataclass
class DataProvenance:
    """Tracks where a specific data point came from."""
    source: str  # 'static', 'linkedin', 'indeed', 'naukri', 'glassdoor', 'aggregated'
    freshness: str  # 'live', 'cached', 'static'
    confidence: float  # 0.0 to 1.0
    scraped_at: Optional[str] = None
    uncertainty_flags: List[str] = None


# =============================================================================
# LIVE DATA INTEGRATION
# =============================================================================

def get_live_role_requirements(role: str, location: str = "India") -> Tuple[Optional[RoleRequirements], DataProvenance]:
    """
    Get role requirements, enriched with live JD data if available.
    Returns (RoleRequirements, DataProvenance) so callers know data origin.
    """
    static_req = _static_get_role_requirements(role)
    if not static_req:
        return None, DataProvenance(source="static", freshness="static", confidence=0.0)

    if not ENABLE_JD_SCRAPING:
        return static_req, DataProvenance(
            source="static",
            freshness="static",
            confidence=0.7,
            uncertainty_flags=["JD_SCRAPING_DISABLED: Using static market data only"]
        )

    try:
        from scrapers.jd_scraper import refresh_market_data
        snapshot = refresh_market_data(role, location, force_refresh=False)

        if snapshot.data_quality_score < 0.3:
            # Live data too sparse; use static with uncertainty flag
            return static_req, DataProvenance(
                source="static",
                freshness="static",
                confidence=0.6,
                uncertainty_flags=snapshot.uncertainty_flags + [
                    f"LIVE_DATA_SPARSE: Quality score {snapshot.data_quality_score}, using static fallback"
                ]
            )

        # Merge live data with static data
        merged_req = _merge_live_data(static_req, snapshot)
        provenance = DataProvenance(
            source="aggregated",
            freshness="live" if "_error" not in str(snapshot.uncertainty_flags) else "cached",
            confidence=snapshot.data_quality_score,
            scraped_at=snapshot.scraped_at,
            uncertainty_flags=snapshot.uncertainty_flags,
        )
        return merged_req, provenance

    except Exception as e:
        logger.error(f"Live data fetch failed for {role}: {e}")
        return static_req, DataProvenance(
            source="static",
            freshness="static",
            confidence=0.6,
            uncertainty_flags=[f"LIVE_FETCH_ERROR: {str(e)}. Using static fallback."]
        )


def _merge_live_data(static_req: RoleRequirements, snapshot) -> RoleRequirements:
    """
    Merge live scraped data into static RoleRequirements.
    Live data augments but does not fully replace static data,
    because scrapers may miss nuanced requirements.
    """
    # Start with static data
    merged = RoleRequirements(
        role_name=static_req.role_name,
        role_category=static_req.role_category,
        min_experience_months=static_req.min_experience_months,
        required_skills=list(static_req.required_skills),
        preferred_skills=list(static_req.preferred_skills),
        framework_tools=list(static_req.framework_tools),
        system_design_level=static_req.system_design_level,
        salary_range_lpa=static_req.salary_range_lpa,
        hiring_difficulty=static_req.hiring_difficulty,
        typical_rejection_reasons=list(static_req.typical_rejection_reasons),
        tier_1_callback_rate=static_req.tier_1_callback_rate,
        tier_2_callback_rate=static_req.tier_2_callback_rate,
        tier_3_callback_rate=static_req.tier_3_callback_rate,
        stepping_stone_roles=list(static_req.stepping_stone_roles),
        strength_indicators=list(static_req.strength_indicators),
    )

    # Override salary if live data is available and reasonable
    if snapshot.salary_range_lpa:
        live_min, live_max = snapshot.salary_range_lpa
        static_min, static_max = static_req.salary_range_lpa

        # Only override if live data is within 50% of static (sanity check)
        if (static_min * 0.5) <= live_min <= (static_max * 1.5):
            merged.salary_range_lpa = (live_min, live_max)

    # Augment skills with live-discovered skills
    live_skills = [skill for skill, _ in snapshot.top_skills]
    for skill in live_skills:
        if skill not in merged.required_skills and skill not in merged.preferred_skills:
            # Add high-frequency skills to preferred
            merged.preferred_skills.append(skill)

    # Adjust experience if live data shows different norms
    if snapshot.experience_range_months != (0, 0):
        live_exp_min = snapshot.experience_range_months[0]
        # Only update if live minimum is higher (indicates market shift)
        if live_exp_min > merged.min_experience_months:
            merged.min_experience_months = live_exp_min

    return merged


# =============================================================================
# WRAPPER FUNCTIONS (drop-in replacements for static functions)
# =============================================================================

def get_role_requirements(role: str, use_live: bool = True) -> Optional[RoleRequirements]:
    """
    Drop-in replacement for data.market_data.get_role_requirements.
    Returns live-enriched requirements when available.
    """
    if not use_live:
        return _static_get_role_requirements(role)

    req, _ = get_live_role_requirements(role)
    return req


def get_salary_range(role: str, location: str, college_tier: CollegeTier, use_live: bool = True) -> Tuple[float, float]:
    """
    Drop-in replacement for data.market_data.get_salary_range.
    Uses live salary data when available and trustworthy.
    """
    if not use_live:
        return _static_get_salary_range(role, location, college_tier)

    req, provenance = get_live_role_requirements(role, location)
    if not req:
        return (0.0, 0.0)

    base_min, base_max = req.salary_range_lpa

    # Apply location multiplier
    from data.market_data import LOCATION_MULTIPLIERS
    loc_mult = LOCATION_MULTIPLIERS.get(location.lower(), 1.0)

    # Apply college tier adjustment
    from data.market_data import COLLEGE_TIER_IMPACT
    tier_data = COLLEGE_TIER_IMPACT.get(college_tier, {})
    salary_premium = tier_data.get("salary_premium", 0.0)

    adjusted_min = round(base_min * loc_mult * (1 + salary_premium), 2)
    adjusted_max = round(base_max * loc_mult * (1 + salary_premium), 2)

    return (adjusted_min, adjusted_max)


def get_data_provenance(role: str, location: str = "India") -> Dict:
    """
    Public API to expose where the data for a role came from.
    Used by the frontend to show "Data sourced from..." badges.
    """
    _, provenance = get_live_role_requirements(role, location)
    return {
        "source": provenance.source,
        "freshness": provenance.freshness,
        "confidence": provenance.confidence,
        "scraped_at": provenance.scraped_at,
        "uncertainty_flags": provenance.uncertainty_flags or [],
    }
