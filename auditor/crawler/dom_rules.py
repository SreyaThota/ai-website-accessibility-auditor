import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
from auditor.models.schemas import (
    AccessibilityIssue,
    WCAGPrinciple,
    WCAGLevel,
    Severity,
    RemediationSnippet,
    BoundingBox,
)
from auditor.core.logging import logger

VAGUE_LINK_TEXTS = {
    "click here", "click this", "here", "read more", "learn more",
    "more", "link", "go", "view", "details", "info", "this page"
}

GENERIC_ALT_TEXTS = {
    "image", "picture", "photo", "graphic", "icon", "logo", "img", "screenshot"
}

class DOMRulesEvaluator:
    """
    Evaluates raw and rendered DOM structures against WCAG 2.1 AA success criteria.
    Extracts syntactic, structural, semantic, and ARIA relationship barriers.
    """

    def __init__(self, html_content: str, element_boxes: Optional[Dict[str, Dict[str, float]]] = None):
        self.soup = BeautifulSoup(html_content, "html.parser")
        self.element_boxes = element_boxes or {}
        self.issues: List[AccessibilityIssue] = []

    def evaluate_all(self) -> List[AccessibilityIssue]:
        """Runs the complete suite of programmatic DOM accessibility checks."""
        self.issues.clear()
        self._check_page_language()
        self._check_page_title()
        self._check_images_alt_attributes()
        self._check_form_labels()
        self._check_heading_hierarchy()
        self._check_landmark_roles()
        self._check_buttons_and_links_accessible_names()
        self._check_vague_links()
        self._check_aria_references()

        logger.info(f"DOM rules evaluation identified {len(self.issues)} violations.")
        return self.issues

    def _get_box(self, selector: str) -> Optional[BoundingBox]:
        """Resolves bounding box if available from crawler."""
        if selector in self.element_boxes:
            b = self.element_boxes[selector]
            return BoundingBox(x=b["x"], y=b["y"], width=b["width"], height=b["height"])
        return None

    def _check_page_language(self):
        """WCAG 3.1.1: Language of Page (Level A)"""
        html_tag = self.soup.find("html")
        if not html_tag or not html_tag.get("lang"):
            self.issues.append(
                AccessibilityIssue(
                    id="DOM_3_1_1_MISSING_LANG",
                    rule_id="WCAG_3_1_1_LANGUAGE_OF_PAGE",
                    principle=WCAGPrinciple.UNDERSTANDABLE,
                    level=WCAGLevel.A,
                    severity=Severity.MAJOR,
                    element_selector="html",
                    element_tag="html",
                    description="The <html> element lacks a valid 'lang' attribute.",
                    failure_summary="Screen readers cannot determine the default vocalization language or pronunciation rules.",
                    remediation=RemediationSnippet(
                        current_code="<html>",
                        recommended_code='<html lang="en"> <!-- or lang="de" for German -->',
                        explanation="Specify the primary language of the document using an ISO 639-1 language code.",
                        wcag_criterion="3.1.1 Language of Page",
                        wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/language-of-page.html",
                    ),
                )
            )

    def _check_page_title(self):
        """WCAG 2.4.2: Page Titled (Level A)"""
        title_tag = self.soup.find("title")
        title_text = title_tag.get_text().strip() if title_tag else ""

        if not title_tag or not title_text or title_text.lower() in ["untitled", "index", "home", "page"]:
            current = str(title_tag) if title_tag else "<head> (missing <title>)"
            self.issues.append(
                AccessibilityIssue(
                    id="DOM_2_4_2_MISSING_TITLE",
                    rule_id="WCAG_2_4_2_PAGE_TITLED",
                    principle=WCAGPrinciple.OPERABLE,
                    level=WCAGLevel.A,
                    severity=Severity.MAJOR,
                    element_selector="head > title",
                    element_tag="title",
                    description="The web page is missing a descriptive <title> element.",
                    failure_summary="Users of screen readers rely on page titles to orient themselves when navigating across tabs.",
                    remediation=RemediationSnippet(
                        current_code=current,
                        recommended_code="<title>Dashboard | Student Portal - Technical University</title>",
                        explanation="Provide a descriptive, context-specific page title describing the purpose of the page.",
                        wcag_criterion="2.4.2 Page Titled",
                        wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/page-titled.html",
                    ),
                )
            )

    def _check_images_alt_attributes(self):
        """WCAG 1.1.1: Non-text Content (Level A)"""
        images = self.soup.find_all("img")
        for i, img in enumerate(images):
            selector = self._generate_selector(img, f"img:nth-of-type({i+1})")
            has_alt = img.has_attr("alt")
            alt_val = img.get("alt", "").strip() if has_alt else None
            is_in_link_or_button = bool(img.find_parent(["a", "button"]))

            if not has_alt:
                self.issues.append(
                    AccessibilityIssue(
                        id=f"DOM_1_1_1_IMG_NO_ALT_{i}",
                        rule_id="WCAG_1_1_1_NON_TEXT_CONTENT",
                        principle=WCAGPrinciple.PERCEIVABLE,
                        level=WCAGLevel.A,
                        severity=Severity.CRITICAL,
                        element_selector=selector,
                        element_tag="img",
                        description="Image element is completely missing an 'alt' attribute.",
                        failure_summary="Assistive technologies read out raw file URLs or completely announce the image as unlabelled.",
                        bounding_box=self._get_box(selector),
                        remediation=RemediationSnippet(
                            current_code=str(img)[:150],
                            recommended_code=self._propose_alt_fix(img, "Descriptive description of the image content"),
                            explanation="Add a concise, descriptive 'alt' attribute. If decorative, set alt=\"\" and role=\"presentation\".",
                            wcag_criterion="1.1.1 Non-text Content",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
                        ),
                    )
                )
            elif is_in_link_or_button and not alt_val:
                self.issues.append(
                    AccessibilityIssue(
                        id=f"DOM_1_1_1_LINK_IMG_EMPTY_ALT_{i}",
                        rule_id="WCAG_1_1_1_NON_TEXT_CONTENT",
                        principle=WCAGPrinciple.PERCEIVABLE,
                        level=WCAGLevel.A,
                        severity=Severity.CRITICAL,
                        element_selector=selector,
                        element_tag="img",
                        description="Actionable image inside link or button has empty alt=\"\" text.",
                        failure_summary="Screen reader users cannot determine the target or destination of this interactive control.",
                        bounding_box=self._get_box(selector),
                        remediation=RemediationSnippet(
                            current_code=str(img)[:150],
                            recommended_code=self._propose_alt_fix(img, "Home Page"),
                            explanation="Images serving as the sole content of a link or button must describe the action or destination.",
                            wcag_criterion="1.1.1 Non-text Content",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
                        ),
                    )
                )
            elif alt_val and alt_val.lower() in GENERIC_ALT_TEXTS:
                self.issues.append(
                    AccessibilityIssue(
                        id=f"DOM_1_1_1_GENERIC_ALT_{i}",
                        rule_id="WCAG_1_1_1_NON_TEXT_CONTENT",
                        principle=WCAGPrinciple.PERCEIVABLE,
                        level=WCAGLevel.A,
                        severity=Severity.MAJOR,
                        element_selector=selector,
                        element_tag="img",
                        description=f"Image alt text is generic placeholder text ('{alt_val}').",
                        failure_summary="Placeholder alt text conveys zero meaningful information to visually impaired users.",
                        bounding_box=self._get_box(selector),
                        remediation=RemediationSnippet(
                            current_code=str(img)[:150],
                            recommended_code=self._propose_alt_fix(img, "University Central Library main entrance building"),
                            explanation="Replace generic placeholders with factual descriptions of the visual content.",
                            wcag_criterion="1.1.1 Non-text Content",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
                        ),
                    )
                )

    def _check_form_labels(self):
        """WCAG 1.3.1: Info and Relationships & 4.1.2: Name, Role, Value"""
        form_controls = self.soup.find_all(["input", "select", "textarea"])

        for i, control in enumerate(form_controls):
            input_type = control.get("type", "text").lower()
            if input_type in ["hidden", "submit", "reset", "button", "image"]:
                continue

            selector = self._generate_selector(control, f"{control.name}:nth-of-type({i+1})")
            has_label = False

            # 1. Wrapped by <label>
            if control.find_parent("label"):
                has_label = True

            # 2. Associated via for / id
            input_id = control.get("id")
            if input_id and self.soup.find("label", attrs={"for": input_id}):
                has_label = True

            # 3. aria-label or aria-labelledby
            if control.get("aria-label") or control.get("aria-labelledby"):
                has_label = True

            if not has_label:
                self.issues.append(
                    AccessibilityIssue(
                        id=f"DOM_1_3_1_FORM_NO_LABEL_{i}",
                        rule_id="WCAG_1_3_1_INFO_AND_RELATIONSHIPS",
                        principle=WCAGPrinciple.PERCEIVABLE,
                        level=WCAGLevel.A,
                        severity=Severity.CRITICAL,
                        element_selector=selector,
                        element_tag=control.name,
                        description=f"Form control <{control.name}> is missing a programmatically associated label.",
                        failure_summary="Assistive technologies cannot announce the purpose or expected input format of this field.",
                        bounding_box=self._get_box(selector),
                        remediation=RemediationSnippet(
                            current_code=str(control)[:150],
                            recommended_code=f'<label for="{input_id or "user_input"}">Input Label</label>\n' + str(control)[:150],
                            explanation="Associate an explicit <label for=\"id\"> with the form input or provide aria-label.",
                            wcag_criterion="1.3.1 Info and Relationships / 4.1.2 Name, Role, Value",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
                        ),
                    )
                )

    def _check_heading_hierarchy(self):
        """WCAG 1.3.1: Info and Relationships (Heading Hierarchy)"""
        headings = self.soup.find_all(re.compile(r"^h[1-6]$"))

        if not headings:
            self.issues.append(
                AccessibilityIssue(
                    id="DOM_1_3_1_NO_HEADINGS",
                    rule_id="WCAG_1_3_1_INFO_AND_RELATIONSHIPS",
                    principle=WCAGPrinciple.OPERABLE,
                    level=WCAGLevel.A,
                    severity=Severity.MAJOR,
                    element_selector="body",
                    element_tag="body",
                    description="Page contains no semantic heading elements (<h1>-<h6>).",
                    failure_summary="Screen reader users cannot scan or jump through sections without semantic headings.",
                    remediation=RemediationSnippet(
                        current_code="<body>...</body>",
                        recommended_code="<h1>Main Page Header</h1>",
                        explanation="Structure page content using proper semantic heading tags beginning with <h1>.",
                        wcag_criterion="1.3.1 Info and Relationships",
                        wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
                    ),
                )
            )
            return

        has_h1 = any(h.name == "h1" for h in headings)
        if not has_h1:
            self.issues.append(
                AccessibilityIssue(
                    id="DOM_1_3_1_MISSING_H1",
                    rule_id="WCAG_1_3_1_INFO_AND_RELATIONSHIPS",
                    principle=WCAGPrinciple.OPERABLE,
                    level=WCAGLevel.A,
                    severity=Severity.MAJOR,
                    element_selector="body",
                    element_tag="h1",
                    description="Page structure is missing a top-level <h1> heading.",
                    failure_summary="The <h1> tag represents the primary topic of the document; omitting it confuses screen reader navigation.",
                    remediation=RemediationSnippet(
                        current_code=str(headings[0])[:150],
                        recommended_code="<h1>University Portal - Examination Schedule</h1>",
                        explanation="Provide exactly one primary <h1> heading for the main content area.",
                        wcag_criterion="1.3.1 Info and Relationships",
                        wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
                    ),
                )
            )

        # Detect skipped levels (e.g. h1 -> h3)
        last_level = 0
        for i, h in enumerate(headings):
            level = int(h.name[1])
            if last_level > 0 and level > last_level + 1:
                selector = self._generate_selector(h, f"{h.name}:nth-of-type({i+1})")
                self.issues.append(
                    AccessibilityIssue(
                        id=f"DOM_1_3_1_SKIPPED_HEADING_{i}",
                        rule_id="WCAG_1_3_1_INFO_AND_RELATIONSHIPS",
                        principle=WCAGPrinciple.OPERABLE,
                        level=WCAGLevel.AA,
                        severity=Severity.MODERATE,
                        element_selector=selector,
                        element_tag=h.name,
                        description=f"Skipped heading level from <h{last_level}> directly to <h{level}>.",
                        failure_summary="Skipping heading levels creates broken navigational outlines for keyboard and screen reader users.",
                        bounding_box=self._get_box(selector),
                        remediation=RemediationSnippet(
                            current_code=str(h)[:150],
                            recommended_code=f"<h{last_level+1}>{h.get_text().strip()}</h{last_level+1}>",
                            explanation=f"Adjust heading to <h{last_level+1}> to maintain a strict sequential outline hierarchy.",
                            wcag_criterion="1.3.1 Info and Relationships",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
                        ),
                    )
                )
            last_level = level

    def _check_landmark_roles(self):
        """WCAG 1.3.1 & 2.4.1: Landmarks and Structural Regions"""
        has_main = bool(self.soup.find("main") or self.soup.find(attrs={"role": "main"}))
        if not has_main:
            self.issues.append(
                AccessibilityIssue(
                    id="DOM_1_3_1_MISSING_MAIN_LANDMARK",
                    rule_id="WCAG_1_3_1_INFO_AND_RELATIONSHIPS",
                    principle=WCAGPrinciple.OPERABLE,
                    level=WCAGLevel.A,
                    severity=Severity.MAJOR,
                    element_selector="body",
                    element_tag="main",
                    description="The page is missing a designated <main> landmark region.",
                    failure_summary="Screen reader users cannot quickly jump to the main content, having to tab through repetitive headers.",
                    remediation=RemediationSnippet(
                        current_code="<body><div class=\"content\">...</div></body>",
                        recommended_code="<body><main id=\"main-content\">...</main></body>",
                        explanation="Wrap the primary page content in a semantic <main> tag or add role=\"main\".",
                        wcag_criterion="1.3.1 Info and Relationships",
                        wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
                    ),
                )
            )

    def _check_buttons_and_links_accessible_names(self):
        """WCAG 4.1.2: Name, Role, Value (Interactive Controls)"""
        buttons = self.soup.find_all("button")
        for i, btn in enumerate(buttons):
            text = btn.get_text().strip()
            aria_label = btn.get("aria-label", "").strip()
            aria_labelledby = btn.get("aria-labelledby", "").strip()
            title = btn.get("title", "").strip()

            if not (text or aria_label or aria_labelledby or title):
                selector = self._generate_selector(btn, f"button:nth-of-type({i+1})")
                self.issues.append(
                    AccessibilityIssue(
                        id=f"DOM_4_1_2_EMPTY_BUTTON_{i}",
                        rule_id="WCAG_4_1_2_NAME_ROLE_VALUE",
                        principle=WCAGPrinciple.ROBUST,
                        level=WCAGLevel.A,
                        severity=Severity.CRITICAL,
                        element_selector=selector,
                        element_tag="button",
                        description="Button element has no accessible name (empty text and no aria-label).",
                        failure_summary="Screen readers voice this element as 'Button' with zero context on what action it performs.",
                        bounding_box=self._get_box(selector),
                        remediation=RemediationSnippet(
                            current_code=str(btn)[:150],
                            recommended_code='<button aria-label="Submit search query"><svg>...</svg></button>',
                            explanation="Provide inner text or an aria-label attribute describing the button's action.",
                            wcag_criterion="4.1.2 Name, Role, Value",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/name-role-value.html",
                        ),
                    )
                )

    def _check_vague_links(self):
        """WCAG 2.4.4: Link Purpose (In Context) (Level A)"""
        links = self.soup.find_all("a")
        for i, a in enumerate(links):
            text = a.get_text().strip().lower()
            aria_label = a.get("aria-label", "").strip().lower()

            effective_text = aria_label or text
            if effective_text in VAGUE_LINK_TEXTS:
                selector = self._generate_selector(a, f"a:nth-of-type({i+1})")
                self.issues.append(
                    AccessibilityIssue(
                        id=f"DOM_2_4_4_VAGUE_LINK_{i}",
                        rule_id="WCAG_2_4_4_LINK_PURPOSE_IN_CONTEXT",
                        principle=WCAGPrinciple.OPERABLE,
                        level=WCAGLevel.A,
                        severity=Severity.MODERATE,
                        element_selector=selector,
                        element_tag="a",
                        description=f"Link text '{a.get_text().strip()}' is ambiguous when read out of context.",
                        failure_summary="Screen reader users navigating by link lists hear repetitive 'click here' without destination context.",
                        bounding_box=self._get_box(selector),
                        remediation=RemediationSnippet(
                            current_code=str(a)[:150],
                            recommended_code='<a href="/regulations">Read more about TUM Examination Regulations</a>',
                            explanation="Provide descriptive anchor text or add an aria-label qualifying the link destination.",
                            wcag_criterion="2.4.4 Link Purpose (In Context)",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context.html",
                        ),
                    )
                )

    def _check_aria_references(self):
        """WCAG 1.3.1 & 4.1.2: Broken ARIA ID References"""
        ref_attrs = ["aria-labelledby", "aria-describedby", "aria-controls", "aria-owns"]
        for attr in ref_attrs:
            elements = self.soup.find_all(attrs={attr: True})
            for i, el in enumerate(elements):
                target_ids = el.get(attr, "").split()
                for target_id in target_ids:
                    if target_id and not self.soup.find(id=target_id):
                        selector = self._generate_selector(el, f"{el.name}:nth-of-type({i+1})")
                        self.issues.append(
                            AccessibilityIssue(
                                id=f"DOM_4_1_2_BROKEN_ARIA_REF_{attr}_{i}",
                                rule_id="WCAG_4_1_2_NAME_ROLE_VALUE",
                                principle=WCAGPrinciple.ROBUST,
                                level=WCAGLevel.A,
                                severity=Severity.CRITICAL,
                                element_selector=selector,
                                element_tag=el.name,
                                description=f"Attribute '{attr}' references non-existent element ID '{target_id}'.",
                                failure_summary="Broken ARIA references cause assistive tech to miss crucial descriptive relationships.",
                                bounding_box=self._get_box(selector),
                                remediation=RemediationSnippet(
                                    current_code=str(el)[:150],
                                    recommended_code=f'<!-- Ensure element with id="{target_id}" exists in the DOM -->',
                                    explanation=f"Verify that the ID referenced by '{attr}' exists on the target element.",
                                    wcag_criterion="4.1.2 Name, Role, Value",
                                    wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/name-role-value.html",
                                ),
                            )
                        )

    def _generate_selector(self, tag: Tag, fallback: str) -> str:
        """Constructs an actionable CSS selector for a DOM element."""
        if tag.get("id"):
            return f"#{tag['id']}"
        classes = tag.get("class", [])
        if classes:
            return f"{tag.name}." + ".".join(classes[:2])
        return fallback

    def _propose_alt_fix(self, img_tag: Tag, placeholder: str) -> str:
        """Generates clean HTML fix for image alt tags."""
        tag_copy = BeautifulSoup(str(img_tag), "html.parser").find("img")
        tag_copy["alt"] = placeholder
        return str(tag_copy)
