"""
Indeed India Job Scraper
Scrapes Indeed India for real-time JD data.
Source: https://in.indeed.com/jobs
"""

import logging
import urllib.parse
from typing import List, Optional

from bs4 import BeautifulSoup

from .scraper_utils import create_session, respectful_request, ScrapedJob

logger = logging.getLogger(__name__)


class IndeedScraper:
    """Scraper for Indeed India job listings."""

    BASE_URL = "https://in.indeed.com/jobs"

    def __init__(self):
        self.session = create_session()
        self.source_name = "indeed"

    def search_jobs(
        self,
        role: str,
        location: str = "India",
        limit: int = 10
    ) -> List[ScrapedJob]:
        """Search Indeed jobs for a given role and location."""
        jobs = []
        query = urllib.parse.quote_plus(role)
        loc = urllib.parse.quote_plus(location)
        url = f"{self.BASE_URL}?q={query}&l={loc}&fromage=7"

        logger.info(f"[Indeed] Searching: {role} in {location}")
        response = respectful_request(url, self.session, delay_range=(1.5, 3.5))

        if not response:
            logger.warning("[Indeed] Failed to fetch search page.")
            return jobs

        soup = BeautifulSoup(response.text, "lxml")
        job_cards = soup.find_all("div", class_="job_seen_beacon") or soup.find_all("div", class_="slider_container")

        if not job_cards:
            # Try older Indeed markup
            job_cards = soup.find_all("div", class_="result")

        logger.info(f"[Indeed] Found {len(job_cards)} job cards on page.")

        for card in job_cards[:limit]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[Indeed] Failed to parse card: {e}")
                continue

        logger.info(f"[Indeed] Successfully scraped {len(jobs)} jobs.")
        return jobs

    def _parse_job_card(self, card: BeautifulSoup) -> Optional[ScrapedJob]:
        """Parse a single Indeed job card."""
        # Title
        title_tag = card.find("h2", class_="jobTitle") or card.find("a", class_="jcs-JobTitle")
        if not title_tag:
            title_tag = card.find("a", {"data-jk": True})  # Older markup
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Company
        company_tag = card.find("span", class_="companyName") or card.find("span", class_="company")
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"

        # Location
        loc_tag = card.find("div", class_="companyLocation") or card.find("span", class_="location")
        location = loc_tag.get_text(strip=True) if loc_tag else "India"

        # URL
        link_tag = card.find("a", href=True)
        job_url = ""
        if link_tag:
            href = link_tag["href"]
            job_url = f"https://in.indeed.com{href}" if href.startswith("/") else href

        # Summary / Snippet
        snippet_tag = card.find("div", class_="job-snippet") or card.find("div", class_="summary")
        description = snippet_tag.get_text(separator=" ", strip=True) if snippet_tag else f"{title} at {company}."

        # Salary (sometimes shown on card)
        salary_tag = card.find("div", class_="salary-snippet-container") or card.find("span", class_="estimated-salary")
        salary_text = salary_tag.get_text(strip=True) if salary_tag else ""

        return ScrapedJob(
            source=self.source_name,
            title=title,
            company=company,
            location=location,
            description=f"{description} {salary_text}",
            url=job_url,
        )
