"""
CareerGPS Job Description Scrapers
Real-time market data from LinkedIn, Indeed, Glassdoor, and Naukri.
"""

from .jd_scraper import JobDataAggregator, MarketSnapshot, refresh_market_data
from .scraper_utils import ScrapedJob, normalize_skills, extract_salary_range

__all__ = [
    "JobDataAggregator",
    "MarketSnapshot", 
    "refresh_market_data",
    "ScrapedJob",
    "normalize_skills",
    "extract_salary_range",
]
