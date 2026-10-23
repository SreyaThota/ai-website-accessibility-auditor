import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from jinja2 import Template
from auditor.models.schemas import (
    AccessibilityIssue,
    AuditSummary,
    AuditReport,
    WCAGPrinciple,
    Severity,
    CategoryScore,
)
from auditor.core.config import settings
from auditor.core.logging import logger

HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accessibility Audit Report | {{ report.url }}</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #182234;
            --border: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --critical: #ef4444;
            --major: #f97316;
            --moderate: #f59e0b;
            --minor: #3b82f6;
            --success: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background: var(--bg-primary); color: var(--text-primary); line-height: 1.6; padding: 32px 24px; }
        .container { max-width: 1200px; margin: 0 auto; }
        
        /* Header & Meta */
        .header { display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 24px; border-bottom: 1px solid var(--border); margin-bottom: 32px; flex-wrap: wrap; gap: 16px; }
        .title-block h1 { font-size: 2rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
        .url-badge { color: #38bdf8; font-family: monospace; font-size: 0.95rem; margin-top: 6px; word-break: break-all; }
        .meta-badges { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
        .badge { display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; }
        .badge-eaa-pass { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .badge-eaa-fail { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }

        /* Executive Grid */
        .exec-grid { display: grid; grid-template-columns: 280px 1fr; gap: 24px; margin-bottom: 36px; }
        @media (max-width: 850px) { .exec-grid { grid-template-columns: 1fr; } }
        .score-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center; }
        .score-dial { font-size: 4rem; font-weight: 800; line-height: 1; }
        .score-high { color: var(--success); }
        .score-mid { color: var(--moderate); }
        .score-low { color: var(--critical); }
        .score-label { color: var(--text-secondary); font-size: 0.88rem; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.05em; }

        .metrics-panel { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
        .metric-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
        .metric-title { font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary); }
        .metric-value { font-size: 1.8rem; font-weight: 700; margin-top: 4px; }

        /* Severity breakdown */
        .severity-pills { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
        .sev-pill { padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; }
        .sev-critical { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.5); }
        .sev-major { background: rgba(249, 115, 22, 0.2); color: #fdba74; border: 1px solid rgba(249, 115, 22, 0.5); }
        .sev-moderate { background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.5); }
        .sev-minor { background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.5); }

        /* Issues List */
        .section-title { font-size: 1.35rem; font-weight: 700; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .issue-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 18px; transition: transform 0.15s ease; }
        .issue-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; flex-wrap: wrap; gap: 10px; }
        .issue-rule { font-family: monospace; font-size: 0.85rem; color: #38bdf8; }
        .issue-desc { font-size: 1.05rem; font-weight: 600; color: #fff; margin-bottom: 6px; }
        .issue-failure { color: #cbd5e1; font-size: 0.9rem; margin-bottom: 14px; }
        .issue-target { background: #0f172a; padding: 6px 12px; border-radius: 6px; font-family: monospace; font-size: 0.82rem; color: #e2e8f0; margin-bottom: 14px; display: inline-block; }

        /* Code remediation box */
        .remediation-box { background: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; margin-top: 10px; }
        .remediation-title { font-size: 0.8rem; text-transform: uppercase; color: #10b981; font-weight: 700; margin-bottom: 8px; }
        pre { background: #020617; padding: 10px; border-radius: 6px; font-size: 0.85rem; overflow-x: auto; color: #a7f3d0; margin-bottom: 8px; }
        .remediation-expl { font-size: 0.85rem; color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="title-block">
                <h1>🛡️ AI Website Accessibility Audit Report</h1>
                <div class="url-badge">{{ report.url }}</div>
                <div class="meta-badges">
                    <span class="badge {% if 'PASS' in report.summary.eea_compliance_status %}badge-eaa-pass{% else %}badge-eaa-fail{% endif %}">
                        {{ report.summary.eea_compliance_status }}
                    </span>
                    <span class="badge" style="background: rgba(148, 163, 184, 0.15); color: #cbd5e1;">
                        WCAG 2.1 Level {{ report.summary.wcag_level_conformance }}
                    </span>
                    <span class="badge" style="background: rgba(148, 163, 184, 0.15); color: #cbd5e1;">
                        Job ID: {{ report.job_id }}
                    </span>
                    <span class="badge" style="background: rgba(148, 163, 184, 0.15); color: #cbd5e1;">
                        Duration: {{ report.summary.duration_seconds }}s
                    </span>
                </div>
            </div>
        </div>

        <!-- Executive Grid -->
        <div class="exec-grid">
            <div class="score-card">
                <div class="score-dial {% if report.summary.overall_score >= 85 %}score-high{% elif report.summary.overall_score >= 60 %}score-mid{% else %}score-low{% endif %}">
                    {{ report.summary.overall_score|round(0)|int }}
                </div>
                <div class="score-label">Overall A11y Score</div>
                <div class="severity-pills" style="margin-top: 16px;">
                    <span class="sev-pill sev-critical">{{ report.summary.critical_issues }} Critical</span>
                    <span class="sev-pill sev-major">{{ report.summary.major_issues }} Major</span>
                    <span class="sev-pill sev-moderate">{{ report.summary.moderate_issues }} Mod</span>
                </div>
            </div>

            <div class="metrics-panel">
                <div class="metric-card">
                    <div class="metric-title">👁️ Perceivable</div>
                    <div class="metric-value">{{ report.summary.perceivable_score|round(0)|int }}%</div>
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">Alt-text, Contrast, Visuals</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">⌨️ Operable</div>
                    <div class="metric-value">{{ report.summary.operable_score|round(0)|int }}%</div>
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">Touch Targets, Headings, Links</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">🧠 Understandable</div>
                    <div class="metric-value">{{ report.summary.understandable_score|round(0)|int }}%</div>
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">Language, Form Labels</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">🔧 Robust</div>
                    <div class="metric-value">{{ report.summary.robust_score|round(0)|int }}%</div>
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">ARIA References, Button Names</div>
                </div>
            </div>
        </div>

        <!-- Issues List -->
        <div class="section-title">
            <span>Identified Violations & Recommended Fixes ({{ report.issues|length }})</span>
        </div>

        {% for issue in report.issues %}
        <div class="issue-card">
            <div class="issue-header">
                <div>
                    <span class="issue-rule">{{ issue.rule_id }} • {{ issue.remediation.wcag_criterion }}</span>
                    <div class="issue-desc">{{ issue.description }}</div>
                </div>
                <span class="sev-pill {% if issue.severity.value == 'Critical' %}sev-critical{% elif issue.severity.value == 'Major' %}sev-major{% elif issue.severity.value == 'Moderate' %}sev-moderate{% else %}sev-minor{% endif %}">
                    {{ issue.severity.value }}
                </span>
            </div>
            
            <div class="issue-failure">{{ issue.failure_summary }}</div>
            <div class="issue-target">Selector: {{ issue.element_selector }}</div>

            <!-- Code Remediation -->
            <div class="remediation-box">
                <div class="remediation-title">Recommended Code Remediation:</div>
                <pre><code>{{ issue.remediation.recommended_code }}</code></pre>
                <div class="remediation-expl">{{ issue.remediation.explanation }}</div>
            </div>
        </div>
        {% endfor %}

    </div>
</body>
</html>
"""

class ReportGenerator:
    """
    Compiles raw DOM and Computer Vision findings into structured Pydantic DTOs,
    calculates objective compliance indexes, and writes machine-readable JSON & interactive HTML.
    """

    @classmethod
    def generate_report(
        cls,
        job_id: str,
        url: str,
        issues: List[AccessibilityIssue],
        duration_seconds: float,
        screenshot_path: Optional[str] = None,
        a11y_tree: Optional[Dict[str, Any]] = None,
    ) -> AuditReport:
        """Computes executive scorecards and constructs the full AuditReport."""
        # 1. Calculate severity totals
        crit_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        maj_count = sum(1 for i in issues if i.severity == Severity.MAJOR)
        mod_count = sum(1 for i in issues if i.severity == Severity.MODERATE)
        min_count = sum(1 for i in issues if i.severity == Severity.MINOR)

        # 2. Weighted overall score calculation (starts at 100)
        deduction = (crit_count * 15.0) + (maj_count * 8.0) + (mod_count * 4.0) + (min_count * 1.5)
        overall_score = max(0.0, min(100.0, round(100.0 - deduction, 1)))

        # 3. Principle sub-scores
        def calc_principle_score(p: WCAGPrinciple) -> float:
            p_issues = [i for i in issues if i.principle == p]
            if not p_issues:
                return 100.0
            p_deduction = sum(
                15.0 if i.severity == Severity.CRITICAL else
                8.0 if i.severity == Severity.MAJOR else
                4.0 if i.severity == Severity.MODERATE else 1.5
                for i in p_issues
            )
            return max(0.0, min(100.0, round(100.0 - p_deduction, 1)))

        p_score = calc_principle_score(WCAGPrinciple.PERCEIVABLE)
        o_score = calc_principle_score(WCAGPrinciple.OPERABLE)
        u_score = calc_principle_score(WCAGPrinciple.UNDERSTANDABLE)
        r_score = calc_principle_score(WCAGPrinciple.ROBUST)

        # 4. Conformance classifications
        if crit_count == 0 and maj_count == 0 and overall_score >= 90.0:
            wcag_conformance = "COMPLIANT_AA"
        elif crit_count == 0 and overall_score >= 70.0:
            wcag_conformance = "PARTIAL_AA"
        else:
            wcag_conformance = "NON_COMPLIANT"

        # European Accessibility Act (EAA) compliance: strictly forbids critical blocking barriers
        if crit_count == 0 and overall_score >= 80.0:
            eea_status = "PASS - Meets EAA Mandates (EN 301 549)"
        else:
            eea_status = f"FAIL - {crit_count} Critical Barriers Detected"

        summary = AuditSummary(
            url=url,
            overall_score=overall_score,
            wcag_level_conformance=wcag_conformance,
            eea_compliance_status=eea_status,
            perceivable_score=p_score,
            operable_score=o_score,
            understandable_score=u_score,
            robust_score=r_score,
            total_issues=len(issues),
            critical_issues=crit_count,
            major_issues=maj_count,
            moderate_issues=mod_count,
            minor_issues=min_count,
            duration_seconds=round(duration_seconds, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        report = AuditReport(
            job_id=job_id,
            url=url,
            summary=summary,
            issues=issues,
            screenshot_path=screenshot_path,
            a11y_tree_summary=a11y_tree or {},
            metadata={
                "engine": "AI-Website-Accessibility-Auditor",
                "version": "1.0.0",
                "wcag_version": "2.1 AA",
            },
        )

        # Write artifacts to disk
        cls.save_artifacts(report)
        return report

    @classmethod
    def save_artifacts(cls, report: AuditReport) -> Tuple[str, str]:
        """Saves machine-readable JSON and interactive HTML report to disk."""
        reports_dir = Path(settings.REPORTS_DIR)
        reports_dir.mkdir(parents=True, exist_ok=True)

        json_path = reports_dir / f"{report.job_id}_report.json"
        html_path = reports_dir / f"{report.job_id}_report.html"

        # 1. Write JSON
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        # 2. Render and write HTML
        template = Template(HTML_REPORT_TEMPLATE)
        html_content = template.render(report=report)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Saved audit reports: {json_path} and {html_path}")
        return str(json_path), str(html_path)

ReportGenerator.build_report = ReportGenerator.generate_report
AuditReportGenerator = ReportGenerator

