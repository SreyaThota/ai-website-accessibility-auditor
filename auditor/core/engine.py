import os
import json
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from auditor.models.schemas import (
    AuditReport,
    AccessibilityIssue,
    BoundingBox,
    RemediationSnippet,
    WCAGPrinciple,
    WCAGLevel,
    Severity,
)
from auditor.core.config import settings
from auditor.core.logging import logger
from auditor.crawler.playwright_crawler import crawler
from auditor.crawler.dom_rules import DOMRulesEvaluator
from auditor.vision.contrast_analyzer import contrast_analyzer
from auditor.vision.touch_target_checker import touch_target_checker
from auditor.vision.ai_alt_generator import ai_alt_generator
from auditor.reporter.report_generator import ReportGenerator

PRESETS = {
    "preset:inaccessible_portal": str(Path(settings.DEMO_SITES_DIR) / "inaccessible_portal.html"),
    "preset:compliant_portal": str(Path(settings.DEMO_SITES_DIR) / "compliant_portal.html"),
}

class AccessibilityAuditEngine:
    """
    Master Audit Orchestrator.
    Coordinates browser automation, DOM rule checks, multi-modal contrast analysis,
    touch target evaluation, AI alt text generation, and executive report synthesis.
    """

    def __init__(self):
        self.reports_cache: Dict[str, AuditReport] = {}

    async def run_audit(
        self,
        url: str,
        check_visual_contrast: bool = True,
        generate_ai_alt_text: bool = True,
        check_touch_targets: bool = True,
        job_id: Optional[str] = None,
    ) -> AuditReport:
        """Executes a complete accessibility audit over target URL or preset."""
        start_time = time.perf_counter()
        job_id = job_id or f"audit_{uuid.uuid4().hex[:10]}"
        logger.info(f"Starting audit job '{job_id}' for '{url}'")

        # Resolve preset shortcuts
        target_path = PRESETS.get(url, url)

        # 1. Headless crawling & screenshot capture
        html_content, screenshot_path, boxes, a11y_tree = await crawler.crawl_url(target_path, job_id)

        # 2. Programmatic DOM rules evaluation
        dom_evaluator = DOMRulesEvaluator(html_content, boxes)
        dom_issues = dom_evaluator.evaluate_all()

        all_issues: List[AccessibilityIssue] = list(dom_issues)

        # 3. Touch target sizing check (WCAG 2.5.5 / 2.5.8)
        if check_touch_targets and boxes:
            for selector, box in boxes.items():
                if any(k in selector for k in ["button", "a", "input", "select"]):
                    bbox = BoundingBox(x=box["x"], y=box["y"], width=box["width"], height=box["height"])
                    tag = selector.split(".")[0].split(":")[0].replace("#", "")
                    # WCAG 2.5.8 Exception: Inline targets within a block of text
                    is_inline = " p " in selector or "p > a" in selector or (
                        tag == "a" and not any(c in selector for c in ["btn", "nav", "button", "menu", "skip"])
                    )
                    issue = touch_target_checker.evaluate_element_target(selector, tag, bbox, is_inline=is_inline)
                    if issue:
                        all_issues.append(issue)


        # 4. Multi-modal visual contrast analysis
        if check_visual_contrast and screenshot_path and os.path.exists(screenshot_path) and boxes:
            for selector, box in list(boxes.items())[:12]:  # Sample key visual elements
                bbox = BoundingBox(x=box["x"], y=box["y"], width=box["width"], height=box["height"])
                is_large = any(h in selector for h in ["h1", "h2", "h3"])
                contrast_issue = contrast_analyzer.analyze_element_patch(
                    image_path=screenshot_path,
                    bbox=bbox,
                    is_large_text=is_large,
                    selector=selector,
                )
                if contrast_issue:
                    all_issues.append(contrast_issue)

        # 5. Automated AI alt-text generation for missing alt images
        if generate_ai_alt_text:
            for issue in all_issues:
                if issue.rule_id == "WCAG_1_1_1_NON_TEXT_CONTENT" and "alt" in issue.description.lower():
                    # Generate AI-proposed alt text
                    crop_box = None
                    if issue.bounding_box:
                        b = issue.bounding_box
                        crop_box = (int(b.x), int(b.y), int(b.x + b.width), int(b.y + b.height))

                    ai_alt = await ai_alt_generator.generate_alt_text(
                        image_path=screenshot_path or "",
                        context_hint=f"Image selector {issue.element_selector}",
                        crop_box=crop_box,
                    )
                    # Enrich remediation code with the AI-generated alt text
                    issue.remediation.recommended_code = f'<img alt="{ai_alt}" ...>'
                    issue.remediation.explanation += f' [AI Vision Model Proposed Alt-Text: "{ai_alt}"]'

        elapsed = time.perf_counter() - start_time
        logger.info(f"Audit completed in {elapsed:.2f}s with {len(all_issues)} issues identified.")

        # 6. Aggregate report synthesis
        report = ReportGenerator.generate_report(
            job_id=job_id,
            url=url,
            issues=all_issues,
            duration_seconds=elapsed,
            screenshot_path=screenshot_path,
            a11y_tree=a11y_tree,
        )

        self.reports_cache[job_id] = report
        return report

    def get_report(self, job_id: str) -> Optional[AuditReport]:
        """Retrieves cached report by job_id."""
        if job_id in self.reports_cache:
            return self.reports_cache[job_id]

        # Check disk
        json_path = Path(settings.REPORTS_DIR) / f"{job_id}_report.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report = AuditReport(**data)
                self.reports_cache[job_id] = report
                return report
            except Exception as e:
                logger.warning(f"Could not load report from disk: {e}")

        return None

# Singleton audit engine
engine = AccessibilityAuditEngine()
