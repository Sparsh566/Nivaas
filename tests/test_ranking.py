"""Tests for ranking engine: scoring, weight normalization, null handling."""

import pytest
from app.ranking.scorer import score_listings, _generate_explanations
from app.ranking.weights import (
    get_default_weights,
    reprioritize,
    normalize_weights,
    resolve_factor_name,
)


class TestWeightNormalization:
    def test_normalize_all_factors(self):
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}
        result = normalize_weights(weights)
        assert abs(sum(result.values()) - 1.0) < 0.001

    def test_normalize_with_available_factors(self):
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}
        result = normalize_weights(weights, available_factors={"a", "b"})
        assert "c" not in result
        assert abs(sum(result.values()) - 1.0) < 0.001
        assert abs(result["a"] - 0.625) < 0.01
        assert abs(result["b"] - 0.375) < 0.01

    def test_normalize_empty(self):
        result = normalize_weights({})
        assert result == {}

    def test_normalize_zero_weights(self):
        weights = {"a": 0, "b": 0, "c": 0}
        result = normalize_weights(weights)
        assert abs(sum(result.values()) - 1.0) < 0.001


class TestReprioritize:
    def test_doubles_and_renormalizes(self):
        weights = get_default_weights()
        original_budget = weights["budget_fit"]
        result = reprioritize(weights, "budget_fit")
        assert abs(sum(result.values()) - 1.0) < 0.001
        # Budget weight should be larger than before
        assert result["budget_fit"] > original_budget

    def test_unknown_factor_unchanged(self):
        weights = get_default_weights()
        result = reprioritize(weights, "nonexistent")
        assert result == weights

    def test_connectivity_prioritized(self):
        weights = get_default_weights()
        result = reprioritize(weights, "connectivity")
        assert result["connectivity"] > weights["connectivity"]


class TestResolveFactorName:
    def test_budget_alias(self):
        assert resolve_factor_name("budget") == "budget_fit"
        assert resolve_factor_name("price") == "budget_fit"

    def test_metro_alias(self):
        assert resolve_factor_name("metro") == "connectivity"
        assert resolve_factor_name("connectivity") == "connectivity"

    def test_area_alias(self):
        assert resolve_factor_name("area") == "area"
        assert resolve_factor_name("size") == "area"

    def test_unknown_returns_none(self):
        assert resolve_factor_name("foobar") is None


class TestScoreListings:
    def test_empty_listings(self):
        result = score_listings([], {}, get_default_weights())
        assert result == []

    def test_basic_scoring(self):
        listings = [
            {
                "id": "1",
                "title": "Test 1",
                "locality": "Hinjewadi",
                "city": "Pune",
                "price_inr": 6_000_000,
                "bhk": 2,
                "area_sqft": 900,
                "property_type": "flat",
                "furnishing": None,
                "parking": None,
                "amenities": None,
                "source_url": "https://example.com",
                "source_domain": "example.com",
                "fetched_at": "2026-01-01",
            }
        ]
        requirements = {
            "city": "Pune",
            "locality": "Hinjewadi",
            "max_budget_inr": 7_000_000,
            "bhk": 2,
        }
        result = score_listings(listings, requirements, get_default_weights())
        assert len(result) == 1
        assert "match_score" in result[0]
        assert 0 <= result[0]["match_score"] <= 100
        assert "factor_breakdown" in result[0]
        assert "reasons" in result[0]

    def test_budget_fit_within(self):
        listings = [
            {
                "id": "1", "title": "Test", "locality": "Baner", "city": "Pune",
                "price_inr": 6_000_000, "bhk": 2, "area_sqft": None,
                "property_type": None, "furnishing": None, "parking": None,
                "amenities": None, "source_url": "https://x.com", "source_domain": "x",
                "fetched_at": "",
            }
        ]
        reqs = {"max_budget_inr": 7_000_000, "city": "Pune"}
        result = score_listings(listings, reqs, get_default_weights())
        # price is 85.7% of budget, should score 1.0
        budget_factor = [f for f in result[0]["factor_breakdown"] if f["factor"] == "budget_fit"]
        assert len(budget_factor) == 1
        assert budget_factor[0]["score"] == 1.0

    def test_null_factor_skipped(self):
        """Listing with null area should still get a valid score."""
        listings = [
            {
                "id": "1", "title": "Test", "locality": "Baner", "city": "Pune",
                "price_inr": 5_000_000, "bhk": 2, "area_sqft": None,
                "property_type": None, "furnishing": None, "parking": None,
                "amenities": None, "source_url": "https://x.com", "source_domain": "x",
                "fetched_at": "",
            }
        ]
        reqs = {"max_budget_inr": 7_000_000, "city": "Pune", "min_area_sqft": 900}
        result = score_listings(listings, reqs, get_default_weights())
        assert len(result) == 1
        # Area factor should NOT be in breakdown since area_sqft is None
        area_factors = [f for f in result[0]["factor_breakdown"] if f["factor"] == "area"]
        assert len(area_factors) == 0

    def test_sorting_by_score(self):
        listings = [
            {
                "id": "1", "title": "Over budget", "locality": "Baner", "city": "Pune",
                "price_inr": 7_300_000, "bhk": 2, "area_sqft": 900,
                "property_type": "flat", "furnishing": None, "parking": None,
                "amenities": None, "source_url": "https://x.com", "source_domain": "x",
                "fetched_at": "",
            },
            {
                "id": "2", "title": "Within budget", "locality": "Baner", "city": "Pune",
                "price_inr": 5_000_000, "bhk": 2, "area_sqft": 950,
                "property_type": "flat", "furnishing": None, "parking": None,
                "amenities": None, "source_url": "https://x.com", "source_domain": "x",
                "fetched_at": "",
            },
        ]
        reqs = {"max_budget_inr": 7_000_000, "city": "Pune", "locality": "Baner", "bhk": 2}
        result = score_listings(listings, reqs, get_default_weights())
        assert result[0]["match_score"] >= result[1]["match_score"]


class TestExplanations:
    def test_budget_good(self):
        reasons, cons = _generate_explanations(
            {"budget_fit": 1.0}, {}, {}
        )
        assert any("budget" in r.lower() for r in reasons)

    def test_budget_over(self):
        reasons, cons = _generate_explanations(
            {"budget_fit": 0.5}, {}, {}
        )
        assert any("over" in c.lower() for c in cons)

    def test_location_exact(self):
        reasons, cons = _generate_explanations(
            {"location": 1.0}, {}, {}
        )
        assert any("locality" in r.lower() or "location" in r.lower() for r in reasons)
