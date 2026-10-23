from enum import Enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class WCAGPrinciple(str, Enum):
    """The four core principles of WCAG 2.1."""
    PERCEIVABLE = "Perceivable"
    OPERABLE = "Operable"
    UNDERSTANDABLE = "Understandable"
    ROBUST = "Robust"

class WCAGLevel(str, Enum):
    """WCAG conformance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"

class Severity(str, Enum):
    """Issue impact severity rating."""
    CRITICAL = "Critical"   # Total blocker for screen reader / assistive tech
    MAJOR = "Major"         # Serious usability barrier
    MODERATE = "Moderate"   # Impedes efficient access
    MINOR = "Minor"         # Non-blocking best practice flaw

class BoundingBox(BaseModel):
    """Pixel coordinates and dimensions of an element in the viewport."""
    x: float
    y: float
    width: float
    height: float

class RemediationSnippet(BaseModel):
    """Actionable code remediation ready for copy-pasting."""
    current_code: str = Field(..., description="Current offending HTML or CSS")
    recommended_code: str = Field(..., description="WCAG-compliant replacement HTML or CSS")
    explanation: str = Field(..., description="Technical rationale for the remediation")
    wcag_criterion: str = Field(..., description="Specific WCAG 2.1 success criterion (e.g., 1.1.1 Non-text Content)")
    wcag_url: str = Field(..., description="Authoritative W3C specification reference link")

class AccessibilityIssue(BaseModel):
    """Individual accessibility violation or warning."""
    id: str = Field(..., description="Unique issue identifier")
    rule_id: str = Field(..., description="Internal auditor rule code")
    principle: WCAGPrinciple
    level: WCAGLevel
    severity: Severity
    element_selector: str = Field(..., description="CSS path or DOM locator")
    element_tag: str = Field(..., description="HTML tag name")
    description: str = Field(..., description="User-friendly description of violation")
    failure_summary: str = Field(..., description="Specific failure reason")
    bounding_box: Optional[BoundingBox] = None
    remediation: RemediationSnippet
    visual_evidence: Optional[str] = Field(default=None, description="Path or base64 data of screenshot crop")

class CategoryScore(BaseModel):
    """Score breakdown per WCAG principle."""
    principle: WCAGPrinciple
    score: float = Field(..., ge=0.0, le=100.0)
    issues_count: int
    critical_count: int

class AuditSummary(BaseModel):
    """Executive metrics and compliance ratings."""
    url: str
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall compliance index from 0 to 100")
    wcag_level_conformance: str = Field(..., description="'COMPLIANT_AA', 'PARTIAL_AA', or 'NON_COMPLIANT'")
    eea_compliance_status: str = Field(..., description="European Accessibility Act status")
    perceivable_score: float = Field(..., ge=0.0, le=100.0)
    operable_score: float = Field(..., ge=0.0, le=100.0)
    understandable_score: float = Field(..., ge=0.0, le=100.0)
    robust_score: float = Field(..., ge=0.0, le=100.0)
    total_issues: int
    critical_issues: int
    major_issues: int
    moderate_issues: int
    minor_issues: int
    duration_seconds: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AuditReport(BaseModel):
    """Complete machine-readable audit report payload."""
    job_id: str
    url: str
    summary: AuditSummary
    issues: List[AccessibilityIssue] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
    a11y_tree_summary: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AuditRequest(BaseModel):
    """Request payload to initiate a website accessibility audit."""
    url: str = Field(..., min_length=4, description="Target website URL or local HTML path")
    check_visual_contrast: bool = Field(default=True, description="Execute multi-modal pixel contrast analysis")
    generate_ai_alt_text: bool = Field(default=True, description="Propose AI alt descriptions for blank images")
    check_touch_targets: bool = Field(default=True, description="Verify minimum 44x44 CSS pixel target sizing")

class AuditJobStatus(BaseModel):
    """Real-time job tracking status."""
    job_id: str
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str = "Job initialized"
    report: Optional[AuditReport] = None
    error: Optional[str] = None
