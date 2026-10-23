import os
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from auditor.models.schemas import AuditRequest, AuditReport, AuditJobStatus
from auditor.core.engine import engine, PRESETS
from auditor.core.config import settings
from auditor.core.logging import logger

router = APIRouter()

@router.post(
    "/audit",
    response_model=AuditReport,
    summary="Trigger Accessibility Audit",
    description="Crawls the target URL or preset in headless Chromium, analyzes DOM semantics, computes visual contrast and touch target sizing, and returns a WCAG 2.1 AA audit report.",
)
async def trigger_audit(request: AuditRequest) -> AuditReport:
    try:
        report = await engine.run_audit(
            url=request.url,
            check_visual_contrast=request.check_visual_contrast,
            generate_ai_alt_text=request.generate_ai_alt_text,
            check_touch_targets=request.check_touch_targets,
        )
        return report
    except Exception as e:
        logger.error(f"Audit failed for URL '{request.url}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit execution error: {str(e)}",
        )

@router.get(
    "/audit/{job_id}",
    response_model=AuditReport,
    summary="Get Audit Report by Job ID",
    description="Retrieves a cached audit report by its unique job identifier.",
)
async def get_audit(job_id: str) -> AuditReport:
    report = engine.get_report(job_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit job '{job_id}' not found.",
        )
    return report

@router.get(
    "/reports/{job_id}/json",
    response_class=JSONResponse,
    summary="Download Machine-Readable JSON Audit Report",
)
async def download_json_report(job_id: str):
    report = engine.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return JSONResponse(content=report.model_dump())

@router.get(
    "/reports/{job_id}/html",
    response_class=HTMLResponse,
    summary="Render Interactive HTML Audit Report",
)
async def render_html_report(job_id: str):
    html_path = Path(settings.REPORTS_DIR) / f"{job_id}_report.html"
    if not html_path.exists():
        # Check if report in cache and save
        report = engine.get_report(job_id)
        if not report:
            raise HTTPException(status_code=404, detail="HTML report not found.")
        from auditor.reporter.report_generator import ReportGenerator
        ReportGenerator.save_artifacts(report)

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@router.get(
    "/presets",
    summary="List Pre-Packaged Demo Websites",
    description="Returns pre-bundled accessible and inaccessible campus/e-commerce test sites for instant evaluation.",
)
async def list_presets() -> Dict[str, Any]:
    return {
        "presets": [
            {
                "id": "preset:inaccessible_portal",
                "name": "Inaccessible Student Portal (Multiple WCAG AA Violations)",
                "description": "Features missing alt text, unlabelled inputs, broken ARIA references, and undersized buttons.",
            },
            {
                "id": "preset:compliant_portal",
                "name": "Compliant Public Service Portal (WCAG 2.1 AA & EAA)",
                "description": "Features semantic landmarks, accessible form labels, 48px touch targets, and 19.5:1 contrast.",
            },
        ]
    }

@router.get(
    "/health",
    summary="Readiness & Health Probe",
    description="Returns operational readiness, active vision model, and version metadata.",
)
async def health_check():
    return {
        "status": "healthy",
        "engine": "AI-Website-Accessibility-Auditor",
        "version": "1.0.0",
        "standards": ["WCAG 2.1 AA", "European Accessibility Act (EAA)", "EN 301 549"],
        "vision_provider": settings.VISION_PROVIDER,
        "browser_headless": settings.HEADLESS_BROWSER,
    }
