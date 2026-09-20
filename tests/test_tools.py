"""Tests for tool argument validation and schema compliance."""

import pytest
from pydantic import ValidationError
from app.tools.search_properties import SearchPropertiesArgs
from app.tools.get_property_details import GetPropertyDetailsArgs
from app.tools.compare_properties import ComparePropertiesArgs
from app.tools.calculate_emi import CalculateEMIArgs
from app.tools.update_preferences import UpdatePreferencesArgs
from app.tools.search_locality import SearchLocalityArgs
from app.tools.registry import ALLOWED_TOOLS, TOOL_SCHEMAS


class TestSearchPropertiesArgs:
    def test_valid(self):
        args = SearchPropertiesArgs(city="Pune", max_budget_inr=7000000, bhk=2)
        assert args.city == "Pune"
        assert args.max_budget_inr == 7000000

    def test_missing_city_fails(self):
        with pytest.raises(ValidationError):
            SearchPropertiesArgs(max_budget_inr=7000000)

    def test_missing_budget_fails(self):
        with pytest.raises(ValidationError):
            SearchPropertiesArgs(city="Pune")


class TestCompareArgs:
    def test_valid_two(self):
        args = ComparePropertiesArgs(listing_ids=["id1", "id2"])
        assert len(args.listing_ids) == 2

    def test_valid_three(self):
        args = ComparePropertiesArgs(listing_ids=["a", "b", "c"])
        assert len(args.listing_ids) == 3

    def test_one_fails(self):
        with pytest.raises(ValidationError):
            ComparePropertiesArgs(listing_ids=["only_one"])

    def test_four_fails(self):
        with pytest.raises(ValidationError):
            ComparePropertiesArgs(listing_ids=["a", "b", "c", "d"])


class TestEMIArgs:
    def test_valid_minimal(self):
        args = CalculateEMIArgs(price_inr=5000000)
        assert args.down_payment_pct == 20.0
        assert args.annual_rate == 8.5
        assert args.tenure_years == 20

    def test_valid_full(self):
        args = CalculateEMIArgs(
            price_inr=7000000,
            down_payment_pct=30,
            annual_rate=9.0,
            tenure_years=15,
            monthly_income=100000,
        )
        assert args.monthly_income == 100000


class TestUpdatePreferencesArgs:
    def test_valid(self):
        args = UpdatePreferencesArgs(priorities=["metro", "budget"])
        assert len(args.priorities) == 2

    def test_missing_priorities_fails(self):
        with pytest.raises(ValidationError):
            UpdatePreferencesArgs()


class TestLocalityArgs:
    def test_valid(self):
        args = SearchLocalityArgs(locality="Hinjewadi", city="Pune")
        assert args.locality == "Hinjewadi"


class TestToolRegistry:
    def test_all_tools_listed(self):
        expected = {
            "search_properties",
            "get_property_details",
            "compare_properties",
            "search_locality_information",
            "calculate_emi",
            "update_preferences",
        }
        assert ALLOWED_TOOLS == expected

    def test_schema_count(self):
        assert len(TOOL_SCHEMAS) == 6

    def test_schemas_have_required_fields(self):
        for schema in TOOL_SCHEMAS:
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "parameters" in schema["function"]
