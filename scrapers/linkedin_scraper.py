"""
LinkedIn Job Scraper
Scrapes public job search pages for real-time JD data.
Source: https://www.linkedin.com/jobs/search
"""

import logging
import urllib.parse
from typing import List, Optional

from bs4 import BeautifulSoup

from .scraper_utils import create_session, respectful_request, ScrapedJob

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """
    Scraper for LinkedIn public job listings.
    Respects robots.txt and uses polite request pacing.
    """

    BASE_URL = "https://www.linkedin.com/jobs/search"

    def __init__(self):
        self.session = create_session()
        self.source_name = "linkedin"

    def search_jobs(
        self,
        role: str,
        location: str = "India",
        limit: int = 10
    ) -> List[ScrapedJob]:
        """
        Search LinkedIn jobs for a given role and location.
        Returns up to `limit` ScrapedJob objects.
        """
        jobs = []
        query = urllib.parse.quote_plus(role)
        loc = urllib.parse.quote_plus(location)
        url = f"{self.BASE_URL}?keywords={query}&location={loc}&f_TPR=r604800"

        logger.info(f"[LinkedIn] Searching: {role} in {location}")
        response = respectful_request(url, self.session, delay_range=(2.0, 4.0))

        if not response:
            logger.warning("[LinkedIn] Failed to fetch search page.")
            return jobs

        soup = BeautifulSoup(response.text, "lxml")

        # LinkedIn job cards structure
        job_cards = soup.find_all("div", class_="base-search-card__info")
        if not job_cards:
            # Fallback: try alternative selectors
            job_cards = soup.find_all("div", class_="job-search-card")

        logger.info(f"[LinkedIn] Found {len(job_cards)} job cards on page.")

        for card in job_cards[:limit]:
            try:
                job = self._parse_job_card(card, soup)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[LinkedIn] Failed to parse card: {e}")
                continue

        logger.info(f"[LinkedIn] Successfully scraped {len(jobs)} jobs.")
        return jobs

    def _parse_job_card(self, card: BeautifulSoup, page_soup: BeautifulSoup) -> Optional[ScrapedJob]:
        """Parse a single LinkedIn job card."""
        # Title
        title_tag = card.find("h3", class_="base-search-card__title") or card.find("a", class_="job-card-list__title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Company
        company_tag = card.find("h4", class_="base-search-card__subtitle") or card.find("a", class_="job-card-container__company-name")
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"

        # Location
        loc_tag = card.find("span", class_="job-search-card__location") or card.find("span", class_="job-card-container__metadata-item")
        location = loc_tag.get_text(strip=True) if loc_tag else "India"

        # Job URL — prefer the full-link wrapper, then any /jobs/view/ URL, avoid company pages
        job_url = ""
        link_tag = card.find("a", class_="base-card__full-link") or card.find_parent("a", class_="base-card__full-link")
        if link_tag and link_tag.get("href"):
            job_url = link_tag["href"]
        if not job_url or "/company/" in job_url:
            # Scan all anchors for a direct job listing URL
            for a_tag in card.find_all("a", href=True):
                href = a_tag["href"]
                if "/jobs/view/" in href or "/jobs/collections/" in href:
                    job_url = href
                    break
        # Strip tracking params to get a clean URL
        if job_url and "?" in job_url:
            job_url = job_url.split("?")[0]

        # Description - LinkedIn hides full description on search page;
        # we extract whatever summary is available
        desc_tag = card.find("p", class_="job-search-card__description") or card.find("div", class_="base-search-card__metadata")
        description = desc_tag.get_text(strip=True) if desc_tag else f"{title} at {company}. {location}."

        return ScrapedJob(
            source=self.source_name,
            title=title,
            company=company,
            location=location,
            description=description,
            url=job_url,
        )

    def get_job_description(self, job_url: str) -> Optional[str]:
        """
        Fetch full job description from a LinkedIn job detail page.
        Returns raw description text or None.
        """
        if not job_url:
            return None

        response = respectful_request(job_url, self.session, delay_range=(2.0, 4.0))
        if not response:
            return None

        soup = BeautifulSoup(response.text, "lxml")
        desc_div = soup.find("div", class_="description__text") or soup.find("div", class_="show-more-less-html__markup")
        if desc_div:
            return desc_div.get_text(separator=" ", strip=True)

        return None
