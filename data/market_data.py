"""
Dynamic Market Data Module for CareerGPS
Supports ANY career path, not just backend engineering.

NOTE: The data below is derived from aggregated industry research and publicly
available sources (Glassdoor, Indeed, Naukri, LinkedIn). Figures represent
approximate ranges and should be treated as directional guidance rather than
precise, real-time market data. For production use, integrate live APIs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json

class CollegeTier(Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2" 
    TIER_3 = "tier_3"

class RoleCategory(Enum):
    """Canonical role categories used in tests and API."""
    BACKEND_ENGINEER = "backend_engineer"
    FRONTEND_ENGINEER = "frontend_engineer"
    FULLSTACK_ENGINEER = "fullstack_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    MOBILE_DEVELOPER = "mobile_developer"
    SITE_RELIABILITY_ENGINEER = "site_reliability_engineer"
    QA_AUTOMATION = "qa_automation"
    SDET = "sdet"
    DATA_ANALYST = "data_analyst"
    DATA_SCIENTIST = "data_scientist"
    DATA_ENGINEER = "data_engineer"
    ML_ENGINEER = "ml_engineer"
    PRODUCT_MANAGER = "product_manager"
    UX_DESIGNER = "ux_designer"
    UI_DESIGNER = "ui_designer"
    DEVREL = "devrel"
    TECHNICAL_WRITER = "technical_writer"
    SOLUTIONS_ENGINEER = "solutions_engineer"
    SUPPORT_ENGINEER = "support_engineer"
    BUSINESS_ANALYST = "business_analyst"
    PROJECT_MANAGER = "project_manager"
    SOFTWARE_DEVELOPER = "software_developer"
    SDE = "sde"
    GENERATIVE_AI_ENGINEER = "generative_ai_engineer"
    NLP_ENGINEER = "nlp_engineer"
    COMPUTER_VISION_ENGINEER = "computer_vision_engineer"
    AI_RESEARCH_SCIENTIST = "ai_research_scientist"
    MLOPS_ENGINEER = "mlops_engineer"
    PROMPT_ENGINEER = "prompt_engineer"

# =============================================================================
# DYNAMIC ROLE REGISTRY - Supports ANY role user inputs
# =============================================================================

@dataclass
class RoleRequirements:
    """Requirements for ANY role - dynamically populated"""
    role_name: str  # e.g., "backend_engineer", "data_scientist", "product_manager"
    role_category: str  # e.g., "engineering", "data", "design", "management"
    min_experience_months: int
    required_skills: List[str]
    preferred_skills: List[str]
    framework_tools: List[str]  # Frameworks, tools, software
    system_design_level: str  # none, basic, intermediate, advanced
    salary_range_lpa: Tuple[float, float]  # (min, max) for 0-2 YOE
    hiring_difficulty: str  # easy, medium, hard, very_hard
    typical_rejection_reasons: List[str]

    # Credential bias
    tier_1_callback_rate: float
    tier_2_callback_rate: float
    tier_3_callback_rate: float

    # Alternative paths if direct is unrealistic
    stepping_stone_roles: List[str] = field(default_factory=list)

    # What makes someone strong in this role
    strength_indicators: List[str] = field(default_factory=list)

# =============================================================================
# COMPREHENSIVE ROLE DATABASE - Real 2026 Data
# =============================================================================

ROLE_DATABASE = {
    # ENGINEERING ROLES
    "backend_engineer": RoleRequirements(
        role_name="backend_engineer",
        role_category="engineering",
        min_experience_months=24,
        required_skills=["python", "java", "go", "nodejs", "rest_api_design", "sql", "nosql", "git", "docker", "cloud_basics"],
        preferred_skills=["microservices", "kafka", "rabbitmq", "kubernetes", "ci_cd", "redis", "elasticsearch"],
        framework_tools=["django", "fastapi", "flask", "spring_boot", "express", "nestjs"],
        system_design_level="intermediate",
        salary_range_lpa=(5.5, 9.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["no_framework_experience", "no_production_project", "weak_system_design", "no_api_design_experience", "insufficient_git_history", "no_testing_practices"],
        tier_1_callback_rate=0.25,
        tier_2_callback_rate=0.08,
        tier_3_callback_rate=0.03,
        stepping_stone_roles=["qa_automation", "support_engineer", "devops_engineer"],
        strength_indicators=["strong_logic", "api_design", "database_knowledge", "system_thinking"]
    ),

    "frontend_engineer": RoleRequirements(
        role_name="frontend_engineer",
        role_category="engineering",
        min_experience_months=12,
        required_skills=["javascript", "typescript", "html", "css", "react_or_vue_or_angular", "git", "responsive_design", "browser_devtools"],
        preferred_skills=["nextjs", "tailwind", "state_management", "performance_optimization", "accessibility", "testing"],
        framework_tools=["react", "vue", "angular", "nextjs", "webpack", "vite"],
        system_design_level="basic",
        salary_range_lpa=(5.0, 8.5),
        hiring_difficulty="medium",
        typical_rejection_reasons=["weak_javascript_fundamentals", "no_component_design", "no_state_management", "poor_css_skills", "no_accessibility_knowledge"],
        tier_1_callback_rate=0.22,
        tier_2_callback_rate=0.10,
        tier_3_callback_rate=0.05,
        stepping_stone_roles=["ui_designer", "fullstack_engineer", "support_engineer"],
        strength_indicators=["visual_sense", "attention_to_detail", "user empathy", "component_thinking"]
    ),

    "fullstack_engineer": RoleRequirements(
        role_name="fullstack_engineer",
        role_category="engineering",
        min_experience_months=0,
        required_skills=["javascript", "typescript", "react_or_vue", "nodejs_or_python", "html_css", "sql", "git", "rest_apis"],
        preferred_skills=["nextjs", "tailwind", "mongodb", "docker", "aws_basics", "testing"],
        framework_tools=["react", "nodejs", "express", "django", "fastapi", "nextjs"],
        system_design_level="basic",
        salary_range_lpa=(6.0, 8.5),
        hiring_difficulty="medium",
        typical_rejection_reasons=["frontend_weak", "backend_weak", "no_full_project", "no_deployment_experience"],
        tier_1_callback_rate=0.22,
        tier_2_callback_rate=0.10,
        tier_3_callback_rate=0.05,
        stepping_stone_roles=["frontend_engineer", "backend_engineer", "ui_designer"],
        strength_indicators=["breadth", "end_to_end_ownership", "rapid_prototyping"]
    ),

    "devops_engineer": RoleRequirements(
        role_name="devops_engineer",
        role_category="engineering",
        min_experience_months=12,
        required_skills=["linux", "bash", "docker", "kubernetes", "ci_cd", "cloud_platforms", "git", "monitoring", "terraform"],
        preferred_skills=["ansible", "prometheus", "grafana", "helm", "istio", "python", "go"],
        framework_tools=["jenkins", "github_actions", "gitlab_ci", "aws", "gcp", "azure", "terraform"],
        system_design_level="intermediate",
        salary_range_lpa=(6.0, 9.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["no_cloud_experience", "weak_linux", "no_ci_cd_practice", "no_infrastructure_as_code", "no_monitoring_experience"],
        tier_1_callback_rate=0.20,
        tier_2_callback_rate=0.09,
        tier_3_callback_rate=0.04,
        stepping_stone_roles=["support_engineer", "site_reliability_engineer", "backend_engineer"],
        strength_indicators=["automation_mindset", "troubleshooting", "system_thinking", "scripting"]
    ),

    "mobile_developer": RoleRequirements(
        role_name="mobile_developer",
        role_category="engineering",
        min_experience_months=6,
        required_skills=["kotlin_or_swift", "java", "dart", "mobile_ui", "rest_apis", "git", "app_lifecycle"],
        preferred_skills=["flutter", "react_native", "firebase", "push_notifications", "offline_storage", "performance_tuning"],
        framework_tools=["android_sdk", "ios_sdk", "flutter", "react_native", "xamarin"],
        system_design_level="basic",
        salary_range_lpa=(5.5, 8.5),
        hiring_difficulty="medium",
        typical_rejection_reasons=["no_app_store_deployment", "weak_ui_implementation", "no_state_management", "no_api_integration"],
        tier_1_callback_rate=0.20,
        tier_2_callback_rate=0.10,
        tier_3_callback_rate=0.05,
        stepping_stone_roles=["frontend_engineer", "ui_designer", "fullstack_engineer"],
        strength_indicators=["platform_knowledge", "ui_precision", "performance_awareness"]
    ),

    # QA / TESTING ROLES
    "qa_automation": RoleRequirements(
        role_name="qa_automation",
        role_category="qa",
        min_experience_months=0,
        required_skills=["manual_testing", "test_case_design", "selenium_or_playwright", "api_testing", "basic_programming", "agile", "jira"],
        preferred_skills=["cypress", "ci_cd_integration", "performance_testing", "mobile_testing", "bdd"],
        framework_tools=["selenium", "testng", "junit", "cucumber", "postman", "rest_assured"],
        system_design_level="none",
        salary_range_lpa=(4.5, 6.0),
        hiring_difficulty="medium",
        typical_rejection_reasons=["only_manual_testing_no_automation", "no_programming_for_automation", "no_api_testing_experience", "weak_test_case_documentation"],
        tier_1_callback_rate=0.30,
        tier_2_callback_rate=0.15,
        tier_3_callback_rate=0.08,
        stepping_stone_roles=["support_engineer", "business_analyst", "sdet"],
        strength_indicators=["attention_to_detail", "process_oriented", "analytical_thinking", "documentation"]
    ),

    "sdet": RoleRequirements(
        role_name="sdet",
        role_category="qa",
        min_experience_months=12,
        required_skills=["java_or_python", "test_automation", "api_testing", "ci_cd", "git", "framework_design", "performance_testing"],
        preferred_skills=["docker", "kubernetes", "security_testing", "contract_testing", "test_data_management"],
        framework_tools=["selenium", "appium", "cypress", "junit", "testng", "jmeter", "k6"],
        system_design_level="basic",
        salary_range_lpa=(6.0, 9.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["weak_programming", "no_framework_design", "no_ci_cd_integration", "no_performance_testing"],
        tier_1_callback_rate=0.25,
        tier_2_callback_rate=0.12,
        tier_3_callback_rate=0.06,
        stepping_stone_roles=["qa_automation", "support_engineer", "backend_engineer"],
        strength_indicators=["programming", "system_thinking", "automation", "quality_mindset"]
    ),

    # DATA ROLES
    "data_analyst": RoleRequirements(
        role_name="data_analyst",
        role_category="data",
        min_experience_months=0,
        required_skills=["sql", "excel", "python_or_r", "data_visualization", "statistics", "business_understanding", "etl_basics"],
        preferred_skills=["tableau", "power_bi", "pandas", "numpy", "dbt", "snowflake", "machine_learning_basics"],
        framework_tools=["tableau", "power_bi", "looker", "pandas", "numpy", "dbt"],
        system_design_level="none",
        salary_range_lpa=(4.5, 7.0),
        hiring_difficulty="medium",
        typical_rejection_reasons=["weak_sql", "no_business_context", "poor_visualization", "no_statistical_knowledge", "no_tool_proficiency"],
        tier_1_callback_rate=0.25,
        tier_2_callback_rate=0.14,
        tier_3_callback_rate=0.08,
        stepping_stone_roles=["business_analyst", "support_engineer", "project_manager"],
        strength_indicators=["analytical_thinking", "business_acumen", "attention_to_detail", "storytelling"]
    ),

    "data_scientist": RoleRequirements(
        role_name="data_scientist",
        role_category="data",
        min_experience_months=12,
        required_skills=["python", "r", "sql", "statistics", "machine_learning", "data_preprocessing", "feature_engineering", "git"],
        preferred_skills=["deep_learning", "nlp", "computer_vision", "mlops", "big_data", "cloud_ml", "experimentation"],
        framework_tools=["scikit_learn", "tensorflow", "pytorch", "pandas", "numpy", "jupyter", "mlflow"],
        system_design_level="basic",
        salary_range_lpa=(7.0, 12.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["weak_math_stats", "no_ml_project_end_to_end", "no_business_impact", "no_experimentation", "tool_only_no_concepts"],
        tier_1_callback_rate=0.20,
        tier_2_callback_rate=0.10,
        tier_3_callback_rate=0.04,
        stepping_stone_roles=["data_analyst", "ml_engineer", "data_engineer"],
        strength_indicators=["mathematical_intuition", "research_mindset", "business_translation", "experimentation"]
    ),

    "data_engineer": RoleRequirements(
        role_name="data_engineer",
        role_category="data",
        min_experience_months=12,
        required_skills=["python", "sql", "etl_pipelines", "data_warehousing", "cloud_platforms", "git", "data_modeling"],
        preferred_skills=["spark", "kafka", "airflow", "dbt", "snowflake", "redshift", "data_governance", "streaming"],
        framework_tools=["apache_spark", "airflow", "dbt", "snowflake", "kafka", "hadoop", "aws_glue"],
        system_design_level="intermediate",
        salary_range_lpa=(6.0, 10.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["no_pipeline_experience", "weak_sql", "no_cloud_data_tools", "no_data_modeling", "no_optimization"],
        tier_1_callback_rate=0.22,
        tier_2_callback_rate=0.11,
        tier_3_callback_rate=0.05,
        stepping_stone_roles=["data_analyst", "business_analyst", "backend_engineer"],
        strength_indicators=["pipeline_thinking", "optimization", "system_design", "data_intuition"]
    ),

    "ml_engineer": RoleRequirements(
        role_name="ml_engineer",
        role_category="data",
        min_experience_months=18,
        required_skills=["python", "machine_learning", "mlops", "docker", "kubernetes", "ci_cd_ml", "cloud", "git"],
        preferred_skills=["feature_stores", "model_monitoring", "a_b_testing", "distributed_training", "gpu_computing"],
        framework_tools=["tensorflow", "pytorch", "mlflow", "kubeflow", "bentoml", "aws_sagemaker"],
        system_design_level="intermediate",
        salary_range_lpa=(8.0, 14.0),
        hiring_difficulty="very_hard",
        typical_rejection_reasons=["no_mlops_experience", "no_model_deployment", "weak_software_engineering", "no_monitoring", "no_scaling"],
        tier_1_callback_rate=0.18,
        tier_2_callback_rate=0.08,
        tier_3_callback_rate=0.03,
        stepping_stone_roles=["data_scientist", "data_analyst", "data_engineer"],
        strength_indicators=["engineering_rigor", "ml_knowledge", "system_thinking", "optimization"]
    ),

    # PRODUCT & DESIGN ROLES
    "product_manager": RoleRequirements(
        role_name="product_manager",
        role_category="product",
        min_experience_months=0,
        required_skills=["communication", "stakeholder_management", "data_analysis", "user_research", "roadmapping", "prioritization", "agile"],
        preferred_skills=["sql", "ab_testing", "metrics_design", "growth_hacking", "technical_depth", "design_thinking"],
        framework_tools=["jira", "confluence", "figma", "amplitude", "mixpanel", "sql"],
        system_design_level="none",
        salary_range_lpa=(6.0, 10.0),
        hiring_difficulty="medium",
        typical_rejection_reasons=["no_ownership_examples", "weak_data_skills", "no_user_research", "poor_communication", "no_prioritization_framework"],
        tier_1_callback_rate=0.20,
        tier_2_callback_rate=0.12,
        tier_3_callback_rate=0.07,
        stepping_stone_roles=["business_analyst", "project_manager", "solutions_engineer"],
        strength_indicators=["user_empathy", "business_sense", "communication", "decision_making"]
    ),

    "ux_designer": RoleRequirements(
        role_name="ux_designer",
        role_category="design",
        min_experience_months=0,
        required_skills=["user_research", "wireframing", "prototyping", "usability_testing", "design_tools", "information_architecture", "communication"],
        preferred_skills=["interaction_design", "motion_design", "design_systems", "frontend_basics", "data_driven_design", "accessibility"],
        framework_tools=["figma", "sketch", "adobe_xd", "invision", "principle", "maze"],
        system_design_level="none",
        salary_range_lpa=(4.5, 7.5),
        hiring_difficulty="medium",
        typical_rejection_reasons=["weak_portfolio", "no_research_process", "no_usability_testing", "poor_visual_design", "no_collaboration_examples"],
        tier_1_callback_rate=0.22,
        tier_2_callback_rate=0.12,
        tier_3_callback_rate=0.06,
        stepping_stone_roles=["ui_designer", "frontend_engineer", "devrel"],
        strength_indicators=["empathy", "visual_sense", "problem_framing", "communication"]
    ),

    "ui_designer": RoleRequirements(
        role_name="ui_designer",
        role_category="design",
        min_experience_months=0,
        required_skills=["visual_design", "design_tools", "typography", "color_theory", "layout", "design_systems", "communication"],
        preferred_skills=["motion_design", "frontend_basics", "branding", "illustration", "3d_design", "accessibility"],
        framework_tools=["figma", "sketch", "adobe_suite", "framer", "webflow"],
        system_design_level="none",
        salary_range_lpa=(4.0, 6.5),
        hiring_difficulty="easy",
        typical_rejection_reasons=["weak_portfolio", "no_design_system_knowledge", "poor_typography", "no_responsive_design", "no_tool_proficiency"],
        tier_1_callback_rate=0.25,
        tier_2_callback_rate=0.15,
        tier_3_callback_rate=0.10,
        stepping_stone_roles=["ux_designer", "frontend_engineer", "devrel"],
        strength_indicators=["visual_craft", "attention_to_detail", "taste", "tool_mastery"]
    ),

    # DEVREL & TECHNICAL ROLES
    "devrel": RoleRequirements(
        role_name="devrel",
        role_category="devrel",
        min_experience_months=0,
        required_skills=["strong_communication", "technical_writing", "developer_community", "content_creation", "basic_coding", "public_speaking"],
        preferred_skills=["video_content", "social_media", "api_documentation", "open_source", "event_management", "advocacy"],
        framework_tools=["github", "markdown", "youtube", "twitter", "dev_to", "hashnode"],
        system_design_level="none",
        salary_range_lpa=(5.0, 8.0),
        hiring_difficulty="medium",
        typical_rejection_reasons=["no_content_portfolio", "weak_technical_depth", "no_community_engagement", "poor_communication", "no_evangelism_examples"],
        tier_1_callback_rate=0.20,
        tier_2_callback_rate=0.12,
        tier_3_callback_rate=0.07,
        stepping_stone_roles=["technical_writer", "solutions_engineer", "support_engineer"],
        strength_indicators=["communication", "technical_depth", "community_building", "content_creation"]
    ),

    "technical_writer": RoleRequirements(
        role_name="technical_writer",
        role_category="devrel",
        min_experience_months=0,
        required_skills=["technical_writing", "documentation", "communication", "research", "markdown", "basic_technical_knowledge"],
        preferred_skills=["api_documentation", "developer_portals", "information_architecture", "seo", "video_scripts", "tool_proficiency"],
        framework_tools=["markdown", "gitbook", "readme", "confluence", "docusaurus", "notion"],
        system_design_level="none",
        salary_range_lpa=(4.5, 7.0),
        hiring_difficulty="easy",
        typical_rejection_reasons=["weak_writing_samples", "no_technical_understanding", "poor_structure", "no_audience_awareness", "no_tool_experience"],
        tier_1_callback_rate=0.22,
        tier_2_callback_rate=0.14,
        tier_3_callback_rate=0.09,
        stepping_stone_roles=["support_engineer", "devrel", "solutions_engineer"],
        strength_indicators=["writing", "clarity", "technical_aptitude", "empathy"]
    ),

    "solutions_engineer": RoleRequirements(
        role_name="solutions_engineer",
        role_category="devrel",
        min_experience_months=6,
        required_skills=["communication", "technical_presales", "api_knowledge", "problem_solving", "client_management", "demo_building", "basic_coding"],
        preferred_skills=["cloud_platforms", "integration_architecture", "security_basics", "data_analysis", "consulting", "negotiation"],
        framework_tools=["postman", "swagger", "salesforce", "hubspot", "aws", "gcp"],
        system_design_level="basic",
        salary_range_lpa=(6.0, 10.0),
        hiring_difficulty="medium",
        typical_rejection_reasons=["weak_technical_depth", "poor_communication", "no_client_facing_experience", "no_demo_building", "no_problem_solving_examples"],
        tier_1_callback_rate=0.20,
        tier_2_callback_rate=0.11,
        tier_3_callback_rate=0.06,
        stepping_stone_roles=["support_engineer", "devrel", "technical_writer"],
        strength_indicators=["communication", "technical_breadth", "problem_solving", "relationship_building"]
    ),

    # SUPPORT & OPERATIONS
    "support_engineer": RoleRequirements(
        role_name="support_engineer",
        role_category="support",
        min_experience_months=0,
        required_skills=["basic_troubleshooting", "communication", "sql_basics", "api_basics", "ticket_management", "customer_empathy"],
        preferred_skills=["scripting", "cloud_basics", "monitoring_tools", "escalation_management", "documentation"],
        framework_tools=["zendesk", "freshdesk", "jira_service_desk", "slack", "pagerduty"],
        system_design_level="none",
        salary_range_lpa=(3.5, 5.5),
        hiring_difficulty="easy",
        typical_rejection_reasons=["poor_communication", "no_technical_aptitude", "no_empathy", "no_ticket_management"],
        tier_1_callback_rate=0.35,
        tier_2_callback_rate=0.20,
        tier_3_callback_rate=0.12,
        stepping_stone_roles=["business_analyst", "solutions_engineer", "technical_writer"],
        strength_indicators=["patience", "communication", "troubleshooting", "empathy"]
    ),

    "site_reliability_engineer": RoleRequirements(
        role_name="site_reliability_engineer",
        role_category="engineering",
        min_experience_months=24,
        required_skills=["linux", "python_or_go", "monitoring", "incident_management", "cloud_platforms", "ci_cd", "automation", "git"],
        preferred_skills=["kubernetes", "terraform", "chaos_engineering", "performance_engineering", "distributed_systems", "oncall_rotation"],
        framework_tools=["prometheus", "grafana", "pagerduty", "terraform", "kubernetes", "ansible"],
        system_design_level="advanced",
        salary_range_lpa=(8.0, 14.0),
        hiring_difficulty="very_hard",
        typical_rejection_reasons=["no_oncall_experience", "weak_automation", "no_incident_management", "no_distributed_systems", "no_performance_tuning"],
        tier_1_callback_rate=0.18,
        tier_2_callback_rate=0.08,
        tier_3_callback_rate=0.03,
        stepping_stone_roles=["devops_engineer", "support_engineer", "backend_engineer"],
        strength_indicators=["reliability_mindset", "automation", "system_thinking", "calm_under_pressure"]
    ),

    # BUSINESS & ANALYTICS
    "business_analyst": RoleRequirements(
        role_name="business_analyst",
        role_category="business",
        min_experience_months=0,
        required_skills=["communication", "requirements_gathering", "data_analysis", "process_modeling", "stakeholder_management", "documentation", "excel"],
        preferred_skills=["sql", "tableau", "power_bi", "agile", "domain_knowledge", "project_management"],
        framework_tools=["excel", "visio", "jira", "confluence", "tableau", "sql"],
        system_design_level="none",
        salary_range_lpa=(4.5, 7.0),
        hiring_difficulty="easy",
        typical_rejection_reasons=["weak_communication", "no_analytical_thinking", "poor_documentation", "no_stakeholder_management", "no_domain_knowledge"],
        tier_1_callback_rate=0.25,
        tier_2_callback_rate=0.15,
        tier_3_callback_rate=0.10,
        stepping_stone_roles=["data_analyst", "support_engineer", "project_manager"],
        strength_indicators=["analytical_thinking", "communication", "domain_knowledge", "detail_oriented"]
    ),

    "project_manager": RoleRequirements(
        role_name="project_manager",
        role_category="business",
        min_experience_months=12,
        required_skills=["communication", "stakeholder_management", "risk_management", "scheduling", "budgeting", "agile", "leadership"],
        preferred_skills=["pmp", "scrum_master", "jira", "confluence", "change_management", "negotiation", "domain_knowledge"],
        framework_tools=["jira", "ms_project", "asana", "monday", "confluence", "slack"],
        system_design_level="none",
        salary_range_lpa=(6.0, 10.0),
        hiring_difficulty="medium",
        typical_rejection_reasons=["no_ownership_examples", "weak_leadership", "no_risk_management", "poor_communication", "no_delivery_track_record"],
        tier_1_callback_rate=0.20,
        tier_2_callback_rate=0.12,
        tier_3_callback_rate=0.07,
        stepping_stone_roles=["business_analyst", "product_manager", "support_engineer"],
        strength_indicators=["leadership", "organization", "communication", "risk_awareness"]
    ),

    # GENERALIST & PRODUCT ENGINEERING
    "software_developer": RoleRequirements(
        role_name="software_developer",
        role_category="engineering",
        min_experience_months=0,
        required_skills=["javascript", "python", "git", "sql", "rest_apis", "problem_solving", "html_css"],
        preferred_skills=["react_or_vue", "nodejs", "docker", "testing", "agile", "version_control_advanced"],
        framework_tools=["react", "vue", "nodejs", "express", "django", "fastapi", "git", "docker"],
        system_design_level="basic",
        salary_range_lpa=(3.5, 8.0),
        hiring_difficulty="medium",
        typical_rejection_reasons=["no_framework_experience", "no_production_project", "weak_system_design", "no_git_history", "no_testing_practices"],
        tier_1_callback_rate=0.18,
        tier_2_callback_rate=0.08,
        tier_3_callback_rate=0.05,
        stepping_stone_roles=["support_engineer", "qa_automation", "frontend_engineer"],
        strength_indicators=["breadth", "rapid_learning", "problem_solving", "shipping_mindset"]
    ),

    "sde": RoleRequirements(
        role_name="sde",
        role_category="engineering",
        min_experience_months=24,
        required_skills=["dsa", "system_design", "cpp_or_java", "operating_systems", "dbms", "computer_networks", "git"],
        preferred_skills=["distributed_systems", "microservices", "concurrency", "performance_optimization", "leetcode_advanced", "behavioral_interviews"],
        framework_tools=["spring_boot", "django", "fastapi", "leetcode", "hackerrank", "git"],
        system_design_level="advanced",
        salary_range_lpa=(8.0, 25.0),
        hiring_difficulty="very_hard",
        typical_rejection_reasons=["weak_dsa", "no_system_design", "no_production_code", "poor_behavioral", "weak_cs_fundamentals", "no_internship_experience"],
        tier_1_callback_rate=0.12,
        tier_2_callback_rate=0.05,
        tier_3_callback_rate=0.02,
        stepping_stone_roles=["backend_engineer", "software_developer", "site_reliability_engineer"],
        strength_indicators=["algorithmic_thinking", "system_design", "cs_fundamentals", "problem_solving"]
    ),

    # AI / ML SPECIALIZED ROLES
    "generative_ai_engineer": RoleRequirements(
        role_name="generative_ai_engineer",
        role_category="data",
        min_experience_months=18,
        required_skills=["python", "transformers", "pytorch", "llm_fine_tuning", "rag", "vector_databases", "git"],
        preferred_skills=["diffusion_models", "multimodal_ai", "llm_evaluation", "prompt_engineering", "model_compression", "gpu_optimization"],
        framework_tools=["pytorch", "tensorflow", "hugging_face", "langchain", "llamaindex", "openai_api", "vllm"],
        system_design_level="intermediate",
        salary_range_lpa=(10.0, 25.0),
        hiring_difficulty="very_hard",
        typical_rejection_reasons=["weak_math", "no_llm_project", "no_fine_tuning_experience", "no_paper_reading", "no_evaluation_metrics"],
        tier_1_callback_rate=0.10,
        tier_2_callback_rate=0.04,
        tier_3_callback_rate=0.015,
        stepping_stone_roles=["ml_engineer", "data_scientist", "nlp_engineer"],
        strength_indicators=["research_aptitude", "math_intuition", "llm_experience", "experimentation"]
    ),

    "nlp_engineer": RoleRequirements(
        role_name="nlp_engineer",
        role_category="data",
        min_experience_months=18,
        required_skills=["python", "nlp_libraries", "transformers", "text_processing", "sentiment_analysis", "sequence_models", "git"],
        preferred_skills=["information_extraction", "question_answering", "dialogue_systems", "multilingual_nlp", "model_deployment", "annotation_tools"],
        framework_tools=["pytorch", "tensorflow", "hugging_face", "spacy", "nltk", "gensim", "langchain"],
        system_design_level="basic",
        salary_range_lpa=(8.0, 20.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["weak_math", "no_nlp_project", "no_deep_learning", "no_text_preprocessing", "no_evaluation_understanding"],
        tier_1_callback_rate=0.12,
        tier_2_callback_rate=0.05,
        tier_3_callback_rate=0.02,
        stepping_stone_roles=["data_scientist", "ml_engineer", "data_analyst"],
        strength_indicators=["linguistic_intuition", "math_background", "text_analysis", "model_tuning"]
    ),

    "computer_vision_engineer": RoleRequirements(
        role_name="computer_vision_engineer",
        role_category="data",
        min_experience_months=18,
        required_skills=["python", "opencv", "cnn", "image_processing", "pytorch", "object_detection", "git"],
        preferred_skills=["segmentation", "3d_vision", "medical_imaging", "video_analysis", "model_optimization", "edge_deployment"],
        framework_tools=["pytorch", "tensorflow", "opencv", "yolo", "detectron2", "mediapipe", "onnx"],
        system_design_level="basic",
        salary_range_lpa=(8.0, 20.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["weak_math", "no_cv_project", "no_deep_learning", "no_image_preprocessing", "no_model_evaluation"],
        tier_1_callback_rate=0.12,
        tier_2_callback_rate=0.05,
        tier_3_callback_rate=0.02,
        stepping_stone_roles=["data_scientist", "ml_engineer", "data_analyst"],
        strength_indicators=["spatial_intuition", "math_background", "image_analysis", "model_tuning"]
    ),

    "ai_research_scientist": RoleRequirements(
        role_name="ai_research_scientist",
        role_category="data",
        min_experience_months=36,
        required_skills=["python", "advanced_math", "deep_learning", "research_methodology", "pytorch", "statistics", "git"],
        preferred_skills=["publications", "conference_papers", "grant_writing", "peer_review", "theoretical_ml", "optimization_theory"],
        framework_tools=["pytorch", "tensorflow", "jax", "latex", "jupyter", "matplotlib", "seaborn"],
        system_design_level="advanced",
        salary_range_lpa=(12.0, 30.0),
        hiring_difficulty="very_hard",
        typical_rejection_reasons=["weak_research_background", "no_publications", "weak_math_stats", "no_original_contribution", "no_phd_or_equivalent"],
        tier_1_callback_rate=0.08,
        tier_2_callback_rate=0.03,
        tier_3_callback_rate=0.015,
        stepping_stone_roles=["ml_engineer", "data_scientist", "generative_ai_engineer"],
        strength_indicators=["research_excellence", "mathematical_rigor", "original_thinking", "publication_record"]
    ),

    "mlops_engineer": RoleRequirements(
        role_name="mlops_engineer",
        role_category="data",
        min_experience_months=18,
        required_skills=["python", "docker", "kubernetes", "ci_cd", "cloud_platforms", "monitoring", "model_serving", "git"],
        preferred_skills=["feature_stores", "model_registry", "a_b_testing", "data_drift_detection", "gpu_cluster_management", "terraform"],
        framework_tools=["kubernetes", "docker", "mlflow", "kubeflow", "bentoml", "aws_sagemaker", "azure_ml", "prometheus", "grafana"],
        system_design_level="intermediate",
        salary_range_lpa=(10.0, 22.0),
        hiring_difficulty="hard",
        typical_rejection_reasons=["no_mlops_experience", "no_cloud_experience", "weak_devops", "no_model_monitoring", "no_scaling_experience"],
        tier_1_callback_rate=0.14,
        tier_2_callback_rate=0.06,
        tier_3_callback_rate=0.025,
        stepping_stone_roles=["devops_engineer", "ml_engineer", "data_engineer"],
        strength_indicators=["engineering_rigor", "ml_knowledge", "automation", "system_reliability"]
    ),

    # PROMPT ENGINEERING
    "prompt_engineer": RoleRequirements(
        role_name="prompt_engineer",
        role_category="devrel",
        min_experience_months=0,
        required_skills=["prompt_engineering", "llm_basics", "communication", "python_basics", "content_creation", "critical_thinking"],
        preferred_skills=["chain_of_thought", "few_shot_prompting", "rag_systems", "model_evaluation", "api_integration", "ui_ux_basics"],
        framework_tools=["openai_api", "langchain", "llamaindex", "anthropic_api", "cohere_api", "streamlit", "gradio"],
        system_design_level="none",
        salary_range_lpa=(5.0, 12.0),
        hiring_difficulty="easy",
        typical_rejection_reasons=["weak_communication", "no_llm_experience", "no_optimization_skills", "no_eval_framework", "no_product_sense"],
        tier_1_callback_rate=0.15,
        tier_2_callback_rate=0.10,
        tier_3_callback_rate=0.07,
        stepping_stone_roles=["support_engineer", "technical_writer", "devrel"],
        strength_indicators=["communication", "creativity", "llm_fluency", "product_thinking"]
    ),
}

# =============================================================================
# ROLE ALIASES - Handle different ways users might name roles
# =============================================================================

ROLE_ALIASES = {
    # Backend variations
    "backend": "backend_engineer",
    "backend developer": "backend_engineer",
    "backend dev": "backend_engineer",
    "server side developer": "backend_engineer",
    "api developer": "backend_engineer",

    # Frontend variations
    "frontend": "frontend_engineer",
    "frontend developer": "frontend_engineer",
    "frontend dev": "frontend_engineer",
    "front end": "frontend_engineer",
    "front-end": "frontend_engineer",
    "ui developer": "frontend_engineer",
    "react developer": "frontend_engineer",

    # Fullstack variations
    "fullstack": "fullstack_engineer",
    "full stack": "fullstack_engineer",
    "full-stack": "fullstack_engineer",
    "fullstack developer": "fullstack_engineer",

    # DevOps variations
    "devops": "devops_engineer",
    "devops developer": "devops_engineer",
    "platform engineer": "devops_engineer",
    "infrastructure engineer": "devops_engineer",
    "cloud engineer": "devops_engineer",

    # Mobile variations
    "mobile": "mobile_developer",
    "mobile developer": "mobile_developer",
    "android developer": "mobile_developer",
    "ios developer": "mobile_developer",
    "app developer": "mobile_developer",
    "flutter developer": "mobile_developer",

    # QA variations
    "qa": "qa_automation",
    "qa engineer": "qa_automation",
    "tester": "qa_automation",
    "automation tester": "qa_automation",
    "test engineer": "qa_automation",
    "quality assurance": "qa_automation",
    "sdet": "sdet",
    "software development engineer in test": "sdet",

    # Data variations
    "data analyst": "data_analyst",
    "analyst": "data_analyst",
    "business analyst": "business_analyst",
    "ba": "business_analyst",
    "data scientist": "data_scientist",
    "ds": "data_scientist",
    "machine learning engineer": "ml_engineer",
    "ml engineer": "ml_engineer",
    "mle": "ml_engineer",
    "data engineer": "data_engineer",
    "de": "data_engineer",

    # Product variations
    "product manager": "product_manager",
    "pm": "product_manager",
    "associate product manager": "product_manager",
    "apm": "product_manager",
    "product owner": "product_manager",

    # Design variations
    "ux": "ux_designer",
    "ux designer": "ux_designer",
    "user experience": "ux_designer",
    "ui": "ui_designer",
    "ui designer": "ui_designer",
    "user interface": "ui_designer",
    "product designer": "ux_designer",

    # DevRel variations
    "devrel": "devrel",
    "developer advocate": "devrel",
    "developer evangelist": "devrel",
    "community manager": "devrel",
    "technical writer": "technical_writer",
    "tech writer": "technical_writer",
    "documentation engineer": "technical_writer",
    "solutions engineer": "solutions_engineer",
    "solutions architect": "solutions_engineer",
    "sales engineer": "solutions_engineer",
    "presales engineer": "solutions_engineer",

    # Support variations
    "support": "support_engineer",
    "support engineer": "support_engineer",
    "technical support": "support_engineer",
    "customer support": "support_engineer",
    "helpdesk": "support_engineer",
    "sre": "site_reliability_engineer",
    "site reliability": "site_reliability_engineer",
    "reliability engineer": "site_reliability_engineer",

    # Project management
    "project manager": "project_manager",
    "pm": "project_manager",
    "scrum master": "project_manager",
    "delivery manager": "project_manager",

    # Software Developer
    "software developer": "software_developer",
    "software dev": "software_developer",
    "developer": "software_developer",
    "application developer": "software_developer",
    "web developer": "software_developer",

    # SDE
    "sde": "sde",
    "software development engineer": "sde",
    "software engineer": "sde",
    "product engineer": "sde",

    # Generative AI
    "generative ai engineer": "generative_ai_engineer",
    "gen ai engineer": "generative_ai_engineer",
    "llm engineer": "generative_ai_engineer",
    "ai engineer": "generative_ai_engineer",
    "foundation model engineer": "generative_ai_engineer",

    # NLP
    "nlp engineer": "nlp_engineer",
    "natural language processing engineer": "nlp_engineer",
    "nlp developer": "nlp_engineer",
    "text mining engineer": "nlp_engineer",

    # Computer Vision
    "computer vision engineer": "computer_vision_engineer",
    "cv engineer": "computer_vision_engineer",
    "vision engineer": "computer_vision_engineer",
    "image processing engineer": "computer_vision_engineer",

    # AI Research
    "ai research scientist": "ai_research_scientist",
    "ml research scientist": "ai_research_scientist",
    "research scientist": "ai_research_scientist",
    "ai scientist": "ai_research_scientist",
    "deep learning researcher": "ai_research_scientist",

    # MLOps
    "mlops engineer": "mlops_engineer",
    "mlops": "mlops_engineer",
    "ml platform engineer": "mlops_engineer",
    "ai infrastructure engineer": "mlops_engineer",

    # Prompt Engineer
    "prompt engineer": "prompt_engineer",
    "prompt engineering": "prompt_engineer",
    "llm prompt engineer": "prompt_engineer",
    "ai prompt engineer": "prompt_engineer",
}

# =============================================================================
# LOCATION MULTIPLIERS
# =============================================================================

LOCATION_MULTIPLIERS = {
    "bangalore": 1.25,
    "hyderabad": 1.15,
    "pune": 1.10,
    "chennai": 1.05,
    "mumbai": 1.20,
    "delhi_ncr": 1.15,
    "gurgaon": 1.15,
    "noida": 1.10,
    "tier_2": 0.85,
    "remote": 1.0,
    "kolkata": 0.95,
    "ahmedabad": 0.90,
    "jaipur": 0.85,
    "indore": 0.85,
    "coimbatore": 0.90,
    "kochi": 0.90,
}

# =============================================================================
# COLLEGE TIER IMPACT
# =============================================================================

COLLEGE_TIER_IMPACT = {
    CollegeTier.TIER_1: {
        "callback_multiplier": 3.5,
        "salary_premium": 1.15,
        "interview_conversion": 0.40
    },
    CollegeTier.TIER_2: {
        "callback_multiplier": 1.2,
        "salary_premium": 1.0,
        "interview_conversion": 0.25
    },
    CollegeTier.TIER_3: {
        "callback_multiplier": 1.0,
        "salary_premium": 0.90,
        "interview_conversion": 0.15
    }
}

# =============================================================================
# DYNAMIC ROLE FUNCTIONS
# =============================================================================

def normalize_role_name(role_input: str) -> str:
    """
    Convert any user input to canonical role name.
    Handles typos, abbreviations, and variations.
    Returns empty string if no input provided.
    """
    if not role_input:
        return ""

    role_lower = role_input.lower().strip()

    # Check aliases first
    if role_lower in ROLE_ALIASES:
        return ROLE_ALIASES[role_lower]

    # Check exact match in database
    if role_lower in ROLE_DATABASE:
        return role_lower

    # Try partial matching
    for alias, canonical in ROLE_ALIASES.items():
        if alias in role_lower or role_lower in alias:
            return canonical

    # Try database keys
    for key in ROLE_DATABASE.keys():
        if key in role_lower or role_lower in key:
            return key

    # Return as-is if no match (will be handled as unknown)
    return role_lower

def get_role_requirements(role_name: str) -> Optional[RoleRequirements]:
    """Get requirements for any role."""
    canonical = normalize_role_name(role_name)
    return ROLE_DATABASE.get(canonical)

def get_all_roles() -> List[str]:
    """Get list of all supported roles."""
    return list(ROLE_DATABASE.keys())

def get_roles_by_category(category: str) -> List[str]:
    """Get roles filtered by category."""
    return [name for name, req in ROLE_DATABASE.items() if req.role_category == category]

def get_callback_rate(role_name, college_tier: CollegeTier) -> float:
    """Get callback rate for any role and tier.
    Accepts role_name as str or RoleCategory enum."""
    # Handle enum input
    if isinstance(role_name, RoleCategory):
        role_name = role_name.value
    req = get_role_requirements(role_name)
    if not req:
        return 0.05  # Conservative default

    if college_tier == CollegeTier.TIER_1:
        return req.tier_1_callback_rate
    elif college_tier == CollegeTier.TIER_2:
        return req.tier_2_callback_rate
    else:
        return req.tier_3_callback_rate

def get_salary_range(role_name, location: str = "pune", college_tier: CollegeTier = CollegeTier.TIER_3) -> Tuple[float, float]:
    """Get salary range for any role, adjusted for location and tier.
    Accepts role_name as str or RoleCategory enum."""
    # Handle enum input
    if isinstance(role_name, RoleCategory):
        role_name = role_name.value
    req = get_role_requirements(role_name)
    if not req:
        return (3.0, 5.0)

    base_min, base_max = req.salary_range_lpa
    location_mult = LOCATION_MULTIPLIERS.get(location.lower(), 1.0)
    tier_premium = COLLEGE_TIER_IMPACT[college_tier]["salary_premium"]

    return (
        round(base_min * location_mult * tier_premium, 1),
        round(base_max * location_mult * tier_premium, 1)
    )

def is_role_supported(role_name: str) -> bool:
    """Check if a role is in our database."""
    canonical = normalize_role_name(role_name)
    return canonical in ROLE_DATABASE

def suggest_similar_roles(role_name: str) -> List[str]:
    """Suggest similar roles if exact match not found."""
    canonical = normalize_role_name(role_name)
    req = ROLE_DATABASE.get(canonical)

    if req:
        return req.stepping_stone_roles[:3]

    # If unknown, suggest based on keywords
    role_lower = role_name.lower()
    suggestions = []

    if any(word in role_lower for word in ["data", "analyst", "science"]):
        suggestions.extend(["data_analyst", "data_scientist", "data_engineer"])
    elif any(word in role_lower for word in ["ai", "ml", "machine learning", "deep learning", "neural"]):
        suggestions.extend(["ml_engineer", "data_scientist", "generative_ai_engineer"])
    elif any(word in role_lower for word in ["llm", "generative", "prompt", "gpt", "foundation model"]):
        suggestions.extend(["generative_ai_engineer", "prompt_engineer", "nlp_engineer"])
    elif any(word in role_lower for word in ["nlp", "natural language", "text", "chatbot"]):
        suggestions.extend(["nlp_engineer", "generative_ai_engineer", "data_scientist"])
    elif any(word in role_lower for word in ["vision", "image", "cv", "opencv", "object detection"]):
        suggestions.extend(["computer_vision_engineer", "ml_engineer", "data_scientist"])
    elif any(word in role_lower for word in ["research", "scientist", "phd", "academic"]):
        suggestions.extend(["ai_research_scientist", "data_scientist", "ml_engineer"])
    elif any(word in role_lower for word in ["mlops", "ml platform", "model deployment", "model serving"]):
        suggestions.extend(["mlops_engineer", "devops_engineer", "ml_engineer"])
    elif any(word in role_lower for word in ["design", "ux", "ui", "creative"]):
        suggestions.extend(["ux_designer", "ui_designer", "product_designer"])
    elif any(word in role_lower for word in ["write", "content", "doc"]):
        suggestions.extend(["technical_writer", "content_writer", "devrel"])
    elif any(word in role_lower for word in ["manage", "lead", "product"]):
        suggestions.extend(["product_manager", "project_manager", "business_analyst"])
    else:
        suggestions.extend(["backend_engineer", "frontend_engineer", "fullstack_engineer"])

    return suggestions[:3]

def get_role_categories() -> List[str]:
    """Get all role categories."""
    categories = set()
    for req in ROLE_DATABASE.values():
        categories.add(req.role_category)
    return sorted(list(categories))

# =============================================================================
# REALISTIC TIMELINE ESTIMATES (role-specific)
# =============================================================================

REALISTIC_TIMELINES = {
    # Format: (college_tier, current_state, target_role) -> months
    ("tier_3", "no_coding", "backend_engineer"): 14,
    ("tier_3", "basic_python", "backend_engineer"): 10,
    ("tier_3", "qa_manual", "backend_engineer"): 18,
    ("tier_3", "frontend_basic", "backend_engineer"): 12,
    ("tier_3", "backend_engineer", "backend_engineer"): 12,

    ("tier_3", "no_coding", "frontend_engineer"): 8,
    ("tier_3", "basic_javascript", "frontend_engineer"): 6,
    ("tier_3", "ui_designer", "frontend_engineer"): 4,

    ("tier_3", "no_coding", "fullstack_engineer"): 12,
    ("tier_3", "frontend_basic", "fullstack_engineer"): 8,
    ("tier_3", "backend_basic", "fullstack_engineer"): 8,

    ("tier_3", "no_coding", "devops_engineer"): 14,
    ("tier_3", "backend_engineer", "devops_engineer"): 8,
    ("tier_3", "system_admin", "devops_engineer"): 6,

    ("tier_3", "no_coding", "data_analyst"): 6,
    ("tier_3", "excel_user", "data_analyst"): 3,
    ("tier_3", "backend_engineer", "data_analyst"): 4,

    ("tier_3", "no_coding", "data_scientist"): 18,
    ("tier_3", "data_analyst", "data_scientist"): 12,
    ("tier_3", "math_background", "data_scientist"): 10,

    ("tier_3", "no_coding", "data_engineer"): 12,
    ("tier_3", "data_analyst", "data_engineer"): 8,
    ("tier_3", "backend_engineer", "data_engineer"): 6,

    ("tier_3", "no_coding", "ml_engineer"): 20,
    ("tier_3", "data_scientist", "ml_engineer"): 10,
    ("tier_3", "backend_engineer", "ml_engineer"): 14,

    ("tier_3", "no_coding", "qa_automation"): 4,
    ("tier_3", "manual_tester", "qa_automation"): 3,
    ("tier_3", "backend_engineer", "qa_automation"): 2,

    ("tier_3", "no_coding", "product_manager"): 8,
    ("tier_3", "business_analyst", "product_manager"): 6,
    ("tier_3", "developer", "product_manager"): 10,

    ("tier_3", "no_design", "ux_designer"): 8,
    ("tier_3", "graphic_designer", "ux_designer"): 4,
    ("tier_3", "frontend_engineer", "ux_designer"): 6,

    ("tier_3", "no_design", "ui_designer"): 6,
    ("tier_3", "graphic_designer", "ui_designer"): 3,

    ("tier_3", "no_coding", "devrel"): 4,
    ("tier_3", "developer", "devrel"): 2,
    ("tier_3", "technical_writer", "devrel"): 3,

    ("tier_3", "no_coding", "technical_writer"): 3,
    ("tier_3", "developer", "technical_writer"): 2,
    ("tier_3", "content_writer", "technical_writer"): 2,

    ("tier_3", "no_coding", "solutions_engineer"): 8,
    ("tier_3", "support_engineer", "solutions_engineer"): 6,
    ("tier_3", "developer", "solutions_engineer"): 6,

    ("tier_3", "no_coding", "support_engineer"): 2,
    ("tier_3", "customer_facing", "support_engineer"): 1,

    ("tier_3", "no_coding", "business_analyst"): 4,
    ("tier_3", "excel_user", "business_analyst"): 2,
    ("tier_3", "data_analyst", "business_analyst"): 2,

    ("tier_3", "no_coding", "project_manager"): 10,
    ("tier_3", "business_analyst", "project_manager"): 6,
    ("tier_3", "team_lead", "project_manager"): 4,

    ("tier_3", "no_coding", "site_reliability_engineer"): 18,
    ("tier_3", "devops_engineer", "site_reliability_engineer"): 8,
    ("tier_3", "backend_engineer", "site_reliability_engineer"): 12,

    ("tier_3", "no_coding", "mobile_developer"): 10,
    ("tier_3", "frontend_engineer", "mobile_developer"): 6,
    ("tier_3", "java_kotlin", "mobile_developer"): 4,

    ("tier_3", "no_coding", "sdet"): 10,
    ("tier_3", "qa_automation", "sdet"): 6,
    ("tier_3", "backend_engineer", "sdet"): 4,

    # New roles
    ("tier_3", "no_coding", "software_developer"): 10,
    ("tier_3", "basic_python", "software_developer"): 6,
    ("tier_3", "frontend_basic", "software_developer"): 4,

    ("tier_3", "no_coding", "sde"): 18,
    ("tier_3", "backend_engineer", "sde"): 12,
    ("tier_3", "dsa_strong", "sde"): 8,

    ("tier_3", "no_coding", "generative_ai_engineer"): 20,
    ("tier_3", "ml_engineer", "generative_ai_engineer"): 10,
    ("tier_3", "data_scientist", "generative_ai_engineer"): 12,

    ("tier_3", "no_coding", "nlp_engineer"): 20,
    ("tier_3", "data_scientist", "nlp_engineer"): 12,
    ("tier_3", "ml_engineer", "nlp_engineer"): 10,

    ("tier_3", "no_coding", "computer_vision_engineer"): 20,
    ("tier_3", "data_scientist", "computer_vision_engineer"): 12,
    ("tier_3", "ml_engineer", "computer_vision_engineer"): 10,

    ("tier_3", "no_coding", "ai_research_scientist"): 24,
    ("tier_3", "ml_engineer", "ai_research_scientist"): 18,
    ("tier_3", "data_scientist", "ai_research_scientist"): 18,

    ("tier_3", "no_coding", "mlops_engineer"): 18,
    ("tier_3", "devops_engineer", "mlops_engineer"): 8,
    ("tier_3", "ml_engineer", "mlops_engineer"): 10,

    ("tier_3", "no_coding", "prompt_engineer"): 4,
    ("tier_3", "content_writer", "prompt_engineer"): 2,
    ("tier_3", "support_engineer", "prompt_engineer"): 3,
}

def estimate_timeline(college_tier: str, current_state: str, target_role: str) -> int:
    """Estimate months needed for any role transition."""
    key = (college_tier, current_state, target_role)
    return REALISTIC_TIMELINES.get(key, -1)

def get_stepping_stone_suggestions(target_role: str, current_state: str) -> List[Dict]:
    """
    Get stepping stone suggestions for any target role.
    Returns list of dicts with role, timeline, and reasoning.
    """
    req = get_role_requirements(target_role)
    if not req:
        return []

    suggestions = []
    for stepping_role in req.stepping_stone_roles[:3]:
        stepping_req = get_role_requirements(stepping_role)
        if not stepping_req:
            continue

        timeline = estimate_timeline("tier_3", current_state, stepping_role)
        if timeline < 0:
            timeline = 6  # Default

        suggestions.append({
            "role": stepping_role,
            "role_display": stepping_role.replace("_", " ").title(),
            "timeline_months": timeline,
            "salary_range": stepping_req.salary_range_lpa,
            "difficulty": stepping_req.hiring_difficulty,
            "callback_rate_tier3": stepping_req.tier_3_callback_rate,
            "reasoning": f"{stepping_role.replace('_', ' ').title()} is more accessible and builds skills needed for {target_role.replace('_', ' ').title()}"
        })

    return suggestions
