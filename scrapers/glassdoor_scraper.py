"""
Glassdoor India Job Scraper
Scrapes Glassdoor India for salary and JD data.
Source: https://www.glassdoor.co.in/Job/
"""

import logging
import re
import urllib.parse
from typing import List, Optional

from bs4 import BeautifulSoup

from .scraper_utils import create_session, respectful_request, ScrapedJob

logger = logging.getLogger(__name__)


class GlassdoorScraper:
    """
    Scraper for Glassdoor India job listings.
    Glassdoor is the most aggressive at blocking scrapers, so this has extra fallback logic.
    """

    BASE_URL = "https://www.glassdoor.co.in/Job/"

    def __init__(self):
        self.session = create_session()
        self.source_name = "glassdoor"

    def search_jobs(
        self,
        role: str,
        location: str = "India",
        limit: int = 10
    ) -> List[ScrapedJob]:
        """Search Glassdoor jobs for a given role and location."""
        jobs = []
        query = urllib.parse.quote_plus(role)
        loc = urllib.parse.quote_plus(location)
        url = f"{self.BASE_URL}{loc}-{role}-jobs-SRCH_IL.0,6_IN115_KO7,{len(role)}.htm"

        logger.info(f"[Glassdoor] Searching: {role} in {location}")
        response = respectful_request(url, self.session, delay_range=(3.0, 5.0))

        if not response:
            logger.warning("[Glassdoor] Failed to fetch search page (common due to anti-bot).")
            return jobs

        soup = BeautifulSoup(response.text, "lxml")

        # Glassdoor job cards
        job_cards = soup.find_all("li", class_="JobsList_jobListItem__JBBUV")
        if not job_cards:
            job_cards = soup.find_all("div", class_="jobContainer")
        if not job_cards:
            job_cards = soup.find_all("li", {"data-test": re.compile(r"jobListing")})

        logger.info(f"[Glassdoor] Found {len(job_cards)} job cards on page.")

        for card in job_cards[:limit]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[Glassdoor] Failed to parse card: {e}")
                continue

        logger.info(f"[Glassdoor] Successfully scraped {len(jobs)} jobs.")
        return jobs

    def _parse_job_card(self, card: BeautifulSoup) -> Optional[ScrapedJob]:
        """Parse a single Glassdoor job card."""
        # Title
        title_tag = card.find("a", class_="jobTitle") or card.find("a", {"data-test": "job-title"})
        if not title_tag:
            title_tag = card.find("a", class_="JobCard_jobTitle___7I6y")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Company
        company_tag = card.find("span", class_="EmployerProfile_compactEmployerName__LE242") or card.find("div", class_="jobInfoItem")
        if not company_tag:
            company_tag = card.find("span", class_="JobCard_companyName__N1YrF")
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"

        # Location
        loc_tag = card.find("span", class_="JobCard_location__rCz3x") or card.find("span", {"data-test": "emp-location"})
        location = loc_tag.get_text(strip=True) if loc_tag else "India"

        # URL
        job_url = ""
        if title_tag and title_tag.get("href"):
            href = title_tag["href"]
            job_url = f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href

        # Salary (Glassdoor often shows estimated salary on card)
        salary_tag = card.find("span", class_="JobCard_salaryEstimate__arV5C") or card.find("span", {"data-test": "detailSalary"})
        salary_text = salary_tag.get_text(strip=True) if salary_tag else ""

        # Description snippet
        desc_tag = card.find("div", class_="JobCard_jobDescriptionSnippet__yWW8q")
        description = desc_tag.get_text(separator=" ", strip=True) if desc_tag else f"{title} at {company}."

        full_text = f"{title}. {salary_text}. {description}"

        return ScrapedJob(
            source=self.source_name,
            title=title,
            company=company,
            location=location,
            description=full_text,
            url=job_url,
        )
