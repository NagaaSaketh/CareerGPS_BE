#!/usr/bin/env python3
"""
Weekly Market Data Refresh Script
Scrapes job listings for India-focused roles and upserts them into the
Supabase market_snapshots table.

Run manually:
    python scripts/refresh_market.py

Or schedule via cron (e.g., every Sunday at 3 AM):
    0 3 * * 0 cd /path/to/careergps-backend && python scripts/refresh_market.py
"""

import os
import sys
import logging
from dataclasses import asdict

# Add parent directory to path so we can import careergps modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.jd_scraper import JobDataAggregator
from db import get_supabase, save_market_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# India-focused roles (most in-demand tech roles)
ROLES = [
    "backend_engineer",
    "frontend_engineer",
    "fullstack_engineer",
    "data_scientist",
    "data_analyst",
    "devops_engineer",
    "mobile_developer",
    "software_developer",
    "sde",
    "generative_ai_engineer",
    "nlp_engineer",
    "computer_vision_engineer",
    "ai_research_scientist",
    "mlops_engineer",
    "prompt_engineer",
]

# India-focused locations
LOCATIONS = [
    "India",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Mumbai",
    "Delhi",
    "Remote",
]

JOBS_PER_SOURCE = int(os.getenv("JOBS_PER_SOURCE", "5"))


def job_to_dict(job) -> dict:
    """Serialize a ScrapedJob dataclass to a plain dict."""
    d = asdict(job)
    # Ensure tuple fields are lists for JSON serialization
    if d.get("salary_lpa") and isinstance(d["salary_lpa"], tuple):
        d["salary_lpa"] = list(d["salary_lpa"])
    if d.get("experience_months") and isinstance(d["experience_months"], tuple):
        d["experience_months"] = list(d["experience_months"])
    return d


def main():
    logger.info("=" * 60)
    logger.info("CareerGPS Weekly Market Refresh — India Focused")
    logger.info("=" * 60)

    # Verify Supabase is configured
    try:
        get_supabase()
        logger.info("Supabase connection OK")
    except Exception as e:
        logger.error(f"Supabase not configured: {e}")
        sys.exit(1)

    aggregator = JobDataAggregator()
    total_combos = len(ROLES) * len(LOCATIONS)
    processed = 0
    success = 0
    failed = 0

    for role in ROLES:
        for location in LOCATIONS:
            processed += 1
            logger.info(f"[{processed}/{total_combos}] Scraping '{role}' in '{location}' ...")

            try:
                # Scrape raw jobs
                jobs = aggregator.scrape_jobs_raw(role, location, limit_per_source=JOBS_PER_SOURCE)

                if not jobs:
                    logger.warning(f"  No jobs found for {role}/{location}")
                    failed += 1
                    continue

                # Build snapshot
                snapshot = aggregator._build_snapshot(
                    role=role,
                    location=location,
                    jobs=jobs,
                    sources=list(set(j.source for j in jobs)),
                    uncertainty_flags=[],
                )

                # Serialize for Supabase
                jobs_data = [job_to_dict(j) for j in jobs]
                top_skills = [[s, c] for s, c in snapshot.top_skills]

                save_market_snapshot(role, location, {
                    "jobs": jobs_data,
                    "salary_range_lpa": list(snapshot.salary_range_lpa) if snapshot.salary_range_lpa else None,
                    "experience_range_months": list(snapshot.experience_range_months),
                    "top_skills": top_skills,
                    "top_companies": snapshot.top_companies,
                    "hiring_volume_indicator": snapshot.hiring_volume_indicator,
                    "data_quality_score": snapshot.data_quality_score,
                    "uncertainty_flags": snapshot.uncertainty_flags,
                })

                logger.info(
                    f"  ✓ Saved {len(jobs_data)} jobs | "
                    f"salary: {snapshot.salary_range_lpa} | "
                    f"volume: {snapshot.hiring_volume_indicator}"
                )
                success += 1

            except Exception as e:
                logger.error(f"  ✗ Failed: {e}")
                failed += 1

    logger.info("=" * 60)
    logger.info(f"Done: {success} succeeded, {failed} failed out of {total_combos} combinations")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
