#!/usr/bin/env python3
"""
Command-Line Interface (CLI) for AI Website Accessibility Auditor.
Executes programmatic DOM validation, computer vision contrast analysis,
and remediation report generation directly from the terminal.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals to avoid charmap UnicodeEncodeErrors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from auditor.core.engine import engine, PRESETS
from auditor.core.logging import logger
from auditor.models.schemas import Severity


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Website Accessibility Auditor - Enterprise WCAG 2.1 AA & EAA Compliance Engine"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", type=str, help="Target URL to crawl and audit (e.g. https://example.com)")
    group.add_argument(
        "--preset",
        type=str,
        choices=["inaccessible_portal", "compliant_portal"],
        help="Run audit on pre-packaged test fixtures",
    )

    parser.add_argument("--no-vision", action="store_true", help="Disable visual contrast analysis")
    parser.add_argument("--no-ai-alt", action="store_true", help="Disable AI alt-text generation")
    parser.add_argument("--no-targets", action="store_true", help="Disable touch target checks")
    parser.add_argument("--out-dir", type=str, default="./reports", help="Directory to save audit artifacts")

    return parser.parse_args()


async def main_async():
    args = parse_args()

    target = f"preset:{args.preset}" if args.preset else args.url
    print("\n" + "=" * 70)
    print("🛡️  AI Website Accessibility Auditor (WCAG 2.1 AA & EAA Compliance)")
    print(f"🎯 Target: {target}")
    print("=" * 70 + "\n")

    report = await engine.run_audit(
        url=target,
        check_visual_contrast=not args.no_vision,
        generate_ai_alt_text=not args.no_ai_alt,
        check_touch_targets=not args.no_targets,
    )

    s = report.summary
    print("\n" + "-" * 70)
    print("📊 EXECUTIVE AUDIT SUMMARY")
    print("-" * 70)
    print(f"Overall Compliance Score:  {s.overall_score}/100")
    print(f"WCAG 2.1 Conformance:      {s.wcag_level_conformance}")
    print(f"EAA Mandate Status:        {s.eea_compliance_status}")
    print(f"Total Issues Detected:     {s.total_issues}")
    print(f"  - Critical:              {s.critical_issues}")
    print(f"  - Major:                 {s.major_issues}")
    print(f"  - Moderate:              {s.moderate_issues}")
    print(f"  - Minor:                 {s.minor_issues}")
    print(f"Audit Elapsed Time:        {s.duration_seconds}s")
    print("-" * 70)

    if report.issues:
        print("\n🔍 TOP DETECTED BARRIERS:")
        for idx, issue in enumerate(report.issues[:5], 1):
            print(f" [{idx}] {issue.severity.value.upper()} | {issue.rule_id}")
            print(f"     Description: {issue.description}")
            print(f"     Selector:    {issue.element_selector}")
            print(f"     Fix:         {issue.remediation.explanation}\n")

    json_file = Path(args.out_dir) / f"{report.job_id}_report.json"
    html_file = Path(args.out_dir) / f"{report.job_id}_report.html"
    print(f"📁 JSON Report Artifact: {json_file.resolve()}")
    print(f"🌐 HTML Interactive Report: {html_file.resolve()}\n")

    return 0 if s.critical_issues == 0 else 1


def main():
    try:
        sys.exit(asyncio.run(main_async()))
    except KeyboardInterrupt:
        print("\nAudit aborted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
