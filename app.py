import streamlit as st
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import CareerGPS
from data.market_data import (
    get_all_roles, get_roles_by_category, is_role_supported,
    normalize_role_name, suggest_similar_roles, get_role_requirements
)

st.set_page_config(
    page_title="CareerGPS - Dynamic Career Navigation",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4a4a6a;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #16213e;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #e0e0e0;
    }
    .task-box {
        background-color: #f0f4f8;
        border-left: 4px solid #16213e;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .danger-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #0d6efd;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #16213e;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #6c757d;
    }
    .role-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.3rem;
        text-align: center;
        cursor: pointer;
    }
    .role-card:hover {
        background-color: #e9ecef;
        border-color: #16213e;
    }
    .footer {
        text-align: center;
        color: #6c757d;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "gps" not in st.session_state:
    st.session_state.gps = CareerGPS()
if "report" not in st.session_state:
    st.session_state.report = None
if "page" not in st.session_state:
    st.session_state.page = "input"

# Header
st.markdown('<div class="main-header">🧭 CareerGPS</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Evidence-Based Career Navigation for ANY Path</div>', unsafe_allow_html=True)

# Role exploration helper
all_roles = get_all_roles()
role_categories = {
    "engineering": ["backend_engineer", "frontend_engineer", "fullstack_engineer", "devops_engineer", "mobile_developer", "site_reliability_engineer", "software_developer", "sde"],
    "qa": ["qa_automation", "sdet"],
    "data": ["data_analyst", "data_scientist", "data_engineer", "ml_engineer", "generative_ai_engineer", "nlp_engineer", "computer_vision_engineer", "ai_research_scientist", "mlops_engineer"],
    "product": ["product_manager"],
    "design": ["ux_designer", "ui_designer"],
    "devrel": ["devrel", "technical_writer", "solutions_engineer", "prompt_engineer"],
    "support": ["support_engineer"],
    "business": ["business_analyst", "project_manager"]
}

# Navigation
if st.session_state.page == "input":
    st.markdown('<div class="section-header">Choose Your Career Path</div>', unsafe_allow_html=True)

    # Role selection method
    selection_method = st.radio(
        "How do you want to select your target role?",
        ["Browse by Category", "Search by Name", "I am not sure - help me explore"],
        horizontal=True
    )

    target_role = None

    if selection_method == "Browse by Category":
        col1, col2 = st.columns(2)

        with col1:
            category = st.selectbox(
                "Select Category",
                ["Engineering", "QA / Testing", "Data", "Product", "Design", "DevRel / Content", "Support", "Business"]
            )

        cat_map = {
            "Engineering": "engineering",
            "QA / Testing": "qa",
            "Data": "data",
            "Product": "product",
            "Design": "design",
            "DevRel / Content": "devrel",
            "Support": "support",
            "Business": "business"
        }

        with col2:
            roles_in_cat = role_categories.get(cat_map.get(category, "engineering"), [])
            role_display_names = [r.replace("_", " ").title() for r in roles_in_cat]
            selected_display = st.selectbox("Select Role", role_display_names)
            target_role = roles_in_cat[role_display_names.index(selected_display)] if selected_display else None

        # Show role details
        if target_role:
            req = get_role_requirements(target_role)
            if req:
                st.info(f"**{target_role.replace('_', ' ').title()}** | Difficulty: {req.hiring_difficulty.title()} | "
                       f"Salary: ₹{req.salary_range_lpa[0]}-{req.salary_range_lpa[1]} LPA | "
                       f"Experience: {req.min_experience_months} months min")

    elif selection_method == "Search by Name":
        target_role_input = st.text_input(
            "Type your target role",
            placeholder="e.g., Data Scientist, UX Designer, Product Manager, DevOps Engineer",
            help="Type any role name. We support 25+ roles and will suggest similar ones if not found."
        )

        if target_role_input:
            normalized = normalize_role_name(target_role_input)
            if is_role_supported(target_role_input):
                target_role = normalized
                req = get_role_requirements(target_role)
                st.success(f"✅ Found: **{target_role.replace('_', ' ').title()}** | Category: {req.role_category.title()}")
            else:
                similar = suggest_similar_roles(target_role_input)
                st.warning(f"⚠️ '{target_role_input}' not in database. Did you mean one of these?")
                cols = st.columns(len(similar))
                for i, sim in enumerate(similar):
                    with cols[i]:
                        sim_req = get_role_requirements(sim)
                        if st.button(f"{sim.replace('_', ' ').title()}", key=f"sim_{i}"):
                            target_role = sim
                            st.rerun()

    elif selection_method == "I am not sure - help me explore":
        st.markdown("#### Let's find your path based on your strengths")

        col1, col2 = st.columns(2)
        with col1:
            likes_coding = st.checkbox("I enjoy writing code")
            likes_data = st.checkbox("I enjoy working with data/numbers")
            likes_design = st.checkbox("I enjoy visual design/creativity")
            likes_writing = st.checkbox("I enjoy writing/teaching")
        with col2:
            likes_people = st.checkbox("I enjoy working with people")
            likes_systems = st.checkbox("I enjoy systems/processes")
            likes_problems = st.checkbox("I enjoy solving problems")
            likes_leading = st.checkbox("I enjoy leading/managing")

        if st.button("🔍 Suggest Roles for Me"):
            suggestions = []
            if likes_coding and likes_systems:
                suggestions.extend(["backend_engineer", "devops_engineer", "site_reliability_engineer", "sde"])
            if likes_coding and likes_design:
                suggestions.extend(["frontend_engineer", "mobile_developer", "fullstack_engineer", "software_developer"])
            if likes_data and likes_coding:
                suggestions.extend(["data_scientist", "data_engineer", "ml_engineer", "generative_ai_engineer", "nlp_engineer", "computer_vision_engineer", "mlops_engineer"])
            if likes_data and not likes_coding:
                suggestions.extend(["data_analyst", "business_analyst"])
            if likes_design and not likes_coding:
                suggestions.extend(["ux_designer", "ui_designer"])
            if likes_writing and likes_coding:
                suggestions.extend(["devrel", "technical_writer", "prompt_engineer"])
            if likes_people and likes_problems and not likes_coding:
                suggestions.extend(["product_manager", "solutions_engineer", "project_manager"])
            if likes_people and not likes_coding and not likes_problems:
                suggestions.extend(["support_engineer", "business_analyst"])
            if likes_coding and likes_problems and not likes_systems:
                suggestions.extend(["qa_automation", "sdet"])

            suggestions = list(dict.fromkeys(suggestions))  # Remove duplicates

            st.markdown("#### Suggested Roles:")
            cols = st.columns(min(3, len(suggestions)))
            for i, sug in enumerate(suggestions[:6]):
                with cols[i % 3]:
                    sug_req = get_role_requirements(sug)
                    if st.button(f"🎯 {sug.replace('_', ' ').title()}", key=f"sug_{i}"):
                        target_role = sug
                        st.session_state.selected_role = sug
                        st.rerun()

    # If role is selected, show the rest of the form
    if target_role or st.session_state.get("selected_role"):
        if not target_role:
            target_role = st.session_state.get("selected_role")

        st.markdown("---")
        st.markdown('<div class="section-header">Your Profile</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Basic Information")

            college_tier = st.selectbox(
                "College Tier *",
                ["Tier 3 (Private/Unknown)", "Tier 2 (State/Recognized Private)", "Tier 1 (IIT/NIT/BITS)"]
            )

            location = st.selectbox(
                "Preferred Location",
                ["Pune", "Bangalore", "Hyderabad", "Chennai", "Mumbai", "Delhi NCR", "Remote", "Tier 2 City"]
            )

            experience_months = st.slider(
                "Experience (months)",
                0, 36, 0,
                help="Include internships"
            )

            cgpa = st.slider("CGPA / Percentage", 0.0, 10.0, 7.2, step=0.1)

        with col2:
            st.subheader("Skills & Evidence")

            # Dynamic skill sliders based on role
            req = get_role_requirements(target_role)
            if req:
                st.caption(f"Key skills for {target_role.replace('_', ' ').title()}:")
                key_skills = req.required_skills[:5]
                skill_ratings = {}
                for skill in key_skills:
                    display_name = skill.replace("_", " ").title()
                    skill_ratings[skill] = st.slider(f"{display_name} (self-rated)", 1, 5, 2)

                # Add communication for all roles
                communication = st.slider("Communication (self-rated)", 1, 5, 3)
                skill_ratings["communication"] = communication
            else:
                python_skill = st.slider("Python (self-rated)", 1, 5, 2)
                communication = st.slider("Communication (self-rated)", 1, 5, 3)
                skill_ratings = {"python": python_skill, "communication": communication}

            st.markdown("---")

            github_url = st.text_input(
                "GitHub / Portfolio URL",
                placeholder="https://github.com/username or portfolio link",
                help="Public repos/portfolio only. We cannot assess private content."
            )

            has_internship = st.checkbox("Have internship experience?")
            internship_type = "none"
            if has_internship:
                internship_type = st.selectbox(
                    "Internship Type",
                    ["Development", "Testing/QA", "Support", "Data/Analytics", "Design", "Product", "Business", "Other"]
                )

            num_projects = st.number_input("Number of projects", 0, 20, 2)
            has_deployed = st.checkbox("Any deployed/published projects?")

        st.markdown("---")

        # Build profile
        if st.button("🚀 Generate My Career Report", type="primary", use_container_width=True):
            tier_map = {
                "Tier 3 (Private/Unknown)": "tier_3",
                "Tier 2 (State/Recognized Private)": "tier_2",
                "Tier 1 (IIT/NIT/BITS)": "tier_1"
            }

            loc_map = {
                "Pune": "pune", "Bangalore": "bangalore", "Hyderabad": "hyderabad",
                "Chennai": "chennai", "Mumbai": "mumbai", "Delhi NCR": "delhi_ncr",
                "Remote": "remote", "Tier 2 City": "tier_2"
            }

            # Determine current state
            current_state = "unknown"
            if has_internship:
                if "test" in internship_type.lower():
                    current_state = "qa_manual"
                elif "develop" in internship_type.lower():
                    current_state = "basic_coding"
                elif "design" in internship_type.lower():
                    current_state = "design_intern"
                elif "data" in internship_type.lower():
                    current_state = "data_intern"
                elif "product" in internship_type.lower():
                    current_state = "product_intern"
                else:
                    current_state = "internship"
            else:
                if skill_ratings.get("python", 0) >= 2:
                    current_state = "basic_python"
                elif skill_ratings.get("communication", 0) >= 3:
                    current_state = "communication_strong"
                else:
                    current_state = "no_coding"

            profile = {
                "target_role": target_role,
                "college_tier": tier_map[college_tier],
                "location": loc_map[location],
                "experience_months": experience_months,
                "current_state": current_state,
                "self_assessment": skill_ratings,
                "github": {
                    "url": github_url,
                    "accessible": bool(github_url),
                    "num_repos": num_projects,
                    "total_commits": num_projects * 15,
                    "languages": {"python": num_projects * 200} if skill_ratings.get("python", 0) > 1 else {},
                    "has_readme": num_projects > 0,
                    "has_tests": False,
                    "has_error_handling": False,
                    "avg_function_length": 50,
                    "max_function_length": 150
                },
                "resume": {
                    "internship": {
                        "has_internship": has_internship,
                        "type": internship_type.lower(),
                        "duration_months": 3 if has_internship else 0
                    },
                    "projects": [
                        {"technologies_used": list(skill_ratings.keys())[:3], "deployed": has_deployed}
                        for _ in range(num_projects)
                    ],
                    "skills": list(skill_ratings.keys())[:5],
                    "cgpa": cgpa,
                    "college_tier": tier_map[college_tier]
                },
                "diagnostics": {}
            }

            with st.spinner(f"Analyzing your profile for {target_role.replace('_', ' ').title()} against real 2026 market data..."):
                report = st.session_state.gps.process_profile(profile)
                st.session_state.report = report
                st.session_state.page = "report"
                st.rerun()

elif st.session_state.page == "report":
    report = st.session_state.report

    # Parse and display report
    lines = report.split("\n")

    st.markdown("---")

    for line in lines:
        line = line.strip()

        if "WHERE YOU ARE" in line:
            st.markdown('<div class="section-header">📍 Where You Are</div>', unsafe_allow_html=True)
            continue

        if "WHERE YOU CAN GO" in line:
            st.markdown('<div class="section-header">🎯 Where You Can Go</div>', unsafe_allow_html=True)
            continue

        if "YOUR 3 TASKS" in line:
            st.markdown('<div class="section-header">📋 Your 3 Tasks This Week</div>', unsafe_allow_html=True)
            continue

        if "=" * 20 in line or "CareerGPS" in line or "Data sourced" in line or "Supports 25" in line:
            continue

        if not line:
            continue

        # Format based on content
        if line.startswith("⚠️") or "CONTRADICTION" in line or "GAPS DETECTED" in line:
            st.markdown(f'<div class="warning-box">{line}</div>', unsafe_allow_html=True)
        elif line.startswith("🔴") or "CRITICAL" in line:
            st.markdown(f'<div class="danger-box">{line}</div>', unsafe_allow_html=True)
        elif line.startswith("✅"):
            st.markdown(f'<div class="success-box">{line}</div>', unsafe_allow_html=True)
        elif line.startswith("💡") or line.startswith("WHY:"):
            st.markdown(f'<div class="info-box">{line}</div>', unsafe_allow_html=True)
        elif line.startswith("📋") or line.startswith("  1.") or line.startswith("  2.") or line.startswith("  3."):
            if "→" in line:
                st.markdown(f'<div class="task-box">{line}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="task-box"><strong>{line}</strong></div>', unsafe_allow_html=True)
        elif line.startswith("  •") or line.startswith("     •"):
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{line}")
        elif line.startswith("  ") and not line.startswith("   "):
            st.markdown(f"**{line.strip()}**")
        else:
            st.markdown(line)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Input", use_container_width=True):
            st.session_state.page = "input"
            st.session_state.selected_role = None
            st.rerun()
    with col2:
        if st.button("📅 Simulate Week 1 Check-in", type="primary", use_container_width=True):
            st.session_state.page = "checkin"
            st.rerun()

elif st.session_state.page == "checkin":
    st.markdown('<div class="section-header">📅 Weekly Check-in Simulator</div>', unsafe_allow_html=True)

    st.info("This simulates how CareerGPS tracks your progress week-over-week for ANY career path.")

    week = st.number_input("Week Number", 1, 52, 1)

    st.subheader("What did you complete this week?")

    col1, col2, col3 = st.columns(3)

    with col1:
        learning_tasks = st.number_input("Learning tasks completed", 0, 20, 2)
        project_tasks = st.number_input("Project/portfolio tasks completed", 0, 20, 0)

    with col2:
        practice_tasks = st.number_input("Practice/coding tasks", 0, 20, 1)
        application_tasks = st.number_input("Job applications sent", 0, 50, 0)

    with col3:
        responses = st.number_input("Responses received", 0, 50, 0)
        interviews = st.number_input("Interviews attended", 0, 20, 0)

    if st.button("Analyze My Week", type="primary", use_container_width=True):
        has_project = project_tasks > 0
        has_application = application_tasks > 0
        only_learning = learning_tasks > 0 and project_tasks == 0 and practice_tasks == 0

        if only_learning:
            progress_type = "⚠️ COMPLIANCE"
            message = "You have been learning but not applying. This is the #1 trap."
            box_class = "warning-box"
        elif has_project and has_application:
            progress_type = "🚀 BREAKTHROUGH"
            message = "You are building AND applying. This is the winning combination."
            box_class = "success-box"
        elif has_project:
            progress_type = "✅ REAL PROGRESS"
            message = "You are building real skills. Keep testing the market too."
            box_class = "success-box"
        else:
            progress_type = "🔄 MOTION"
            message = "You are active but not building or applying enough."
            box_class = "warning-box"

        st.markdown(f'<div class="{box_class}"><h4>{progress_type}</h4><p>{message}</p></div>', unsafe_allow_html=True)

        response_rate = responses / application_tasks if application_tasks > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{application_tasks}</div><div class="metric-label">Applications</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{responses}</div><div class="metric-label">Responses</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{response_rate:.1%}</div><div class="metric-label">Response Rate</div></div>', unsafe_allow_html=True)

        if application_tasks > 10 and responses == 0 and week > 2:
            st.markdown('<div class="danger-box">🚨 APPLICATION BLACK HOLE: 10+ applications, 0 responses. Your profile is not passing screening. Stop applying. Fix your resume and projects first.</div>', unsafe_allow_html=True)

        if only_learning and learning_tasks >= 3:
            st.markdown('<div class="danger-box">🚨 STAGNATION ALERT: 3+ weeks of learning without building. You must ship projects NOW.</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">📋 Next Week 3 Tasks</div>', unsafe_allow_html=True)

        if only_learning:
            tasks = [
                "STOP watching tutorials. Build ONE project feature this week.",
                "Deploy your project and add it to your portfolio/resume.",
                "Apply to 3 jobs with your new project link."
            ]
        elif application_tasks > 10 and responses == 0:
            tasks = [
                "Get 2 industry professionals to review your portfolio. Implement their top 3 suggestions.",
                "Rewrite your resume to match 5 real job descriptions word-for-word.",
                "Do 1 mock interview and record yourself. Identify 2 weaknesses."
            ]
        else:
            tasks = [
                "Build one portfolio piece using your target skill (Week focus)",
                "Practice 3 problems/tasks related to your weak areas",
                "Apply to 3-5 jobs with personalized cover notes"
            ]

        for i, task in enumerate(tasks, 1):
            st.markdown(f'<div class="task-box"><strong>{i}.</strong> {task}</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("← Back to Report", use_container_width=True):
        st.session_state.page = "report"
        st.rerun()

# Footer
st.markdown('<div class="footer">CareerGPS | Supports 25+ roles across 8 categories | Uses aggregated industry data for guidance | Built for Applied AI Capstone</div>', unsafe_allow_html=True)
