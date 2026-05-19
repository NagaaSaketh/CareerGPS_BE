"""
Shared utilities for all JD scrapers.
Handles headers, retry logic, rate limiting, skill extraction, and salary parsing.
"""

import re
import time
import random
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# =============================================================================
# HTTP SESSION WITH RETRY LOGIC
# =============================================================================

def create_session(
    retries: int = 3,
    backoff_factor: float = 1.5,
    timeout: int = 15
) -> requests.Session:
    """Create a requests session with automatic retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=5, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.timeout = timeout
    return session


# Rotating user agents to reduce blocking risk
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

def get_headers() -> Dict[str, str]:
    """Return randomized request headers."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def respectful_request(
    url: str,
    session: requests.Session,
    delay_range: Tuple[float, float] = (1.5, 3.5),
    **kwargs
) -> Optional[requests.Response]:
    """
    Make a respectful HTTP request with rate limiting and error handling.
    Returns None if the request fails after all retries.
    """
    # Respectful delay between requests
    time.sleep(random.uniform(*delay_range))

    headers = get_headers()
    headers.update(kwargs.pop("headers", {}))

    try:
        response = session.get(url, headers=headers, timeout=15, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        if response.status_code == 403:
            logger.warning(f"Access denied (403) for {url}. Site may be blocking scrapers.")
        elif response.status_code == 429:
            logger.warning(f"Rate limited (429) for {url}. Backing off.")
        else:
            logger.warning(f"HTTP error {response.status_code} for {url}: {e}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed for {url}: {e}")

    return None


# =============================================================================
# SKILL EXTRACTION ENGINE
# =============================================================================

# Comprehensive skill taxonomy extracted from real JDs
SKILL_KEYWORDS = {
    # Programming Languages
    "python": ["python", "python3"],
    "java": ["java", "core java", "java 8", "java 11", "java 17"],
    "javascript": ["javascript", "js", "es6", "es2020"],
    "typescript": ["typescript", "ts"],
    "go": ["go", "golang"],
    "c++": ["c++", "cpp", "c plus plus"],
    "c#": ["c#", "csharp", ".net"],
    "rust": ["rust"],
    "ruby": ["ruby"],
    "php": ["php"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "scala": ["scala"],
    "r": [" r ", " r,"],
    "sql": ["sql", "mysql", "postgresql", "oracle"],
    "nosql": ["nosql", "mongodb", "cassandra", "dynamodb", "couchbase"],

    # Web/Frameworks
    "react": ["react", "reactjs", "react.js"],
    "angular": ["angular", "angularjs", "angular 2+"],
    "vue": ["vue", "vuejs", "vue.js"],
    "nextjs": ["next.js", "nextjs"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi", "fast api"],
    "spring_boot": ["spring boot", "springboot"],
    "express": ["express", "expressjs"],
    "nodejs": ["nodejs", "node.js", "node js"],
    "nestjs": ["nestjs", "nest.js"],
    "rails": ["rails", "ruby on rails"],
    "laravel": ["laravel"],
    ".net": [".net", ".net core", "asp.net"],

    # Data & ML
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch", "torch"],
    "scikit_learn": ["scikit-learn", "sklearn"],
    "keras": ["keras"],
    "spark": ["spark", "apache spark", "pyspark"],
    "hadoop": ["hadoop"],
    "kafka": ["kafka", "apache kafka"],
    "airflow": ["airflow", "apache airflow"],
    "dbt": ["dbt"],
    "snowflake": ["snowflake"],
    "tableau": ["tableau"],
    "power_bi": ["power bi", "powerbi"],

    # DevOps / Cloud
    "docker": ["docker", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "terraform": ["terraform", "iac"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins", "ci/cd"],
    "github_actions": ["github actions"],
    "gitlab_ci": ["gitlab ci"],
    "prometheus": ["prometheus"],
    "grafana": ["grafana"],
    "helm": ["helm"],
    "argo": ["argo", "argocd"],

    # Databases
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"],
    "rabbitmq": ["rabbitmq"],

    # Testing / QA
    "selenium": ["selenium"],
    "cypress": ["cypress"],
    "jest": ["jest"],
    "pytest": ["pytest"],
    "junit": ["junit"],
    "postman": ["postman"],
    "jmeter": ["jmeter"],
    "cucumber": ["cucumber", "bdd"],

    # Mobile
    "flutter": ["flutter"],
    "react_native": ["react native"],
    "android": ["android", "android sdk"],
    "ios": ["ios", "swift ui"],

    # Design
    "figma": ["figma"],
    "sketch": ["sketch"],
    "adobe_xd": ["adobe xd", "xd"],
    "prototyping": ["prototyping", "wireframing"],
    "user_research": ["user research", "usability testing"],

    # Product / Business
    "jira": ["jira", "confluence"],
    "agile": ["agile", "scrum", "kanban"],
    "product_strategy": ["product strategy", "roadmapping"],
    "data_analysis": ["data analysis", "data analytics"],
    "a_b_testing": ["a/b testing", "ab testing"],
    "sql_advanced": ["advanced sql", "window functions", "cte"],

    # Soft / Cross-functional
    "communication": ["communication", "written communication"],
    "leadership": ["leadership", "team lead"],
    "problem_solving": ["problem solving", "analytical thinking"],
}


def normalize_skills(text: str) -> List[str]:
    """
    Extract normalized skills from a job description text.
    Returns a deduplicated list of skill slugs.
    """
    text_lower = text.lower()
    found_skills = set()

    for skill_slug, keywords in SKILL_KEYWORDS.items():
        for kw in keywords:
            # Use word boundaries for short keywords to avoid false matches
            if len(kw) <= 3:
                pattern = r'\b' + re.escape(kw) + r'\b'
            else:
                pattern = re.escape(kw)
            if re.search(pattern, text_lower):
                found_skills.add(skill_slug)
                break

    return sorted(list(found_skills))


# =============================================================================
# SALARY EXTRACTION
# =============================================================================

# Indian salary patterns in JDs
SALARY_PATTERNS = [
    # "₹5,00,000 - ₹8,00,000 a year"
    re.compile(r'[₹Rs\.\s]*([\d,]+)\s*[-–to]+\s*[₹Rs\.\s]*([\d,]+)\s*(?:a year|per year|annum|pa)', re.IGNORECASE),
    # "5-8 LPA"
    re.compile(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*LPA', re.IGNORECASE),
    # "₹5.0L - ₹8.0L"
    re.compile(r'[₹Rs\.\s]*(\d+(?:\.\d+)?)\s*L\s*[-–]\s*[₹Rs\.\s]*(\d+(?:\.\d+)?)\s*L', re.IGNORECASE),
    # "500000 - 800000"
    re.compile(r'(\d{5,7})\s*[-–]\s*(\d{5,7})'),
]


def extract_salary_range(text: str) -> Optional[Tuple[float, float]]:
    """
    Extract salary range (min, max) in LPA from JD text.
    Returns None if no salary found.
    """
    for pattern in SALARY_PATTERNS:
        match = pattern.search(text)
        if match:
            raw_min = match.group(1).replace(",", "")
            raw_max = match.group(2).replace(",", "")

            try:
                min_val = float(raw_min)
                max_val = float(raw_max)

                # Normalize to LPA
                if min_val > 10000:  # Likely in INR (e.g., 500000)
                    min_val = round(min_val / 100000, 2)
                    max_val = round(max_val / 100000, 2)
                # If already in LPA (e.g., 5.5), keep as-is

                if min_val < max_val:
                    return (min_val, max_val)
            except ValueError:
                continue

    return None


# =============================================================================
# EXPERIENCE EXTRACTION
# =============================================================================

# Match "year", "years", "yr", "yrs" — common on Indian job boards like Naukri
_YR_RE = r'(?:years?|yrs?)'

EXPERIENCE_PATTERNS = [
    # "3-6 years", "3 - 6 yrs", "3–6 Yrs"
    re.compile(rf'(\d+)\s*[-–]\s*(\d+)\s*{_YR_RE}', re.IGNORECASE),
    # "3+ years experience", "3 years of experience", "3 yrs exp"
    re.compile(rf'(\d+)\+?\s*{_YR_RE}\s*(?:of\s*)?(?:experience|exp)?', re.IGNORECASE),
    # "minimum 3 years"
    re.compile(rf'minimum\s*(\d+)\s*{_YR_RE}', re.IGNORECASE),
    # "at least 3 years"
    re.compile(rf'at least\s*(\d+)\s*{_YR_RE}', re.IGNORECASE),
    # "3+ years" without "experience" word
    re.compile(rf'(\d+)\+\s*{_YR_RE}', re.IGNORECASE),
    # Fresher patterns: "freshers", "entry level", "0-1 year", "0 - 1 yrs"
    re.compile(rf'(?:freshers?|entry level|0\s*[-–]\s*1\s*{_YR_RE})', re.IGNORECASE),
]


def extract_experience(text: str) -> Tuple[int, int]:
    """
    Extract (min_months, max_months) experience requirement from JD text.
    Returns (0, 0) if not found.
    """
    text_lower = text.lower()

    # Check for fresher-friendly language (broad match)
    fresher_kw = [
        "fresher", "freshers", "entry level", "0-1 year", "0 - 1 year",
        "0-1 yr", "0 - 1 yr", "0-1 yrs", "0 - 1 yrs",
        "no experience required", "no exp required", "0 years",
    ]
    if any(kw in text_lower for kw in fresher_kw):
        return (0, 12)

    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            # Fresher pattern has 0 capture groups (non-capturing group only)
            if len(groups) == 0 or (len(groups) == 1 and groups[0] is None):
                return (0, 12)
            if len(groups) >= 2 and groups[1] is not None:
                try:
                    min_years = int(groups[0])
                    max_years = int(groups[1])
                    return (min_years * 12, max_years * 12)
                except ValueError:
                    continue
            elif len(groups) >= 1 and groups[0] is not None:
                try:
                    years = int(groups[0])
                    return (years * 12, (years + 2) * 12)
                except ValueError:
                    continue

    return (0, 0)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ScrapedJob:
    """Normalized representation of a scraped job posting."""
    source: str  # 'linkedin', 'indeed', 'glassdoor', 'naukri'
    title: str
    company: str
    location: str
    description: str
    url: str
    skills_found: List[str] = field(default_factory=list)
    salary_lpa: Optional[Tuple[float, float]] = None
    experience_months: Tuple[int, int] = field(default=(0, 0))
    posted_date: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if not self.skills_found and self.description:
            self.skills_found = normalize_skills(self.description)
        if not self.salary_lpa and self.description:
            self.salary_lpa = extract_salary_range(self.description)
        if self.experience_months == (0, 0) and self.description:
            self.experience_months = extract_experience(self.description)
