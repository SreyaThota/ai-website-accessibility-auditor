import os
import time
import requests
import streamlit as st

st.set_page_config(
    page_title="AI Accessibility Auditor | WCAG 2.1 & EAA Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")

# Custom CSS for dark-mode enterprise theme
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .hero-card {
        background: linear-gradient(135deg, #091e3a 0%, #1e1b4b 60%, #172554 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
    }
    .hero-title { font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 0; }
    .hero-subtitle { color: #94a3b8; font-size: 0.95rem; margin-top: 6px; }
    
    .status-badge {
        display: inline-flex;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 10px;
    }
    .badge-pass { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-fail { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    
    .score-circle {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: #1e293b;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #334155;
        text-align: center;
    }
    .score-number { font-size: 3.8rem; font-weight: 800; line-height: 1; }
    .score-green { color: #10b981; }
    .score-amber { color: #f59e0b; }
    .score-red { color: #ef4444; }

    .issue-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .sev-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .sev-critical { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.5); }
    .sev-major { background: rgba(249, 115, 22, 0.2); color: #fdba74; border: 1px solid rgba(249, 115, 22, 0.5); }
    .sev-moderate { background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.5); }
    .sev-minor { background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.5); }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar: Controls & System Health
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/visible--v1.png", width=64)
    st.title("A11y Auditor Core")
    st.caption("WCAG 2.1 AA & European Accessibility Act Engine")

    try:
        health_res = requests.get(f"{BACKEND_URL}/health", timeout=2.0)
        if health_res.status_code == 200:
            h = health_res.json()
            st.success("🟢 **API Backend Connected**")
            st.info(f"Standards: `{', '.join(h['standards'])}`\n\nVision AI: `{h['vision_provider']}`")
        else:
            st.warning("🟡 Backend status: Non-200")
    except Exception:
        st.error("🔴 **Backend Offline**\nStart FastAPI via `uvicorn backend.app.main:app`")

    st.divider()

    st.subheader("⚙️ Inspection Modules")
    chk_contrast = st.checkbox("Multi-Modal Pixel Contrast Analysis", value=True, help="Samples pixel bounding boxes over gradients and images.")
    chk_ai_alt = st.checkbox("Automated AI Alt-Text Generation", value=True, help="Invokes Vision LLM to propose descriptive alt text.")
    chk_targets = st.checkbox("Touch Target Size Checks (44x44px)", value=True, help="Validates interactive dimensions per WCAG 2.5.5 / 2.5.8.")

    st.divider()
    st.caption("AI Website Accessibility Auditor v1.0.0")

# Main Header Banner
st.markdown(
    """
    <div class="hero-card">
        <h1 class="hero-title">🛡️ AI Website Accessibility Auditor</h1>
        <div class="hero-subtitle">
            Automated compliance engine combining Headless Chromium crawling, DOM tree validation,
            and Multi-Modal Computer Vision for WCAG 2.1 Level AA & European Accessibility Act (EAA) conformance.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Input Section: Preset Buttons & URL Bar
st.subheader("🌐 Target Inspection URL")
col_preset1, col_preset2, col_preset3 = st.columns(3)

target_input = "preset:inaccessible_portal"
if col_preset1.button("🔴 Inaccessible University Portal (Demo)", use_container_width=True):
    target_input = "preset:inaccessible_portal"
if col_preset2.button("🟢 Compliant Portal (WCAG 2.1 AA & EAA)", use_container_width=True):
    target_input = "preset:compliant_portal"
if col_preset3.button("🌐 W3C WAI Example Page", use_container_width=True):
    target_input = "https://www.w3.org/WAI/demos/bad/before/home.html"

url_to_audit = st.text_input("Enter URL or select demo preset above:", value=target_input)

if st.button("🚀 Run Full Accessibility Audit", type="primary", use_container_width=True):
    with st.spinner("Executing headless browser crawl, DOM tree validation & multi-modal contrast analysis..."):
        payload = {
            "url": url_to_audit,
            "check_visual_contrast": chk_contrast,
            "generate_ai_alt_text": chk_ai_alt,
            "check_touch_targets": chk_targets,
        }
        try:
            res = requests.post(f"{BACKEND_URL}/audit", json=payload, timeout=60.0)
            if res.status_code == 200:
                st.session_state["latest_report"] = res.json()
                st.success("Audit completed successfully!")
            else:
                st.error(f"Audit API Error (HTTP {res.status_code}): {res.text}")
        except Exception as e:
            st.error(f"Failed to communicate with audit backend: {e}")

# Render Results
if "latest_report" in st.session_state:
    report = st.session_state["latest_report"]
    summary = report["summary"]
    issues = report["issues"]

    st.markdown("---")
    st.subheader("📊 Executive Compliance Scorecard")

    col_gauge, col_m1, col_m2, col_m3, col_m4 = st.columns([1.5, 1, 1, 1, 1])

    score = summary["overall_score"]
    score_class = "score-green" if score >= 85 else "score-amber" if score >= 60 else "score-red"

    with col_gauge:
        st.markdown(
            f"""
            <div class="score-circle">
                <div class="score-number {score_class}">{int(score)}</div>
                <div style="font-size: 0.9rem; color: #94a3b8; font-weight:600; text-transform:uppercase;">Compliance Index</div>
                <div style="margin-top: 10px;">
                    <span class="status-badge {'badge-pass' if 'PASS' in summary['eea_compliance_status'] else 'badge-fail'}">
                        {summary['eea_compliance_status']}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_m1:
        st.metric("👁️ Perceivable", f"{int(summary['perceivable_score'])}%", help="Alt text, contrast, structural text alternatives")
    with col_m2:
        st.metric("⌨️ Operable", f"{int(summary['operable_score'])}%", help="Touch target sizes, heading outlines, link purposes")
    with col_m3:
        st.metric("🧠 Understandable", f"{int(summary['understandable_score'])}%", help="Page language, input form labels")
    with col_m4:
        st.metric("🔧 Robust", f"{int(summary['robust_score'])}%", help="ARIA references, accessible button names")

    st.markdown(
        f"""
        <div style="display: flex; gap: 12px; margin-top: 16px; margin-bottom: 24px; align-items: center;">
            <span class="sev-tag sev-critical">{summary['critical_issues']} Critical</span>
            <span class="sev-tag sev-major">{summary['major_issues']} Major</span>
            <span class="sev-tag sev-moderate">{summary['moderate_issues']} Moderate</span>
            <span class="sev-tag sev-minor">{summary['minor_issues']} Minor</span>
            <span style="font-size: 0.85rem; color: #94a3b8; margin-left: auto;">⏱️ Scan duration: {summary['duration_seconds']}s</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Export Buttons
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.link_button("📑 View Interactive HTML Report", f"{BACKEND_URL}/reports/{report['job_id']}/html", use_container_width=True)
    with col_dl2:
        st.link_button("💾 Download JSON Data (API Payload)", f"{BACKEND_URL}/reports/{report['job_id']}/json", use_container_width=True)

    # Filterable Issue Explorer
    st.subheader(f"🔍 Accessibility Barriers & Code Remediations ({len(issues)})")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_severity = st.multiselect(
            "Filter by Severity",
            options=["Critical", "Major", "Moderate", "Minor"],
            default=["Critical", "Major", "Moderate"],
        )
    with col_f2:
        selected_principle = st.multiselect(
            "Filter by WCAG Principle",
            options=["Perceivable", "Operable", "Understandable", "Robust"],
            default=["Perceivable", "Operable", "Understandable", "Robust"],
        )

    filtered_issues = [
        i for i in issues
        if i["severity"] in selected_severity and i["principle"] in selected_principle
    ]

    for idx, issue in enumerate(filtered_issues, 1):
        sev_cls = f"sev-{issue['severity'].lower()}"
        with st.expander(f"#{idx} [{issue['severity']}] {issue['description']} ({issue['rule_id']})", expanded=(issue['severity'] == "Critical")):
            st.markdown(f"**Failure Summary:** {issue['failure_summary']}")
            st.code(f"Selector: {issue['element_selector']} | Tag: <{issue['element_tag']}>", language="css")

            rem = issue["remediation"]
            st.markdown(f"**Criterion:** `{rem['wcag_criterion']}` — [W3C Understanding Doc]({rem['wcag_url']})")
            
            st.markdown("**Current Offending Code:**")
            st.code(rem["current_code"], language="html")

            st.markdown("**Recommended WCAG-Compliant Remediation:**")
            st.code(rem["recommended_code"], language="html")

            st.caption(f"💡 Technical Rationale: {rem['explanation']}")
