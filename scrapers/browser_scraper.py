"""
Stealth Browser Scraper using Playwright + playwright-stealth.

playwright-stealth patches navigator.webdriver, plugins, chrome runtime,
and a dozen other fingerprint signals so Indeed/Glassdoor can't detect headless mode.
"""

import logging
import random
import time
import urllib.parse
from typing import List

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .scraper_utils import ScrapedJob, extract_salary_range, extract_experience

logger = logging.getLogger(__name__)

# Maps role IDs → human-readable search queries for job boards
ROLE_SEARCH_QUERIES = {
    "backend_engineer": "backend developer",
    "frontend_engineer": "frontend developer",
    "fullstack_engineer": "full stack developer",
    "devops_engineer": "devops engineer",
    "site_reliability_engineer": "site reliability engineer SRE",
    "mobile_developer": "mobile developer android ios",
    "data_analyst": "data analyst",
    "data_scientist": "data scientist",
    "data_engineer": "data engineer",
    "ml_engineer": "machine learning engineer",
    "qa_automation": "QA automation engineer",
    "sdet": "software development engineer in test SDET",
    "product_manager": "product manager",
    "ux_designer": "UX designer",
    "ui_designer": "UI designer",
    "devrel": "developer relations engineer",
    "technical_writer": "technical writer",
    "solutions_engineer": "solutions engineer presales",
    "support_engineer": "technical support engineer",
    "business_analyst": "business analyst",
    "project_manager": "project manager IT",
    "software_developer": "software developer",
    "sde": "software development engineer",
    "generative_ai_engineer": "generative AI engineer LLM",
    "nlp_engineer": "NLP engineer",
    "computer_vision_engineer": "computer vision engineer",
    "ai_research_scientist": "AI research scientist",
    "mlops_engineer": "MLOps engineer",
}


def role_to_query(role: str) -> str:
    """Convert a role ID to a job board search query."""
    if role in ROLE_SEARCH_QUERIES:
        return ROLE_SEARCH_QUERIES[role]
    # Fallback: replace underscores with spaces
    return role.replace("_", " ")


# Realistic desktop user-agent pool
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


def _apply_stealth(page):
    """
    Inject stealth JS to mask headless browser signals.
    Uses playwright-stealth if installed; falls back to manual patches.
    """
    try:
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(page)
        return
    except (ImportError, Exception):
        pass

    # Manual fallback: patch the most-checked fingerprint signals
    page.add_init_script("""
        // Remove webdriver flag
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // Fake plugins (headless has 0)
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });

        // Fake languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });

        // Fake chrome runtime
        window.chrome = { runtime: {} };

        // Pass permissions query
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
    """)


def _human_delay(min_ms=600, max_ms=1800):
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


class BrowserScraper:
    """
    Unified stealth browser scraper using Playwright.
    Launches Chromium with anti-detection flags and playwright-stealth patches.
    """

    def __init__(self, headless: bool = True):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        self.context = self.browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            viewport={"width": random.choice([1920, 1440, 1366]), "height": random.choice([1080, 900, 768])},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        logger.info("[BrowserScraper] Stealth Chromium launched")

    def close(self):
        for obj, method, label in [
            (self.context, "close", "context"),
            (self.browser, "close", "browser"),
            (self.playwright, "stop", "playwright"),
        ]:
            try:
                getattr(obj, method)()
            except Exception as e:
                logger.debug(f"[BrowserScraper] {label} close error: {e}")
        logger.info("[BrowserScraper] Browser closed")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
        return False

    def _new_page(self):
        page = self.context.new_page()
        page.set_default_timeout(20000)
        _apply_stealth(page)
        return page

    def scrape_all(self, role: str, location: str = "India", limit_per_source: int = 5) -> List[ScrapedJob]:
        all_jobs = []
        seen = set()

        # Glassdoor uses Cloudflare Bot Management — headless browsers are blocked
        # regardless of stealth. Skip it; focus on Indeed, LinkedIn, Naukri.
        sources = [
            ("indeed", self.scrape_indeed),
            ("linkedin", self.scrape_linkedin),
            ("naukri", self.scrape_naukri),
        ]

        for name, fn in sources:
            try:
                jobs = fn(role, location, limit=limit_per_source)
                logger.info(f"[BrowserScraper] {name}: {len(jobs)} jobs")
                for job in jobs:
                    key = job.url.split("?")[0] if job.url else f"{job.title}|{job.company}"
                    if key and key not in seen:
                        seen.add(key)
                        all_jobs.append(job)
            except Exception as e:
                logger.warning(f"[BrowserScraper] {name} failed: {e}")

        return all_jobs

    # =========================================================================
    # LINKEDIN
    # =========================================================================

    def scrape_linkedin(self, role: str, location: str, limit: int = 5) -> List[ScrapedJob]:
        page = self._new_page()
        jobs = []
        query = urllib.parse.quote_plus(role_to_query(role))
        loc = urllib.parse.quote_plus(location)
        url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc}&f_TPR=r604800&position=1&pageNum=0"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            _human_delay(1200, 2500)
            page.wait_for_selector(
                "[data-view-name='job-card'], .jobs-search__results-list li, .base-card",
                timeout=12000,
            )
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 600)")
                _human_delay(400, 900)

            cards = page.query_selector_all(
                "[data-view-name='job-card'], .jobs-search__results-list > li, .base-card"
            )
            for card in cards[:limit]:
                try:
                    title = _text(card, "h3, .job-card-list__title, .base-search-card__title")
                    company = _text(card, "h4, .job-card-container__company-name, .base-search-card__subtitle")
                    job_loc = _text(card, "[class*='location'], .job-search-card__location") or location
                    exp_text = _text(card, "[class*='experience'], [class*='criteria']")
                    link_el = card.query_selector("a[href*='/jobs/view/'], a[href*='/jobs/collections/'], a[href*='/jobs/']")
                    job_url = link_el.get_attribute("href") if link_el else ""
                    if job_url and job_url.startswith("/"):
                        job_url = f"https://www.linkedin.com{job_url}"
                    if job_url and "?" in job_url:
                        job_url = job_url.split("?")[0]
                    if not title:
                        continue
                    job = ScrapedJob(source="linkedin", title=title, company=company,
                                    location=job_loc, description=f"{title} at {company}.", url=job_url)
                    if exp_text:
                        job.experience_months = extract_experience(exp_text)
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"[LinkedIn] card error: {e}")
        except PlaywrightTimeout:
            logger.warning("[LinkedIn] Timeout")
        except Exception as e:
            logger.warning(f"[LinkedIn] Error: {e}")
        finally:
            page.close()
        return jobs

    # =========================================================================
    # INDEED INDIA  — stealth Playwright replaces the requests-based scraper
    # =========================================================================

    def scrape_indeed(self, role: str, location: str, limit: int = 5) -> List[ScrapedJob]:
        page = self._new_page()
        jobs = []
        query = urllib.parse.quote_plus(role_to_query(role))
        loc = urllib.parse.quote_plus(location)
        url = f"https://in.indeed.com/jobs?q={query}&l={loc}&fromage=14&sort=date"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            _human_delay(2000, 3500)  # let JS hydrate fully

            if "validatecaptcha" in page.url.lower():
                logger.warning("[Indeed] Captcha page detected, skipping")
                return jobs

            # .job_seen_beacon is the full card with title + company + location
            try:
                page.wait_for_selector(".job_seen_beacon", timeout=12000)
            except PlaywrightTimeout:
                logger.warning("[Indeed] No .job_seen_beacon cards within timeout")
                return jobs

            for _ in range(2):
                page.evaluate("window.scrollBy(0, 600)")
                _human_delay(400, 800)

            cards = page.query_selector_all(".job_seen_beacon")
            logger.info(f"[Indeed] Found {len(cards)} cards")

            for card in cards[:limit]:
                try:
                    # Title is in <span title="..."> inside the h2.jobTitle
                    title_el = card.query_selector("h2 a span[title], h2 a span[id^=jobTitle]")
                    title = title_el.get_attribute("title") or title_el.inner_text().strip() if title_el else ""
                    if not title:
                        title = _text(card, "h2 a span, h2 span")

                    company = _text(card, "[data-testid='company-name'], [class*='companyName']")
                    job_loc = _text(card, "[data-testid='text-location'], [class*='companyLocation'], [class*='location']") or location
                    salary_text = _text(card, "[class*='salary'], [class*='estimated-salary']")

                    # Job URL — use data-jk from the anchor to build a clean /viewjob URL
                    link_el = card.query_selector("h2 a[data-jk]")
                    jk = link_el.get_attribute("data-jk") if link_el else ""
                    job_url = f"https://in.indeed.com/viewjob?jk={jk}" if jk else ""

                    if not title:
                        continue

                    job = ScrapedJob(source="indeed", title=title, company=company,
                                    location=job_loc, description=f"{title} at {company}.", url=job_url)
                    if salary_text:
                        job.salary_lpa = extract_salary_range(salary_text)
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Indeed] card error: {e}")

        except PlaywrightTimeout:
            logger.warning("[Indeed] Page load timeout")
        except Exception as e:
            logger.warning(f"[Indeed] Error: {e}")
        finally:
            page.close()

        logger.info(f"[Indeed] Scraped {len(jobs)} jobs")
        return jobs

    # =========================================================================
    # GLASSDOOR INDIA  — stealth Playwright
    # =========================================================================

    def scrape_glassdoor(self, role: str, location: str, limit: int = 5) -> List[ScrapedJob]:
        page = self._new_page()
        jobs = []

        # Glassdoor's URL structure: /Job/<location>-<role>-jobs-SRCH_...
        loc_slug = location.lower().replace(" ", "-")
        role_slug = role_to_query(role).lower().replace(" ", "-")
        url = (
            f"https://www.glassdoor.co.in/Job/{loc_slug}-{role_slug}-jobs-SRCH_IL.0,"
            f"{len(loc_slug)}_IN115_KO{len(loc_slug)+1},{len(loc_slug)+1+len(role_slug)}.htm"
        )
        # Simpler fallback URL that always works
        query = urllib.parse.quote_plus(role_to_query(role))
        loc_q = urllib.parse.quote_plus(location)
        fallback_url = f"https://www.glassdoor.co.in/Search/results.htm?keyword={query}&locT=N&locId=115"

        try:
            page.goto(fallback_url, wait_until="domcontentloaded", timeout=25000)
            _human_delay(2000, 4000)  # Glassdoor is slowest to hydrate

            # Glassdoor often shows a login wall — check for it
            if "glassdoor" not in page.url or page.query_selector("[data-test='LoginModal']"):
                logger.warning("[Glassdoor] Login modal detected, trying job search URL")
                page.goto(
                    f"https://www.glassdoor.co.in/Job/india-{role_slug}-jobs-SRCH_IL.0,5_IN115.htm",
                    wait_until="domcontentloaded", timeout=25000
                )
                _human_delay(2000, 3500)

            try:
                page.wait_for_selector(
                    "[data-test='jobListing'], li[data-id], .JobsList_jobListItem__wjTHv, [class*='jobListItem']",
                    timeout=12000,
                )
            except PlaywrightTimeout:
                logger.warning("[Glassdoor] Job cards not found within timeout")
                return jobs

            for _ in range(3):
                page.evaluate("window.scrollBy(0, 600)")
                _human_delay(400, 900)

            cards = page.query_selector_all("[data-test='jobListing'], li[data-id], .JobsList_jobListItem__wjTHv")
            if not cards:
                cards = page.query_selector_all("[class*='jobListItem'], [class*='JobCard']")

            logger.info(f"[Glassdoor] Found {len(cards)} raw cards")

            for card in cards[:limit]:
                try:
                    title = _text(card, "[data-test='job-title'], a.jobTitle, [class*='jobTitle']")
                    company = _text(card, "[data-test='employer-name'], [class*='employer'], [class*='companyName']")
                    job_loc = _text(card, "[data-test='emp-location'], [class*='location']") or location
                    salary_text = _text(card, "[data-test='detailSalary'], [class*='salary']")

                    job_url = ""
                    link = card.query_selector("a[href*='/job-listing/'], a[data-test='job-title'], a[href*='/Job/']")
                    if link:
                        href = link.get_attribute("href") or ""
                        job_url = f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href

                    if not title:
                        continue

                    job = ScrapedJob(source="glassdoor", title=title, company=company,
                                    location=job_loc, description=f"{title}. {salary_text}.", url=job_url)
                    if salary_text:
                        job.salary_lpa = extract_salary_range(salary_text)
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Glassdoor] card error: {e}")

        except PlaywrightTimeout:
            logger.warning("[Glassdoor] Page load timeout")
        except Exception as e:
            logger.warning(f"[Glassdoor] Error: {e}")
        finally:
            page.close()

        logger.info(f"[Glassdoor] Scraped {len(jobs)} jobs")
        return jobs

    # =========================================================================
    # NAUKRI
    # =========================================================================

    def scrape_naukri(self, role: str, location: str, limit: int = 5) -> List[ScrapedJob]:
        page = self._new_page()
        jobs = []
        query = role.lower().strip().replace(" ", "-").replace("_", "-")
        loc = location.lower().strip().replace(" ", "-")
        url = f"https://www.naukri.com/{query}-jobs-in-{loc}"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            _human_delay(800, 1800)
            page.wait_for_selector(
                ".srp-jobtuple-wrapper, article.jobTuple, [class*='jobTuple']",
                timeout=12000,
            )
            for _ in range(2):
                page.evaluate("window.scrollBy(0, 800)")
                _human_delay(400, 800)

            cards = page.query_selector_all(".srp-jobtuple-wrapper, article.jobTuple")
            for card in cards[:limit]:
                try:
                    title = _text(card, "a.title, a.jobTupleTitle, [class*='title']")
                    company = _text(card, "a.comp-name, [class*='company']")
                    job_loc = _text(card, "span.locWdth, [class*='location']") or location
                    exp_text = _text(card, "span.expwdth, [class*='experience']")
                    salary_text = _text(card, "span[class*='salary']")
                    link = card.query_selector("a.title, a.jobTupleTitle")
                    job_url = ""
                    if link:
                        href = link.get_attribute("href") or ""
                        job_url = href if href.startswith("http") else f"https://www.naukri.com{href}"
                    if not title:
                        continue
                    job = ScrapedJob(source="naukri", title=title, company=company,
                                    location=job_loc, description=f"{title}. {exp_text}.", url=job_url)
                    if salary_text:
                        job.salary_lpa = extract_salary_range(salary_text)
                    if exp_text:
                        job.experience_months = extract_experience(exp_text)
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Naukri] card error: {e}")
        except PlaywrightTimeout:
            logger.warning("[Naukri] Timeout")
        except Exception as e:
            logger.warning(f"[Naukri] Error: {e}")
        finally:
            page.close()
        return jobs


# ---------------------------------------------------------------------------
# Helper — safe inner text extraction for Playwright elements
# ---------------------------------------------------------------------------

def _text(element, selector: str) -> str:
    """Try each comma-separated CSS selector and return the first non-empty text."""
    for sel in selector.split(","):
        sel = sel.strip()
        try:
            el = element.query_selector(sel)
            if el:
                txt = el.inner_text().strip()
                if txt:
                    return txt
        except Exception:
            continue
    return ""
