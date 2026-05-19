"""
JSearch API Scraper
Fetches real job listings via RapidAPI's JSearch (powered by Google for Jobs).
Covers LinkedIn, Indeed, Glassdoor, ZipRecruiter, and more.
"""

import os
import logging
from typing import List

import requests

from .scraper_utils import ScrapedJob

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
JSEARCH_HOST = "jsearch.p.rapidapi.com"
JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"


class JSearchScraper:
    """Fetches jobs from JSearch API (RapidAPI)."""

    def search_jobs(self, role: str, location: str = "India", limit: int = 10) -> List[ScrapedJob]:
        if not RAPIDAPI_KEY:
            logger.warning("[JSearch] RAPIDAPI_KEY not set — skipping")
            return []

        query = f"{role.replace('_', ' ')} jobs in {location}"
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": JSEARCH_HOST,
        }
        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "date_posted": "month",
        }

        try:
            resp = requests.get(JSEARCH_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[JSearch] Request failed: {e}")
            return []

        jobs = []
        for item in (data.get("data") or [])[:limit]:
            try:
                # Salary — JSearch returns min/max in USD; convert roughly to LPA if INR not available
                salary_min = item.get("job_min_salary")
                salary_max = item.get("job_max_salary")
                salary_lpa = None
                if salary_min and salary_max:
                    # If salary currency is USD, convert approx to LPA (1 USD ≈ 83 INR, /100000 for LPA)
                    currency = item.get("job_salary_currency", "USD")
                    if currency == "USD":
                        salary_lpa = [
                            round(salary_min * 83 / 100000, 1),
                            round(salary_max * 83 / 100000, 1),
                        ]
                    else:
                        salary_lpa = [
                            round(salary_min / 100000, 1),
                            round(salary_max / 100000, 1),
                        ]

                # Experience
                exp_required = item.get("job_required_experience", {}) or {}
                exp_months_min = (exp_required.get("required_experience_in_months") or 0)
                exp_months_max = exp_months_min + 24  # estimate range

                # Skills
                skills = [s.lower().replace(" ", "_") for s in (item.get("job_required_skills") or [])[:6]]

                job = ScrapedJob(
                    title=item.get("job_title", ""),
                    company=item.get("employer_name", ""),
                    location=item.get("job_city") or item.get("job_country") or location,
                    url=item.get("job_apply_link") or item.get("job_google_link") or "",
                    source=item.get("job_publisher", "jsearch").lower().replace(" ", "_"),
                    description=item.get("job_description", "")[:300],
                    skills_found=skills,
                    salary_lpa=salary_lpa,
                    experience_months=[exp_months_min, exp_months_max],
                )
                jobs.append(job)
            except Exception as e:
                logger.warning(f"[JSearch] Failed to parse job item: {e}")
                continue

        logger.info(f"[JSearch] {len(jobs)} jobs for '{role}' in '{location}'")
        return jobs
