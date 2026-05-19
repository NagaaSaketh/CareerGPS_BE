"""
Naukri.com Job Scraper
Scrapes Naukri for India-specific JD data.
Source: https://www.naukri.com/
"""

import logging
import urllib.parse
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from .scraper_utils import create_session, respectful_request, ScrapedJob

logger = logging.getLogger(__name__)


class NaukriScraper:
    """Scraper for Naukri.com job listings."""

    BASE_URL = "https://www.naukri.com/"

    def __init__(self):
        self.session = create_session()
        self.source_name = "naukri"

    def search_jobs(
        self,
        role: str,
        location: str = "India",
        limit: int = 10
    ) -> List[ScrapedJob]:
        """Search Naukri jobs for a given role and location."""
        jobs = []
        query = role.lower().strip().replace(" ", "-")
        loc = location.lower().strip().replace(" ", "-")
        url = f"{self.BASE_URL}{query}-jobs-in-{loc}"

        logger.info(f"[Naukri] Searching: {role} in {location}")
        response = respectful_request(url, self.session, delay_range=(2.0, 4.0))

        if not response:
            logger.warning("[Naukri] Failed to fetch search page.")
            return jobs

        soup = BeautifulSoup(response.text, "lxml")

        # Naukri job cards
        job_cards = soup.find_all("div", class_="srp-jobtuple-wrapper")
        if not job_cards:
            job_cards = soup.find_all("article", class_="jobTuple")
        if not job_cards:
            job_cards = soup.find_all("div", {"class": re.compile(r"jobTuple|list")})

        logger.info(f"[Naukri] Found {len(job_cards)} job cards on page.")

        for card in job_cards[:limit]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[Naukri] Failed to parse card: {e}")
                continue

        logger.info(f"[Naukri] Successfully scraped {len(jobs)} jobs.")
        return jobs

    def _parse_job_card(self, card: BeautifulSoup) -> Optional[ScrapedJob]:
        """Parse a single Naukri job card."""
        # Title
        title_tag = card.find("a", class_="title") or card.find("a", class_="jobTupleTitle")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Company
        company_tag = card.find("a", class_="comp-name") or card.find("div", class_="companyInfo")
        if not company_tag:
            company_tag = card.find("span", class_="orgRating")
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"

        # Location
        loc_tag = card.find("span", class_="locWdth") or card.find("span", class_="location")
        location = loc_tag.get_text(strip=True) if loc_tag else "India"

        # URL
        job_url = ""
        if title_tag and title_tag.get("href"):
            job_url = title_tag["href"]
            if job_url.startswith("/"):
                job_url = f"https://www.naukri.com{job_url}"

        # Experience
        exp_tag = card.find("span", class_="expwdth") or card.find("span", class_="experience")
        exp_text = exp_tag.get_text(strip=True) if exp_tag else ""

        # Salary
        salary_tag = card.find("span", class_="ni-job-tuple-icon-srp-rupee") or card.find("span", class_="salary")
        salary_text = salary_tag.get_text(strip=True) if salary_tag else ""

        # Description / Skills
        desc_tag = card.find("span", class_="job-desc") or card.find("div", class_="job-description")
        description = desc_tag.get_text(separator=" ", strip=True) if desc_tag else ""

        # Combine all text for skill extraction
        full_text = f"{title}. {exp_text}. {salary_text}. {description}"

        return ScrapedJob(
            source=self.source_name,
            title=title,
            company=company,
            location=location,
            description=full_text,
            url=job_url,
        )
