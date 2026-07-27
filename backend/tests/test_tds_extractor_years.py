"""Debt-register fix: TDS extractor must never read calendar years as experience."""

from app.services.tds_extractor import TDSCriteriaExtractor


def test_real_experience_extracted():
    text = "The minimum number of years of General Experience in construction shall be 3 (three) years."
    assert TDSCriteriaExtractor.extract_from_text(text).get("general_experience") == "3 years"


def test_calendar_year_not_matched():
    text = "General Experience: completion certificates for FY 2023-2024 shall be 2023 attested."
    assert "general_experience" not in TDSCriteriaExtractor.extract_from_text(text)


def test_year_far_from_phrase_not_matched():
    text = "general experience required. The audited report of year shall be 2025 submitted with tender."
    out = TDSCriteriaExtractor.extract_from_text(text)
    assert out.get("general_experience") != "2025 years"
