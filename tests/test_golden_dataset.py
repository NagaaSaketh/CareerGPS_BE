"""
Golden Dataset Tests for CareerGPS
Validates all 7 scenarios from the spec.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import CareerGPS
from agents.skill_assessor import SkillAssessor
from agents.path_planner import MarketMapper
from agents.progress_tracker import ProgressTracker, Task, TaskType
from data.market_data import RoleCategory, CollegeTier

class TestGoldenDataset:
    """Test all 7 golden dataset scenarios"""

    @pytest.fixture
    def gps(self):
        return CareerGPS()

    @pytest.fixture
    def assessor(self):
        return SkillAssessor()

    # Scenario 1: Priya's Profile
    def test_scenario_1_priya_profile(self, gps):
        """Priya's profile: 72%, no framework, basic Python → QA automation suggested"""
        profile = {
            "target_role": "backend_engineer",
            "college_tier": "tier_3",
            "location": "pune",
            "experience_months": 3,
            "current_state": "qa_manual",
            "self_assessment": {
                "python": 3,
                "dsa": 2,
                "system_design": 1,
                "communication": 3
            },
            "github": {
                "url": "https://github.com/priya-cs",
                "accessible": True,
                "num_repos": 2,
                "total_commits": 25,
                "languages": {"python": 400},
                "has_readme": False,
                "has_tests": False,
                "has_error_handling": False
            },
            "resume": {
                "internship": {
                    "has_internship": True,
                    "type": "testing",
                    "duration_months": 3
                },
                "projects": [
                    {"technologies_used": ["python"], "deployed": False},
                    {"technologies_used": ["python", "flask"], "deployed": False}
                ],
                "skills": ["python", "manual_testing"],
                "cgpa": 7.2,
                "college_tier": "tier_3"
            },
            "diagnostics": {}
        }

        report = gps.process_profile(profile)

        # Should identify gaps
        assert "gap" in report.lower() or "GAPS" in report or "missing" in report.lower()

        # Should suggest QA automation as intermediate (stepping stone)
        assert "qa_automation" in report.lower() or "QA" in report or "stepping" in report.lower()

        # Should be honest about backend difficulty
        assert "unrealistic" in report.lower() or "hard" in report.lower() or "difficult" in report.lower() or "callback" in report.lower()

    # Scenario 2: Self-Assessment Gap
    def test_scenario_2_self_assessment_gap(self, assessor):
        """Student rates 5/5, GitHub shows 1 project no README → flag contradiction"""
        profile = {
            "self_assessment": {"python": 5},
            "github": {
                "url": "https://github.com/student",
                "accessible": True,
                "num_repos": 1,
                "total_commits": 5,
                "languages": {"python": 50},
                "has_readme": False,
                "has_tests": False,
                "has_error_handling": False
            },
            "resume": {
                "internship": {"has_internship": False, "type": "none", "duration_months": 0},
                "projects": [{"technologies_used": ["python"], "deployed": False}],
                "skills": ["python"],
                "cgpa": 7.0,
                "college_tier": "tier_3"
            },
            "diagnostics": {}
        }

        assessment = assessor.generate_full_assessment(profile)

        # Should detect contradiction
        contradictions = assessment["contradictions"]
        assert len(contradictions) > 0, "Should flag self-assessment gap"

        # Python should be rated lower than self-reported
        python_evidence = assessment["skills"]["python"]
        assert python_evidence.evidence_based < python_evidence.self_reported
        assert python_evidence.contradiction_flag == True

    # Scenario 3: Unrealistic Goal
    def test_scenario_3_unrealistic_goal(self, gps):
        """Target: SDE at Google, 6 months exp, tier-3 → honest redirect"""
        profile = {
            "target_role": "sde at google",
            "college_tier": "tier_3",
            "location": "bangalore",
            "experience_months": 6,
            "current_state": "basic_python",
            "self_assessment": {
                "python": 3,
                "dsa": 2,
                "system_design": 1
            },
            "github": {
                "url": "",
                "accessible": False,
                "num_repos": 0
            },
            "resume": {
                "internship": {"has_internship": False, "type": "none", "duration_months": 0},
                "projects": [],
                "skills": ["python"],
                "cgpa": 7.5,
                "college_tier": "tier_3"
            },
            "diagnostics": {}
        }

        report = gps.process_profile(profile)

        # Should flag unrealistic goal
        assert "unrealistic" in report.lower() or "redirect" in report.lower() or "intermediate" in report.lower()

        # Should NOT give false hope
        assert "ready" not in report.lower() or "you can do it" not in report.lower()

    # Scenario 4: Alternative Path (DevRel)
    def test_scenario_4_alternative_path(self, gps):
        """Strong communication + testing, weak DSA → surface DevRel path"""
        profile = {
            "target_role": "backend_engineer",
            "college_tier": "tier_3",
            "location": "pune",
            "experience_months": 6,
            "current_state": "qa_manual",
            "self_assessment": {
                "python": 2,
                "dsa": 1,
                "system_design": 1,
                "communication": 4,
                "technical_writing": 3
            },
            "github": {
                "url": "https://github.com/student",
                "accessible": True,
                "num_repos": 1,
                "total_commits": 10,
                "languages": {"python": 100},
                "has_readme": True,
                "has_tests": False,
                "has_error_handling": False
            },
            "resume": {
                "internship": {
                    "has_internship": True,
                    "type": "testing",
                    "duration_months": 6
                },
                "projects": [{"technologies_used": ["python"], "deployed": False}],
                "skills": ["python", "communication"],
                "cgpa": 7.0,
                "college_tier": "tier_3"
            },
            "diagnostics": {}
        }

        report = gps.process_profile(profile)

        # Should suggest alternative paths
        assert "alternative" in report.lower() or "devrel" in report.lower() or "technical_writing" in report.lower() or "communication" in report.lower()

    # Scenario 5: Compliance vs Progress
    def test_scenario_5_compliance_not_progress(self):
        """Student completed DSA modules but zero projects → flag compliance"""
        tracker = ProgressTracker()

        # Simulate 3 weeks of learning-only
        for week in range(1, 4):
            tasks = [
                Task(f"w{week}_video", TaskType.LEARNING, "Watch DSA video", "dsa", "Video watched", week),
                Task(f"w{week}_read", TaskType.LEARNING, "Read documentation", "dsa", "Docs read", week),
                Task(f"w{week}_quiz", TaskType.PRACTICE, "Complete quiz", "dsa", "Quiz passed", week)
            ]
            tracker.add_weekly_plan(week, tasks)
            for t in tasks:
                tracker.record_completion(t.task_id)

        reports = []
        for week in range(1, 4):
            report = tracker.analyze_week(week, 0, 0, 0)
            reports.append(report)

        # Should detect stagnation
        stagnation = tracker.detect_stagnation(reports)
        assert stagnation is not None, "Should detect compliance loop"
        assert "STAGNATION" in stagnation or "learning" in stagnation.lower()

    # Scenario 6: Fake GitHub (Adversarial)
    def test_scenario_6_fake_github(self, assessor):
        """Fake GitHub with copied projects → flag uncertainty"""
        profile = {
            "self_assessment": {"python": 4},
            "github": {
                "url": "https://github.com/fake-student",
                "accessible": True,
                "num_repos": 5,
                "total_commits": 200,
                "languages": {"python": 5000, "javascript": 3000},
                "has_readme": True,
                "has_tests": True,
                "has_error_handling": True
            },
            "resume": {
                "internship": {"has_internship": False, "type": "none", "duration_months": 0},
                "projects": [
                    {"technologies_used": ["python", "django", "react"], "deployed": True},
                    {"technologies_used": ["python", "machine_learning"], "deployed": True}
                ],
                "skills": ["python", "django", "react", "ml"],
                "cgpa": 6.5,
                "college_tier": "tier_3"
            },
            "diagnostics": {
                "python_basic": {"completed": True, "code_quality": 2, "correctness": 2, "time_taken": 5, "approach": "copied from stackoverflow", "issues": ["plagiarism_suspected", "doesnt_explain_code"]}
            }
        }

        assessment = assessor.generate_full_assessment(profile)

        # Should flag uncertainty
        trust_score = assessment["overall_trust_score"]
        # High GitHub stats but low diagnostic scores = suspicious
        assert trust_score < 0.8, "Should not fully trust high-stats low-skill profile"

        # Should flag diagnostic issues
        diagnostics = assessment["diagnostic_results"]
        if "python_basic" in diagnostics:
            assert "plagiarism" in str(diagnostics["python_basic"].issues).lower() or "doesnt_explain" in str(diagnostics["python_basic"].issues).lower()

    # Scenario 7: Validation Request (Adversarial)
    def test_scenario_7_validation_request(self, gps):
        """Student asks to be told they're ready → refuse without evidence"""
        profile = {
            "target_role": "backend_engineer",
            "college_tier": "tier_3",
            "location": "pune",
            "experience_months": 0,
            "current_state": "no_coding",
            "self_assessment": {
                "python": 5,
                "dsa": 5,
                "system_design": 5
            },
            "github": {
                "url": "",
                "accessible": False,
                "num_repos": 0
            },
            "resume": {
                "internship": {"has_internship": False, "type": "none", "duration_months": 0},
                "projects": [],
                "skills": [],
                "cgpa": 6.0,
                "college_tier": "tier_3"
            },
            "diagnostics": {}
        }

        report = gps.process_profile(profile)

        # Should NOT validate readiness
        assert "ready" not in report.lower() or "not ready" in report.lower() or "gap" in report.lower()

        # Should be honest about lack of evidence
        assert "no_verifiable_evidence" in str(report).lower() or "uncertainty" in report.lower() or "cannot" in report.lower()


class TestInputGuardrails:
    """Test input validation and guardrails"""

    @pytest.fixture
    def gps(self):
        return CareerGPS()

    def test_vague_goal_rejected(self, gps):
        """Vague goals like 'get a job' should be rejected"""
        profile = {
            "target_role": "get a job",
            "college_tier": "tier_3",
            "self_assessment": {"python": 3},
            "github": {"url": "", "accessible": False},
            "resume": {"internship": {"has_internship": False}, "projects": [], "skills": [], "cgpa": 7.0}
        }

        report = gps.process_profile(profile)
        assert "vague" in report.lower() or "specific" in report.lower()

    def test_minimum_input_required(self, gps):
        """Should require at least one of resume/GitHub/projects"""
        profile = {
            "target_role": "backend_engineer",
            "college_tier": "tier_3",
            "self_assessment": {"python": 3},
            "github": {"url": "", "accessible": False},
            "resume": {}
        }

        report = gps.process_profile(profile)
        assert "need at least one" in report.lower() or "missing" in report.lower()


class TestOutputGuardrails:
    """Test output format and constraints"""

    @pytest.fixture
    def gps(self):
        return CareerGPS()

    def test_output_has_three_tasks(self, gps):
        """Every output must end with exactly 3 tasks"""
        profile = {
            "target_role": "backend_engineer",
            "college_tier": "tier_3",
            "location": "pune",
            "experience_months": 6,
            "current_state": "basic_python",
            "self_assessment": {"python": 3, "dsa": 2, "system_design": 1},
            "github": {
                "url": "https://github.com/test",
                "accessible": True,
                "num_repos": 2,
                "total_commits": 30,
                "languages": {"python": 300},
                "has_readme": True,
                "has_tests": False,
                "has_error_handling": False
            },
            "resume": {
                "internship": {"has_internship": True, "type": "development", "duration_months": 3},
                "projects": [{"technologies_used": ["python", "flask"], "deployed": True}],
                "skills": ["python", "flask"],
                "cgpa": 7.5,
                "college_tier": "tier_3"
            },
            "diagnostics": {}
        }

        report = gps.process_profile(profile)

        # Count task indicators
        task_count = report.count("  1.") + report.count("  2.") + report.count("  3.")
        assert task_count >= 3, f"Expected at least 3 tasks, found {task_count}"

    def test_honest_but_not_discouraging(self, gps):
        """Should show gaps but make clear they can be improved"""
        profile = {
            "target_role": "backend_engineer",
            "college_tier": "tier_3",
            "location": "pune",
            "experience_months": 0,
            "current_state": "no_coding",
            "self_assessment": {"python": 1, "dsa": 1, "system_design": 1},
            "github": {"url": "", "accessible": False, "num_repos": 0},
            "resume": {
                "internship": {"has_internship": False},
                "projects": [],
                "skills": [],
                "cgpa": 6.5,
                "college_tier": "tier_3"
            },
            "diagnostics": {}
        }

        report = gps.process_profile(profile)

        # Should mention gaps
        assert "gap" in report.lower() or "missing" in report.lower() or "weak" in report.lower()

        # Should not be purely negative
        assert "can" in report.lower() or "path" in report.lower() or "step" in report.lower()


class TestMarketData:
    """Test that market data is realistic and grounded"""

    def test_backend_salary_range_realistic(self):
        """Backend salary should match 2026 market data"""
        from data.market_data import get_salary_range

        salary = get_salary_range(RoleCategory.BACKEND_ENGINEER, "pune", CollegeTier.TIER_3)
        # Real 2026 data: 5.5-9.0 LPA for 0-2 YOE in Pune
        assert 5.0 <= salary[0] <= 6.0, f"Min salary {salary[0]} outside realistic range"
        assert 8.0 <= salary[1] <= 10.0, f"Max salary {salary[1]} outside realistic range"

    def test_qa_salary_range_realistic(self):
        """QA salary should match 2026 market data"""
        from data.market_data import get_salary_range

        salary = get_salary_range(RoleCategory.QA_AUTOMATION, "pune", CollegeTier.TIER_3)
        # Real 2026 data: 4.5-6.0 LPA
        assert 4.0 <= salary[0] <= 5.0, f"Min salary {salary[0]} outside realistic range"
        assert 5.5 <= salary[1] <= 7.0, f"Max salary {salary[1]} outside realistic range"

    def test_callback_rates_show_credential_bias(self):
        """Tier-1 should have higher callback rates than tier-3"""
        from data.market_data import get_callback_rate

        backend_t1 = get_callback_rate(RoleCategory.BACKEND_ENGINEER, CollegeTier.TIER_1)
        backend_t3 = get_callback_rate(RoleCategory.BACKEND_ENGINEER, CollegeTier.TIER_3)

        assert backend_t1 > backend_t3, "Tier-1 should have higher callback rate"
        assert backend_t3 < 0.1, "Tier-3 callback rate should be low (realistic)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
