"""
Mock job generator for production deployments where live scraping is disabled.
Generates realistic job listings based on role requirements data.
"""

import random
from typing import List, Dict, Any
from data.market_data import get_role_requirements

INDIAN_CITIES = ["Bangalore", "Hyderabad", "Pune", "Chennai", "Mumbai", "Delhi NCR", "Noida", "Gurgaon", "Kochi", "Ahmedabad"]

COMPANY_POOL = {
    "engineering": ["Infosys", "TCS", "Wipro", "HCL", "Tech Mahindra", "Capgemini", "Cognizant", "LTIMindtree", "Persistent", "Zoho", "Freshworks", "Razorpay", "PhonePe", "Swiggy", "Zomato", "Ola", "Paytm", "Byju's", "Unacademy", "Meesho", "Dream11", " Zerodha", "Flipkart", "Amazon India", "Google India", "Microsoft India", "Adobe India", "Salesforce India", "VMware India", "Oracle India", "SAP Labs", "Intuit India", "Uber India", "Netflix India"],
    "data": ["Fractal Analytics", "Mu Sigma", "Tiger Analytics", "LatentView", "Absolutdata", "Manthan", "Lymbyc", "Bridgei2i", "EXL Service", "Genpact", "American Express India", "HSBC India", "ICICI Bank", "HDFC Bank", "Reliance Jio", "Airtel", "Tata Digital", "Flipkart", "Amazon India", "Google India"],
    "design": ["Infosys", "Wipro", "TCS", "HCL", "Tech Mahindra", "Zoho", "Freshworks", "Razorpay", "PhonePe", "Swiggy", "Zomato", "Flipkart", "Amazon India", "Google India", "Microsoft India", "Adobe India", "Figma (Remote)", "Cred", "Urban Company", "Lenskart"],
    "management": ["McKinsey India", "BCG India", "Bain India", "Deloitte India", "PwC India", "EY India", "KPMG India", "Accenture Strategy", "ZS Associates", "Avasant", "ISG", "Gartner India", "Forrester India", "Flipkart", "Amazon India", "Google India", "Microsoft India", "Paytm", "PhonePe", "Swiggy"],
    "qa": ["Infosys", "TCS", "Wipro", "HCL", "Capgemini", "Cognizant", "LTIMindtree", "Qualitest", "QA InfoTech", "Cigniti", "TestingXperts", "TestVagrant", "AppSierra", "Zoho", "Freshworks", "Razorpay", "Flipkart", "Amazon India"],
    "default": ["Infosys", "TCS", "Wipro", "HCL", "Tech Mahindra", "Capgemini", "Cognizant", "LTIMindtree", "Zoho", "Freshworks", "Razorpay", "PhonePe", "Swiggy", "Flipkart", "Amazon India"]
}

EXPERIENCE_RANGES = [
    (0, 12),    # 0-1 yr
    (12, 24),   # 1-2 yr
    (24, 36),   # 2-3 yr
    (36, 48),   # 3-4 yr
    (48, 60),   # 4-5 yr
    (0, 0),     # Fresher
]


def _generate_mock_job(role_name: str, location: str, index: int) -> Dict[str, Any]:
    """Generate a single realistic mock job listing."""
    req = get_role_requirements(role_name)
    role_display = role_name.replace("_", " ").title()
    category = req.role_category if req else "default"
    companies = COMPANY_POOL.get(category, COMPANY_POOL["default"])
    company = random.choice(companies)
    city = location if location != "India" else random.choice(INDIAN_CITIES)
    exp_range = random.choice(EXPERIENCE_RANGES)
    
    # Build salary from role data or default
    if req and req.salary_range_lpa:
        min_sal, max_sal = req.salary_range_lpa
        # Adjust based on experience
        if exp_range[1] <= 12:
            salary = (min_sal * 0.8, min_sal * 1.1)
        elif exp_range[1] <= 36:
            salary = (min_sal, max_sal * 0.8)
        else:
            salary = (max_sal * 0.7, max_sal * 1.3)
    else:
        salary = (4.0, 8.0)
    
    # Round salary
    salary = (round(salary[0], 1), round(salary[1], 1))
    
    # Build skills list
    skills = []
    if req:
        skills.extend(req.required_skills[:4])
        skills.extend(req.preferred_skills[:3])
        skills.extend(req.framework_tools[:3])
    if not skills:
        skills = ["python", "javascript", "sql", "git", "docker"]
    skills = list(dict.fromkeys(skills))[:6]  # dedupe and limit
    
    # Build title variants
    title_prefixes = ["", "Senior ", "Junior ", "Associate ", "Lead "]
    title = f"{random.choice(title_prefixes)}{role_display}"
    
    descriptions = [
        f"We are looking for a talented {role_display} to join our growing engineering team. You will work on cutting-edge products serving millions of users.",
        f"Join {company} as a {role_display} and contribute to building scalable systems. Strong problem-solving skills required.",
        f"Exciting opportunity for a {role_display} at {company}. Work with modern tech stack and collaborative team culture.",
        f"{company} is hiring {role_display}s! Build impactful products, mentor junior developers, and shape technical direction.",
        f"Looking for passionate {role_display} to design, develop, and maintain high-performance applications. Remote-friendly.",
    ]
    
    return {
        "source": "mock",
        "title": title,
        "company": company,
        "location": city,
        "description": random.choice(descriptions),
        "url": f"https://careers.{company.lower().replace(' ', '').replace('.', '')}.com/jobs/{index}",
        "skills_found": skills,
        "salary_lpa": salary,
        "experience_months": exp_range,
    }


def generate_mock_jobs(role_name: str, location: str = "India", count: int = 5) -> List[Dict[str, Any]]:
    """Generate realistic mock job listings for any role."""
    random.seed(f"{role_name}:{location}")  # deterministic per role+location
    jobs = []
    for i in range(count):
        jobs.append(_generate_mock_job(role_name, location, i))
    return jobs
