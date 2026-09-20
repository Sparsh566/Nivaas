"""Tests for grounding check: verifies extracted values appear in source text."""

import pytest
from app.tools.search_properties import _ground_check


class TestGroundingCheck:
    def test_valid_extraction(self):
        """Values present in source text should pass."""
        extracted = {
            "price_inr": 6500000,
            "bhk": 2,
            "area_sqft": 950,
            "evidence": {"price": "65 lakh"},
        }
        source_text = "2 BHK flat available at 65 lakh, carpet area 950 sq ft in Hinjewadi"
        passed, issues = _ground_check(extracted, source_text)
        assert passed
        assert len(issues) == 0

    def test_price_mismatch(self):
        """Price not in source text should fail."""
        extracted = {
            "price_inr": 7500000,
            "bhk": 2,
            "area_sqft": 950,
        }
        source_text = "2 BHK flat available at 65 lakh, carpet area 950 sq ft"
        passed, issues = _ground_check(extracted, source_text)
        assert not passed
        assert any("price" in i.lower() for i in issues)

    def test_bhk_mismatch(self):
        """BHK not in source text should fail."""
        extracted = {
            "price_inr": 6500000,
            "bhk": 3,
            "area_sqft": 950,
            "evidence": {"price": "65 lakh"},
        }
        source_text = "2 BHK flat available at 65 lakh, carpet area 950 sq ft"
        passed, issues = _ground_check(extracted, source_text)
        assert not passed
        assert any("bhk" in i.lower() for i in issues)

    def test_null_area_accepted(self):
        """Null area should pass (missing is OK, wrong is not)."""
        extracted = {
            "price_inr": 6500000,
            "bhk": 2,
            "area_sqft": None,
            "evidence": {"price": "65 lakh"},
        }
        source_text = "2 BHK flat available at 65 lakh in Hinjewadi"
        passed, issues = _ground_check(extracted, source_text)
        assert passed

    def test_null_price_accepted(self):
        """Null price is accepted (not stated)."""
        extracted = {
            "price_inr": None,
            "bhk": 2,
            "area_sqft": 950,
        }
        source_text = "2 BHK flat, 950 sq ft in Hinjewadi"
        passed, issues = _ground_check(extracted, source_text)
        assert passed

    def test_price_in_lakh_format(self):
        """Price match via evidence snippet."""
        extracted = {
            "price_inr": 4500000,
            "bhk": 2,
            "evidence": {"price": "45 lakh"},
        }
        source_text = "2 BHK for sale at Rs 45 lakh in Wakad"
        passed, issues = _ground_check(extracted, source_text)
        assert passed

    def test_empty_source_text(self):
        """Empty source text with stated values should fail."""
        extracted = {
            "price_inr": 6500000,
            "bhk": 2,
        }
        passed, issues = _ground_check(extracted, "")
        assert not passed
