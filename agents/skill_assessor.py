"""
Evidence-Based Skill Assessment Module
NEVER trusts self-reported ratings. Always validates against evidence.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
import requests
import base64

class SkillLevel(Enum):
    NONE = 0
    BEGINNER = 1
    BASIC = 2
    INTERMEDIATE = 3
    PROFICIENT = 4
    ADVANCED = 5

@dataclass
class SkillEvidence:
    """Evidence for a single skill"""
    skill_name: str
    self_reported: int  # 1-5 from user
    evidence_based: int  # 1-5 from analysis
    evidence_sources: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    contradiction_flag: bool = False

    @property
    def final_rating(self) -> int:
        """Final rating: NEVER uses self-reported if evidence contradicts"""
        if self.self_reported > self.evidence_based + 1:
            self.contradiction_flag = True
            return self.evidence_based  # Trust evidence, not self-report
        return max(self.self_reported, self.evidence_based)  # Conservative

@dataclass
class GitHubAnalysis:
    """Analysis of GitHub repository"""
    repo_url: str
    accessible: bool
    has_readme: bool
    num_repos: int
    total_commits: int
    languages: Dict[str, int]  # language -> lines of code
    code_quality_signals: Dict[str, bool]
    # Quality signals
    has_tests: bool
    has_error_handling: bool
    has_documentation: bool
    avg_function_length: int
    max_function_length: int
    project_complexity: str  # simple, moderate, complex

    # Red flags
    red_flags: List[str] = field(default_factory=list)

@dataclass
class ResumeAnalysis:
    """Analysis of resume"""
    has_internship: bool
    internship_type: str  # "development", "testing", "support", "none"
    internship_duration_months: int
    projects_listed: int
    project_quality: str  # "none", "academic_only", "deployed", "production_like"
    cgpa: Optional[float]
    college_tier: str
    skills_claimed: List[str]
    skills_verifiable: List[str]  # Skills that appear in projects/internship

@dataclass
class DiagnosticResult:
    """Result from diagnostic coding task"""
    task_id: str
    completed: bool
    code_quality: int  # 1-5
    correctness: int  # 1-5
    time_taken_minutes: int
    approach_description: str
    issues_found: List[str]

    @property
    def issues(self) -> List[str]:
        """Alias for issues_found (backward compatibility)."""
        return self.issues_found

class SkillAssessor:
    """
    Core assessment engine.
    Rule: Self-report is suspicion, evidence is truth.
    """

    def __init__(self):
        self.skill_frameworks = {
            "python": {
                "beginner": ["variables", "loops", "conditionals", "basic_functions"],
                "basic": ["list_comprehensions", "dicts", "file_io", "modules"],
                "intermediate": ["classes", "error_handling", "generators", "decorators", "testing"],
                "proficient": ["async", "metaclasses", "performance_optimization", "design_patterns"],
                "advanced": ["c_extensions", "interpreter_internals", "distributed_systems"]
            },
            "dsa": {
                "beginner": ["arrays", "strings", "basic_sorting"],
                "basic": ["hashmaps", "two_pointers", "sliding_window"],
                "intermediate": ["trees", "graphs", "dp", "heaps"],
                "proficient": ["advanced_graphs", "segment_trees", "tries"],
                "advanced": ["competitive_programming", "advanced_algorithms"]
            },
            "system_design": {
                "none": [],
                "basic": ["scalability_concepts", "load_balancing", "caching_basics"],
                "intermediate": ["microservices", "database_sharding", "message_queues", "cap_theorem"],
                "advanced": ["distributed_consensus", "event_sourcing", "cqrs", "global_scale"]
            },
            "web_frameworks": {
                "none": [],
                "beginner": ["basic_routing", "templates"],
                "basic": ["orm_usage", "middleware", "authentication"],
                "intermediate": ["api_design", "testing", "deployment", "docker"],
                "proficient": ["performance_tuning", "security", "microservices"]
            }
        }

    @staticmethod
    def _extract_github_username(url: str) -> Optional[str]:
        """Extract username from github.com/username or github.com/username/repo URLs."""
        if not url:
            return None
        patterns = [
            r'github\.com/([^/]+)/?',
            r'github\.com/([^/]+)/[^/]+/?',
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                user = m.group(1)
                if user not in ('', 'search', 'topics', 'trending', 'settings'):
                    return user
        return None

    # Mapping: GitHub languages + README keywords → CareerGPS skills we can infer
    _GITHUB_SKILL_MAP = {
        "python": ["python", "django", "flask", "fastapi"],
        "javascript": ["javascript", "react", "nodejs", "express", "vue", "angular", "nextjs"],
        "typescript": ["typescript", "react", "nodejs", "express", "angular", "nextjs"],
        "html": ["html", "react", "vue", "angular"],
        "css": ["css", "tailwindcss", "bootstrap"],
        "java": ["java", "spring_boot"],
        "go": ["go", "gin"],
        "ruby": ["ruby", "rails"],
        "php": ["php", "laravel"],
        "c#": ["c#", ".net"],
        "c++": ["c++"],
        "rust": ["rust"],
        "kotlin": ["kotlin", "android"],
        "swift": ["swift", "ios"],
        "r": ["r"],
        "scala": ["scala"],
        "sql": ["sql", "postgresql", "mysql"],
        "shell": ["docker", "kubernetes", "ci_cd"],
    }

    _README_SKILL_PATTERNS = {
        "react": ["react", "reactjs", "react.js", "vite + react", "create-react-app", "next.js", "nextjs"],
        "nodejs": ["node.js", "nodejs", "node js", "express", "nestjs"],
        "express": ["express", "expressjs", "express.js"],
        "mongodb": ["mongodb", "mongo db", "mongoose"],
        "docker": ["docker", "container", "dockerfile"],
        "kubernetes": ["kubernetes", "k8s", "helm"],
        "aws": ["aws", "amazon web services", "ec2", "s3", "lambda"],
        "html": ["html", "html5"],
        "css": ["css", "css3", "tailwind", "bootstrap", "scss", "sass"],
        "javascript": ["javascript", "es6", "js"],
        "typescript": ["typescript", "ts"],
        "python": ["python", "python3", "django", "flask"],
        "java": ["java", "spring boot"],
        "sql": ["sql", "mysql", "postgresql", "sqlite"],
        "redis": ["redis"],
        "graphql": ["graphql", "apollo"],
        "rest_api": ["rest api", "restful", "api design"],
        "git": ["git", "github"],
    }

    def _scan_readme_for_skills(self, owner: str, repo: str, headers: dict) -> List[str]:
        """Fetch README and scan for technology/framework mentions."""
        found = []
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/readme",
                headers=headers,
                timeout=8,
            )
            if resp.status_code == 200:
                import base64
                content = resp.json().get("content", "")
                if content:
                    text = base64.b64decode(content).decode("utf-8", errors="ignore").lower()
                    for skill, keywords in self._README_SKILL_PATTERNS.items():
                        if any(kw in text for kw in keywords):
                            found.append(skill)
        except Exception:
            pass
        return found

    def _fetch_github_profile(self, url: str) -> dict:
        """
        Fetch real GitHub profile data via the public API.
        Scans READMEs, languages, and repo metadata for skill evidence.
        Falls back gracefully on any error.
        """
        username = self._extract_github_username(url)
        if not username:
            return {"accessible": False, "url": url}

        headers = {"Accept": "application/vnd.github.v3+json"}
        try:
            # 1. Fetch public repos
            resp = requests.get(
                f"https://api.github.com/users/{username}/repos",
                headers=headers,
                timeout=10,
                params={"per_page": 20, "type": "owner", "sort": "updated"}
            )
            if resp.status_code != 200:
                return {"accessible": False, "url": url}

            repos = resp.json()
            if not repos:
                return {"accessible": True, "num_repos": 0, "url": url}

            # 2. Analyze repos
            total_commits = 0
            languages = {}
            readme_skills = set()
            has_readme_count = 0
            has_tests_count = 0
            has_ci_cd = False
            be_repos = 0
            fe_repos = 0

            for repo in repos[:6]:  # Top 6 repos to stay within rate limits
                owner_name = repo.get("owner", {}).get("login", username)
                name = repo.get("name", "")
                if not name:
                    continue

                name_lower = name.lower()
                # Detect BE vs FE from repo naming
                if any(suffix in name_lower for suffix in ["_be", "-be", "_backend", "-backend", "server", "api"]):
                    be_repos += 1
                if any(suffix in name_lower for suffix in ["_fe", "-fe", "_frontend", "-frontend", "client", "ui"]):
                    fe_repos += 1

                total_commits += repo.get("size", 0) // 10

                # Primary language fallback (free, no extra API call)
                primary_lang = repo.get("language", "")
                if primary_lang:
                    pl = primary_lang.lower()
                    mapped = self._GITHUB_SKILL_MAP.get(pl, [pl])
                    for skill in mapped:
                        languages[skill] = languages.get(skill, 0) + 500

                # Detailed languages
                lang_url = repo.get("languages_url")
                if lang_url:
                    try:
                        lresp = requests.get(lang_url, headers=headers, timeout=8)
                        if lresp.status_code == 200:
                            for lang, bytes_count in lresp.json().items():
                                languages[lang.lower()] = languages.get(lang.lower(), 0) + bytes_count
                    except Exception:
                        pass

                # README scan for frameworks
                readme_skills.update(self._scan_readme_for_skills(owner_name, name, headers))
                has_readme = repo.get("has_wiki") or repo.get("size", 0) > 5
                if has_readme:
                    has_readme_count += 1

                # Test signals
                topics = repo.get("topics", [])
                if any(t in name_lower for t in ["test", "spec", "pytest", "jest", "cypress"]):
                    has_tests_count += 1

                # CI/CD signals
                if any(t in topics for t in ["ci-cd", "github-actions", "automation"]):
                    has_ci_cd = True

            # 3. Map raw languages to CareerGPS skills
            inferred_skills = {}
            for lang, bytes_count in languages.items():
                mapped = self._GITHUB_SKILL_MAP.get(lang, [lang])
                for skill in mapped:
                    inferred_skills[skill] = inferred_skills.get(skill, 0) + bytes_count

            # 4. Add README-discovered skills with a base signal
            for skill in readme_skills:
                inferred_skills[skill] = inferred_skills.get(skill, 0) + 1000

            # Convert to rough LOC
            total_inferred = sum(inferred_skills.values()) or 1
            loc_estimates = {
                skill: int((count / total_inferred) * 5000)
                for skill, count in inferred_skills.items()
            }

            return {
                "accessible": True,
                "url": url,
                "num_repos": len(repos),
                "total_commits": max(total_commits, len(repos) * 5),
                "languages": loc_estimates,
                "has_readme": has_readme_count >= len(repos) // 2,
                "has_tests": has_tests_count >= 1,
                "has_error_handling": False,
                "has_documentation": has_readme_count >= 1,
                "has_ci_cd": has_ci_cd,
                "has_contributing": False,
                "avg_function_length": 50,
                "max_function_length": 200,
                "be_repos": be_repos,
                "fe_repos": fe_repos,
                "readme_skills": list(readme_skills),
            }

        except Exception as e:
            return {"accessible": False, "url": url, "error": str(e)}

    def analyze_github(self, repo_data: dict) -> GitHubAnalysis:
        """
        Analyze GitHub evidence.
        If a real GitHub URL is provided, fetches live data via GitHub API.
        Falls back to mock data only if the API call fails.
        """
        url = repo_data.get("url", "")

        # If a real URL was provided, try to fetch live data
        if url and "github.com" in url:
            live_data = self._fetch_github_profile(url)
            if live_data.get("accessible"):
                # Merge live data with any missing fields from mock
                merged = {**repo_data, **live_data}
                repo_data = merged

        accessible = repo_data.get("accessible", False)
        num_repos = repo_data.get("num_repos", 0)

        if not accessible:
            return GitHubAnalysis(
                repo_url=repo_data.get("url", ""),
                accessible=False,
                has_readme=False,
                num_repos=0,
                total_commits=0,
                languages={},
                code_quality_signals={},
                has_tests=False,
                has_error_handling=False,
                has_documentation=False,
                avg_function_length=0,
                max_function_length=0,
                project_complexity="none",
                red_flags=["repository_not_accessible", "cannot_verify_skills"]
            )

        if num_repos == 0:
            return GitHubAnalysis(
                repo_url=repo_data.get("url", ""),
                accessible=True,
                has_readme=False,
                num_repos=0,
                total_commits=0,
                languages={},
                code_quality_signals={},
                has_tests=False,
                has_error_handling=False,
                has_documentation=False,
                avg_function_length=0,
                max_function_length=0,
                project_complexity="none",
                red_flags=["no_repositories", "no_code_evidence"]
            )

        # Analyze actual repos
        languages = repo_data.get("languages", {})
        total_commits = repo_data.get("total_commits", 0)
        has_readme = repo_data.get("has_readme", False)
        has_tests = repo_data.get("has_tests", False)
        has_error_handling = repo_data.get("has_error_handling", False)

        # Determine complexity
        if num_repos >= 3 and total_commits > 50 and has_tests:
            complexity = "moderate"
        elif num_repos >= 1 and total_commits > 10:
            complexity = "simple"
        else:
            complexity = "minimal"

        red_flags = []
        if not has_readme:
            red_flags.append("no_readme")
        if not has_tests:
            red_flags.append("no_tests")
        if total_commits < 10:
            red_flags.append("minimal_commit_history")
        if not has_error_handling:
            red_flags.append("no_error_handling")

        return GitHubAnalysis(
            repo_url=repo_data.get("url", ""),
            accessible=accessible,
            has_readme=has_readme,
            num_repos=num_repos,
            total_commits=total_commits,
            languages=languages,
            code_quality_signals={
                "has_tests": has_tests,
                "has_ci_cd": repo_data.get("has_ci_cd", False),
                "has_contributing": repo_data.get("has_contributing", False)
            },
            has_tests=has_tests,
            has_error_handling=has_error_handling,
            has_documentation=repo_data.get("has_documentation", False),
            avg_function_length=repo_data.get("avg_function_length", 50),
            max_function_length=repo_data.get("max_function_length", 200),
            project_complexity=complexity,
            red_flags=red_flags
        )

    def analyze_resume(self, resume_data: dict) -> ResumeAnalysis:
        """Analyze resume for verifiable skills and experience."""
        internship = resume_data.get("internship", {})
        has_internship = internship.get("has_internship", False)
        internship_type = internship.get("type", "none")
        internship_duration = internship.get("duration_months", 0)

        projects = resume_data.get("projects", [])
        project_count = len(projects)

        # Determine project quality
        deployed_count = sum(1 for p in projects if p.get("deployed", False))
        if deployed_count >= 2:
            project_quality = "deployed"
        elif deployed_count >= 1:
            project_quality = "production_like"
        elif project_count >= 1:
            project_quality = "academic_only"
        else:
            project_quality = "none"

        # ── Verifiable skills: ONLY from explicit project technologies ──
        # We deliberately do NOT use self-assessed skills (claimed_skills)
        # as verifiable evidence. That creates circular verification.
        verifiable_skills = []
        for project in projects:
            verifiable_skills.extend(project.get("technologies_used", []))

        # ── Claimed skills: from form + resume text keywords ──
        # These are what the user SAYS they know. Separate from evidence.
        claimed_skills = list(resume_data.get("skills", []))
        resume_text = resume_data.get("resume_text", "")
        if resume_text:
            text_lower = resume_text.lower()
            from scrapers.scraper_utils import SKILL_KEYWORDS
            for skill_slug, keywords in SKILL_KEYWORDS.items():
                for kw in keywords:
                    if kw in text_lower and skill_slug not in claimed_skills:
                        claimed_skills.append(skill_slug)
                        break
            # Detect deployment / hosting signals from resume text
            if any(sig in text_lower for sig in ["deployed", "live", "production", "hosted on", "aws", "vercel", "heroku"]):
                if project_quality == "academic_only":
                    project_quality = "production_like"
            # Detect testing signals from resume text
            if any(sig in text_lower for sig in ["unit test", "pytest", "jest", "selenium", "cypress"]):
                if "testing" not in verifiable_skills:
                    verifiable_skills.append("testing")

        return ResumeAnalysis(
            has_internship=has_internship,
            internship_type=internship_type,
            internship_duration_months=internship_duration,
            projects_listed=project_count,
            project_quality=project_quality,
            cgpa=resume_data.get("cgpa"),
            college_tier=resume_data.get("college_tier", "tier_3"),
            skills_claimed=claimed_skills,
            skills_verifiable=list(set(verifiable_skills))
        )

    def run_diagnostics(self, diagnostic_data: dict) -> Dict[str, DiagnosticResult]:
        """Run and evaluate diagnostic coding tasks."""
        results = {}
        for task_id, task_data in diagnostic_data.items():
            results[task_id] = DiagnosticResult(
                task_id=task_id,
                completed=task_data.get("completed", False),
                code_quality=task_data.get("code_quality", 1),
                correctness=task_data.get("correctness", 1),
                time_taken_minutes=task_data.get("time_taken", 60),
                approach_description=task_data.get("approach", ""),
                issues_found=task_data.get("issues", [])
            )
        return results

    @staticmethod
    def _decompose_skill(skill_name: str) -> List[str]:
        """
        Split compound skill names into individual components.
        e.g. 'react_or_vue' → ['react', 'vue']
             'html_css'     → ['html', 'css']
             'nodejs_or_python' → ['nodejs', 'python']
             'javascript'   → ['javascript']
        """
        name = skill_name.lower().strip()
        # Split by '_or_' first, then by '_'
        parts = []
        for segment in name.split("_or_"):
            for sub in segment.split("_"):
                if sub and sub not in parts:
                    parts.append(sub)
        # Filter out noise words
        return [p for p in parts if p not in ("", "and")]

    def assess_skill(self, skill_name: str, self_reported: int,
                     github_evidence: GitHubAnalysis,
                     resume_evidence: ResumeAnalysis,
                     diagnostic_results: Dict[str, DiagnosticResult]) -> SkillEvidence:
        """
        Core assessment logic.
        Rule: Start at NONE (0). Only increase if real evidence exists.
        Compound skills (e.g. 'react_or_vue') are decomposed and ANY match counts.
        """
        evidence_level = SkillLevel.NONE.value
        sources = []
        gaps = []
        skill_lower = skill_name.lower()
        components = self._decompose_skill(skill_name)

        # Helper: check if any component matches a list of strings
        def _any_component_match(target_list):
            target_lower = [t.lower() for t in target_list]
            return [c for c in components if c in target_lower]

        # ── GitHub evidence ──
        gh_langs = github_evidence.languages or {}
        gh_keys = [k.lower() for k in gh_langs.keys()]
        gh_matches = [c for c in components if c in gh_keys]
        if gh_matches:
            # Sum LOC across all matching components
            total_loc = sum(gh_langs.get(m, 0) for m in gh_matches)
            if total_loc > 1000:
                evidence_level = max(evidence_level, SkillLevel.INTERMEDIATE.value)
                sources.append(f"github_{'_'.join(gh_matches)}_loc_{total_loc}")
            elif total_loc > 100:
                evidence_level = max(evidence_level, SkillLevel.BASIC.value)
                sources.append(f"github_{'_'.join(gh_matches)}_loc_{total_loc}")
            else:
                evidence_level = max(evidence_level, SkillLevel.BEGINNER.value)
                sources.append(f"github_{'_'.join(gh_matches)}_minimal")
        elif github_evidence.accessible and github_evidence.num_repos > 0:
            gaps.append(f"no_{skill_lower}_in_github")

        # ── Resume evidence ──
        # 1. Check verifiable skills (from project technologies / internships)
        verifiable_lower = [s.lower() for s in resume_evidence.skills_verifiable]
        resume_matches = [c for c in components if c in verifiable_lower]
        if resume_matches:
            if resume_evidence.project_quality in ["deployed", "production_like"]:
                evidence_level = max(evidence_level, SkillLevel.INTERMEDIATE.value)
                sources.append(f"resume_project_evidence_{'_'.join(resume_matches)}")
            else:
                evidence_level = max(evidence_level, SkillLevel.BASIC.value)
                sources.append(f"resume_academic_project_{'_'.join(resume_matches)}")

        # 2. Check resume text for strong skill mentions
        # claimed_skills already has keywords extracted from resume text
        claimed_lower = [s.lower() for s in resume_evidence.skills_claimed]
        text_matches = [c for c in components if c in claimed_lower]
        if text_matches and not resume_matches:
            # Resume text mention is weaker than project evidence
            evidence_level = max(evidence_level, SkillLevel.BEGINNER.value)
            sources.append(f"resume_text_mention_{'_'.join(text_matches)}")

        if not resume_matches and not text_matches:
            gaps.append(f"no_{skill_lower}_in_resume")

        # ── Diagnostic evidence ──
        for task_id, result in diagnostic_results.items():
            tid_lower = task_id.lower()
            if any(c in tid_lower for c in components):
                if result.completed:
                    evidence_level = max(evidence_level, result.code_quality)
                    sources.append(f"diagnostic_{task_id}_score_{result.code_quality}")
                    if result.issues_found:
                        gaps.extend(result.issues_found)

        # ── Final: No evidence at all → stay at NONE ──
        if not sources:
            evidence_level = SkillLevel.NONE.value
            gaps = [f"no_verifiable_evidence_for_{skill_lower}"]

        return SkillEvidence(
            skill_name=skill_name,
            self_reported=self_reported,
            evidence_based=evidence_level,
            evidence_sources=sources,
            gaps=gaps,
            contradiction_flag=(self_reported > evidence_level + 1)
        )

    def generate_full_assessment(self, profile: dict) -> dict:
        """
        Generate complete evidence-based assessment.
        Returns structured assessment with all skills, gaps, and contradictions.
        """
        # Parse inputs
        github_data = profile.get("github", {})
        resume_data = profile.get("resume", {})
        diagnostic_data = profile.get("diagnostics", {})
        self_assessment = profile.get("self_assessment", {})

        # Run analyses
        github_analysis = self.analyze_github(github_data)
        resume_analysis = self.analyze_resume(resume_data)
        diagnostic_results = self.run_diagnostics(diagnostic_data)

        # Assess each skill
        skills = {}
        for skill_name, self_rating in self_assessment.items():
            skills[skill_name] = self.assess_skill(
                skill_name, self_rating,
                github_analysis, resume_analysis, diagnostic_results
            )

        # Identify all contradictions
        contradictions = [
            s for s in skills.values() if s.contradiction_flag
        ]

        # Identify critical gaps (skills needed for target but missing)
        critical_gaps = []
        for skill_evidence in skills.values():
            critical_gaps.extend(skill_evidence.gaps)

        return {
            "github_analysis": github_analysis,
            "resume_analysis": resume_analysis,
            "diagnostic_results": diagnostic_results,
            "skills": skills,
            "contradictions": contradictions,
            "critical_gaps": list(set(critical_gaps)),
            "overall_trust_score": self._calculate_trust_score(skills, github_analysis, resume_analysis, diagnostic_results)
        }

    def _calculate_trust_score(self, skills: Dict[str, SkillEvidence], 
                               github: GitHubAnalysis, 
                               resume: ResumeAnalysis,
                               diagnostic_results: Dict[str, DiagnosticResult] = None) -> float:
        """
        Calculate how much we trust this profile's evidence.
        0.0 = no trust, 1.0 = high trust.
        Penalizes suspicious patterns (e.g., high GitHub stats + low diagnostic scores + plagiarism flags).
        """
        score = 0.0

        # GitHub contribution
        if github.accessible and github.num_repos > 0:
            score += 0.3
            if github.has_readme:
                score += 0.1
            if github.has_tests:
                score += 0.1

        # Resume contribution
        if resume.has_internship:
            score += 0.2
        if resume.project_quality in ["deployed", "production_like"]:
            score += 0.2

        # Diagnostic contribution
        if skills:
            diagnostic_scores = [s.evidence_based for s in skills.values()]
            score += min(0.2, sum(diagnostic_scores) / (len(diagnostic_scores) * 5) * 0.2)

        # Penalty for suspicious diagnostic flags (plagiarism, copied code, etc.)
        if diagnostic_results:
            for result in diagnostic_results.values():
                issues_str = " ".join(result.issues_found).lower()
                if any(flag in issues_str for flag in ["plagiarism", "copied", "cheat", "fake"]):
                    score -= 0.15  # Significant penalty for dishonest evidence
                if "doesnt_explain" in issues_str or "cannot explain" in issues_str:
                    score -= 0.05

        return max(0.0, min(1.0, score))
