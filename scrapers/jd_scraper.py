"""
Job Description Scraper Orchestrator
Aggregates real-time JD data from LinkedIn, Indeed, Glassdoor, and Naukri.
Normalizes, deduplicates, and extracts market intelligence.
"""

import logging
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter

from .scraper_utils import ScrapedJob
from .linkedin_scraper import LinkedInScraper
from .indeed_scraper import IndeedScraper
from .naukri_scraper import NaukriScraper
from .glassdoor_scraper import GlassdoorScraper
from .browser_scraper import BrowserScraper

logger = logging.getLogger(__name__)

# Cache file path
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "market_snapshot.json")
CACHE_TTL_HOURS = 24  # Refresh data every 24 hours


@dataclass
class MarketSnapshot:
    """
    Aggregated market intelligence from scraped job postings.
    This is what the Market Mapper consumes to ground recommendations in reality.
    """
    role: str
    location: str
    scraped_at: str
    sources: List[str] = field(default_factory=list)
    total_jobs_scraped: int = 0

    # Extracted intelligence
    top_skills: List[Tuple[str, int]] = field(default_factory=list)  # (skill, frequency)
    salary_range_lpa: Optional[Tuple[float, float]] = None
    experience_range_months: Tuple[int, int] = field(default=(0, 0))
    hiring_volume_indicator: str = "unknown"  # high / medium / low
    top_companies: List[str] = field(default_factory=list)

    # Data quality flags
    data_quality_score: float = 0.0  # 0.0 to 1.0
    uncertainty_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MarketSnapshot":
        return cls(**data)


class JobDataAggregator:
    """
    Orchestrates multi-source JD scraping and aggregates market intelligence.
    Implements graceful degradation: if a source fails, others still contribute.
    """

    def __init__(
        self,
        linkedin: Optional[LinkedInScraper] = None,
        indeed: Optional[IndeedScraper] = None,
        naukri: Optional[NaukriScraper] = None,
        glassdoor: Optional[GlassdoorScraper] = None,
    ):
        self.linkedin = linkedin or LinkedInScraper()
        self.indeed = indeed or IndeedScraper()
        self.naukri = naukri or NaukriScraper()
        self.glassdoor = glassdoor or GlassdoorScraper()

        self.sources = {
            "linkedin": self.linkedin,
            "indeed": self.indeed,
            "naukri": self.naukri,
            "glassdoor": self.glassdoor,
        }

    def aggregate(
        self,
        role: str,
        location: str = "India",
        jobs_per_source: int = 8,
        use_browser: bool = True,
    ) -> MarketSnapshot:
        """
        Scrape all configured sources and aggregate into a MarketSnapshot.
        This is the primary entry point for live market data.
        """
        all_jobs: List[ScrapedJob] = []
        active_sources = []
        uncertainty_flags = []

        logger.info(f"[Aggregator] Starting aggregation for '{role}' in '{location}'")

        # Try browser-based scraping first (much more reliable)
        if use_browser:
            browser = None
            try:
                browser = BrowserScraper(headless=True)
                browser_jobs = browser.scrape_all(role, location, limit_per_source=jobs_per_source)
                if browser_jobs:
                    all_jobs.extend(browser_jobs)
                    active_sources.extend(list(set(j.source for j in browser_jobs)))
                    logger.info(f"[Aggregator] Browser scraper: {len(browser_jobs)} total jobs")
            except Exception as e:
                logger.warning(f"[Aggregator] Browser scraper failed: {e}")
                uncertainty_flags.append(f"browser_error: {str(e)}")
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception as close_err:
                        logger.warning(f"[Aggregator] Browser cleanup error: {close_err}")

        # Fallback to HTTP scrapers if browser got nothing
        if not all_jobs:
            for name, scraper in self.sources.items():
                try:
                    jobs = scraper.search_jobs(role, location, limit=jobs_per_source)
                    if jobs:
                        all_jobs.extend(jobs)
                        active_sources.append(name)
                        logger.info(f"[Aggregator] {name}: {len(jobs)} jobs")
                    else:
                        uncertainty_flags.append(f"{name}_no_data: No jobs returned (may be blocked or no listings)")
                except Exception as e:
                    logger.error(f"[Aggregator] {name} scraper failed: {e}")
                    uncertainty_flags.append(f"{name}_error: Scraper failed - {str(e)}")

        if not all_jobs:
            logger.warning("[Aggregator] No jobs scraped from any source.")
            return MarketSnapshot(
                role=role,
                location=location,
                scraped_at=datetime.now().isoformat(),
                sources=list(self.sources.keys()),
                total_jobs_scraped=0,
                uncertainty_flags=uncertainty_flags + ["ALL_SOURCES_FAILED: Using fallback static data"],
                data_quality_score=0.0,
            )

        # Build aggregated intelligence
        snapshot = self._build_snapshot(role, location, all_jobs, active_sources, uncertainty_flags)
        return snapshot

    def scrape_jobs_raw(
        self,
        role: str,
        location: str = "India",
        limit_per_source: int = 5,
    ) -> List[ScrapedJob]:
        """
        Return raw scraped job listings (not aggregated).
        Uses lightweight HTTP-based scrapers to avoid launching Chromium,
        which causes OOM kills on low-memory systems.
        """
        jobs: List[ScrapedJob] = []
        seen_urls = set()
        seen_titles = set()

        for name, scraper in self.sources.items():
            try:
                scraped = scraper.search_jobs(role, location, limit=limit_per_source)
                logger.info(f"[scrape_jobs_raw] {name}: {len(scraped)} jobs")
                for job in scraped:
                    url_key = job.url.split("?")[0] if job.url else ""
                    dedupe_key = url_key if url_key else f"{job.title}|{job.company}"
                    title_key = f"{job.title}|{job.company}|{job.location}"
                    if dedupe_key in seen_urls or title_key in seen_titles:
                        continue
                    if job.title and job.company:
                        seen_urls.add(dedupe_key)
                        seen_titles.add(title_key)
                        jobs.append(job)
            except Exception as e:
                logger.warning(f"[scrape_jobs_raw] {name} failed: {e}")

        return jobs

    def _build_snapshot(
        self,
        role: str,
        location: str,
        jobs: List[ScrapedJob],
        sources: List[str],
        uncertainty_flags: List[str],
    ) -> MarketSnapshot:
        """Transform raw scraped jobs into structured market intelligence."""

        # 1. Skill frequency analysis
        all_skills = []
        for job in jobs:
            all_skills.extend(job.skills_found)
        skill_counts = Counter(all_skills)
        top_skills = skill_counts.most_common(15)

        # 2. Salary aggregation
        salaries = [job.salary_lpa for job in jobs if job.salary_lpa]
        if salaries:
            all_mins = [s[0] for s in salaries]
            all_maxs = [s[1] for s in salaries]
            # Remove outliers (beyond 2 std devs)
            salary_range = self._remove_outliers(all_mins, all_maxs)
        else:
            salary_range = None
            uncertainty_flags.append("NO_SALARY_DATA: No salary info found in scraped JDs")

        # 3. Experience range
        exp_mins = [job.experience_months[0] for job in jobs if job.experience_months[0] > 0]
        exp_maxs = [job.experience_months[1] for job in jobs if job.experience_months[1] > 0]
        if exp_mins and exp_maxs:
            experience_range = (min(exp_mins), max(exp_maxs))
        else:
            experience_range = (0, 0)
            uncertainty_flags.append("NO_EXPERIENCE_DATA: No experience requirements found")

        # 4. Hiring volume indicator
        total_jobs = len(jobs)
        if total_jobs >= 25:
            volume = "high"
        elif total_jobs >= 10:
            volume = "medium"
        else:
            volume = "low"

        # 5. Top companies
        companies = [job.company for job in jobs if job.company != "Unknown"]
        top_companies = [c for c, _ in Counter(companies).most_common(5)]

        # 6. Data quality score
        quality_score = self._calculate_quality_score(jobs, salaries, experience_range)

        return MarketSnapshot(
            role=role,
            location=location,
            scraped_at=datetime.now().isoformat(),
            sources=sources,
            total_jobs_scraped=total_jobs,
            top_skills=top_skills,
            salary_range_lpa=salary_range,
            experience_range_months=experience_range,
            hiring_volume_indicator=volume,
            top_companies=top_companies,
            data_quality_score=quality_score,
            uncertainty_flags=uncertainty_flags,
        )

    def _remove_outliers(self, mins: List[float], maxs: List[float]) -> Tuple[float, float]:
        """Remove salary outliers using IQR method."""
        all_values = mins + maxs
        if len(all_values) < 4:
            return (round(min(all_values), 2), round(max(all_values), 2))

        sorted_vals = sorted(all_values)
        q1 = sorted_vals[len(sorted_vals) // 4]
        q3 = sorted_vals[(3 * len(sorted_vals)) // 4]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        filtered = [v for v in all_values if lower <= v <= upper]
        if not filtered:
            filtered = all_values

        return (round(min(filtered), 2), round(max(filtered), 2))

    def _calculate_quality_score(
        self,
        jobs: List[ScrapedJob],
        salaries: List[Tuple[float, float]],
        experience_range: Tuple[int, int],
    ) -> float:
        """
        Calculate a 0.0-1.0 score representing data quality.
        Higher = more complete and trustworthy data.
        """
        score = 0.0

        # Volume contribution
        score += min(0.3, len(jobs) / 50 * 0.3)

        # Salary data contribution
        if salaries:
            score += 0.25

        # Experience data contribution
        if experience_range != (0, 0):
            score += 0.2

        # Skill extraction contribution
        jobs_with_skills = sum(1 for j in jobs if j.skills_found)
        score += min(0.25, jobs_with_skills / len(jobs) * 0.25)

        return round(score, 2)


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_cached_snapshot(role: str, location: str) -> Optional[MarketSnapshot]:
    """Load a cached MarketSnapshot if it exists and is fresh."""
    _ensure_cache_dir()
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    key = f"{role.lower()}__{location.lower()}"
    entry = cache.get(key)
    if not entry:
        return None

    # Check TTL
    scraped_at = datetime.fromisoformat(entry["scraped_at"])
    if datetime.now() - scraped_at > timedelta(hours=CACHE_TTL_HOURS):
        return None

    return MarketSnapshot.from_dict(entry)


def save_snapshot_to_cache(snapshot: MarketSnapshot):
    """Save a MarketSnapshot to the cache."""
    _ensure_cache_dir()
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            cache = {}

    key = f"{snapshot.role.lower()}__{snapshot.location.lower()}"
    cache[key] = snapshot.to_dict()

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, default=str)


# =============================================================================
# PUBLIC API
# =============================================================================

def refresh_market_data(
    role: str,
    location: str = "India",
    force_refresh: bool = False,
    jobs_per_source: int = 8,
) -> MarketSnapshot:
    """
    Public function to refresh market data for a role+location.
    Uses cache unless force_refresh=True.
    This is called by the MarketMapper when it needs live data.
    """
    if not force_refresh:
        cached = load_cached_snapshot(role, location)
        if cached:
            logger.info(f"[refresh_market_data] Using cached snapshot for {role}/{location}")
            return cached

    aggregator = JobDataAggregator()
    snapshot = aggregator.aggregate(role, location, jobs_per_source=jobs_per_source)
    save_snapshot_to_cache(snapshot)
    return snapshot
