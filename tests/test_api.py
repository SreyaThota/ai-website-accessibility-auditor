"""Integration tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "WCAG 2.1 AA" in data["standards"]
    assert "version" in data


def test_presets_endpoint():
    response = client.get("/api/v1/presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) >= 2
    ids = [p["id"] for p in data["presets"]]
    assert "preset:inaccessible_portal" in ids
    assert "preset:compliant_portal" in ids


def test_root_redirect_to_docs():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_audit_preset_compliant():
    response = client.post(
        "/api/v1/audit",
        json={
            "url": "preset:compliant_portal",
            "check_visual_contrast": False,
            "generate_ai_alt_text": False,
            "check_touch_targets": True,
        },
    )
    assert response.status_code == 200
    report = response.json()
    assert report["url"] == "preset:compliant_portal"
    assert "summary" in report
    assert report["summary"]["critical_issues"] == 0
    assert report["summary"]["overall_score"] >= 80.0
    assert "job_id" in report


def test_audit_preset_inaccessible():
    response = client.post(
        "/api/v1/audit",
        json={
            "url": "preset:inaccessible_portal",
            "check_visual_contrast": False,
            "generate_ai_alt_text": False,
            "check_touch_targets": True,
        },
    )
    assert response.status_code == 200
    report = response.json()
    assert report["url"] == "preset:inaccessible_portal"
    assert len(report["issues"]) > 0
    assert report["summary"]["critical_issues"] > 0
    assert "FAIL" in report["summary"]["eea_compliance_status"]


def test_get_audit_by_id():
    # First trigger audit
    post_res = client.post(
        "/api/v1/audit",
        json={"url": "preset:compliant_portal", "check_visual_contrast": False},
    )
    job_id = post_res.json()["job_id"]

    # Retrieve by job_id
    get_res = client.get(f"/api/v1/audit/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["job_id"] == job_id


def test_get_nonexistent_audit_404():
    response = client.get("/api/v1/audit/non_existent_job_123")
    assert response.status_code == 404
