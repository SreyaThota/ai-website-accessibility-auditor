"""Unit tests for DOM programmatic accessibility rules evaluation."""

import pytest
from auditor.crawler.dom_rules import DOMRulesEvaluator
from auditor.models.schemas import Severity, WCAGPrinciple, WCAGLevel


def test_missing_page_lang():
    html = "<html><head><title>Test Title</title></head><body><h1>Header</h1><main><p>Content</p></main></body></html>"
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    lang_issues = [i for i in issues if i.rule_id == "WCAG_3_1_1_LANGUAGE_OF_PAGE"]
    assert len(lang_issues) == 1
    assert lang_issues[0].severity == Severity.MAJOR
    assert lang_issues[0].principle == WCAGPrinciple.UNDERSTANDABLE


def test_valid_page_lang():
    html = '<html lang="en"><head><title>Test Title</title></head><body><h1>Header</h1><main><p>Content</p></main></body></html>'
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    lang_issues = [i for i in issues if i.rule_id == "WCAG_3_1_1_LANGUAGE_OF_PAGE"]
    assert len(lang_issues) == 0


def test_missing_page_title():
    html = '<html lang="en"><head></head><body><h1>Title Here</h1><main><p>Body</p></main></body></html>'
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    title_issues = [i for i in issues if i.rule_id == "WCAG_2_4_2_PAGE_TITLED"]
    assert len(title_issues) == 1
    assert title_issues[0].severity == Severity.MAJOR


def test_generic_page_title():
    html = '<html lang="en"><head><title>Untitled</title></head><body><h1>Title</h1><main><p>Body</p></main></body></html>'
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    title_issues = [i for i in issues if i.rule_id == "WCAG_2_4_2_PAGE_TITLED"]
    assert len(title_issues) == 1


def test_missing_image_alt():
    html = '<html lang="en"><head><title>Title</title></head><body><h1>Header</h1><main><img src="chart.png"></main></body></html>'
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    alt_issues = [i for i in issues if i.rule_id == "WCAG_1_1_1_NON_TEXT_CONTENT"]
    assert len(alt_issues) >= 1
    assert alt_issues[0].severity == Severity.CRITICAL


def test_generic_image_alt_flagged():
    html = '<html lang="en"><head><title>Title</title></head><body><h1>Header</h1><main><img src="chart.png" alt="photo"></main></body></html>'
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    alt_issues = [i for i in issues if i.rule_id == "WCAG_1_1_1_NON_TEXT_CONTENT"]
    assert len(alt_issues) == 1
    assert "generic" in alt_issues[0].description.lower()


def test_valid_image_alt_passes():
    html = '<html lang="en"><head><title>Title</title></head><body><h1>Header</h1><main><img src="chart.png" alt="Annual student enrollment trends graph from 2020 to 2025"></main></body></html>'
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    alt_issues = [i for i in issues if i.rule_id == "WCAG_1_1_1_NON_TEXT_CONTENT"]
    assert len(alt_issues) == 0


def test_form_input_missing_label():
    html = """
    <html lang="en"><head><title>Form Test</title></head><body><h1>Sign In</h1><main>
        <form>
            <input type="text" name="username">
            <input type="password" name="pwd">
        </form>
    </main></body></html>
    """
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    form_issues = [i for i in issues if i.rule_id == "WCAG_1_3_1_INFO_AND_RELATIONSHIPS" and "form" in i.description.lower()]
    assert len(form_issues) == 2
    assert all(issue.severity == Severity.CRITICAL for issue in form_issues)


def test_form_input_with_label_for_passes():
    html = """
    <html lang="en"><head><title>Form Test</title></head><body><h1>Sign In</h1><main>
        <form>
            <label for="uname">Username</label>
            <input id="uname" type="text" name="username">
            <input type="password" name="pwd" aria-label="Password">
        </form>
    </main></body></html>
    """
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    form_issues = [i for i in issues if i.rule_id == "WCAG_1_3_1_INFO_AND_RELATIONSHIPS" and "form" in i.description.lower()]
    assert len(form_issues) == 0


def test_heading_hierarchy_skipped_level():
    html = """
    <html lang="en"><head><title>Headings</title></head><body>
        <h1>Main Topic</h1>
        <h3>Skipped Topic</h3>
        <main><p>Body</p></main>
    </body></html>
    """
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    skipped_headings = [i for i in issues if "Skipped heading level" in i.description]
    assert len(skipped_headings) == 1
    assert skipped_headings[0].severity == Severity.MODERATE


def test_missing_main_landmark():
    html = """
    <html lang="en"><head><title>Title</title></head><body>
        <h1>Main Heading</h1>
        <div><p>Content without landmark wrapper</p></div>
    </body></html>
    """
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    landmark_issues = [i for i in issues if "landmark" in i.description.lower()]
    assert len(landmark_issues) >= 1


def test_vague_link_text():
    html = """
    <html lang="en"><head><title>Links</title></head><body><h1>Heading</h1><main>
        <a href="/report.pdf">Click here</a>
    </main></body></html>
    """
    evaluator = DOMRulesEvaluator(html)
    issues = evaluator.evaluate_all()
    vague_issues = [i for i in issues if "WCAG_2_4_4" in i.rule_id]
    assert len(vague_issues) == 1
    assert vague_issues[0].severity == Severity.MODERATE

