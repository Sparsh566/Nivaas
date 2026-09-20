"""Tests for Indian format parsers: price, BHK, area."""

import pytest
from app.ranking.parsers import (
    parse_price,
    parse_bhk,
    parse_area,
    format_price_indian,
    format_indian_number,
)


class TestParsePrice:
    def test_lakh_word(self):
        assert parse_price("70 lakh") == 7_000_000

    def test_lakh_short(self):
        assert parse_price("70L") == 7_000_000

    def test_lakhs_plural(self):
        assert parse_price("45 lakhs") == 4_500_000

    def test_crore_word(self):
        assert parse_price("1.2 crore") == 12_000_000

    def test_crore_short(self):
        assert parse_price("0.7 cr") == 7_000_000

    def test_crores_plural(self):
        assert parse_price("2 crores") == 20_000_000

    def test_indian_comma_format(self):
        assert parse_price("50,00,000") == 5_000_000

    def test_plain_number(self):
        assert parse_price("7000000") == 7_000_000

    def test_decimal_lakh(self):
        assert parse_price("65.5 lakh") == 6_550_000

    def test_lac_variant(self):
        assert parse_price("70 lac") == 7_000_000

    def test_with_rs_prefix(self):
        assert parse_price("Rs. 70 lakh") == 7_000_000

    def test_with_inr_prefix(self):
        assert parse_price("INR 50 lakh") == 5_000_000

    def test_empty_string(self):
        assert parse_price("") is None

    def test_none(self):
        assert parse_price(None) is None

    def test_garbage(self):
        assert parse_price("hello world") is None

    def test_negative(self):
        assert parse_price("-50 lakh") is None


class TestParseBhk:
    def test_uppercase_no_space(self):
        assert parse_bhk("2BHK") == 2

    def test_lowercase_space(self):
        assert parse_bhk("2 bhk") == 2

    def test_uppercase_space(self):
        assert parse_bhk("2 BHK") == 2

    def test_three_bhk(self):
        assert parse_bhk("3bhk") == 3

    def test_plain_digit(self):
        assert parse_bhk("1") == 1

    def test_empty(self):
        assert parse_bhk("") is None

    def test_none(self):
        assert parse_bhk(None) is None

    def test_garbage(self):
        assert parse_bhk("studio") is None


class TestParseArea:
    def test_sq_ft_space(self):
        assert parse_area("950 sq ft") == 950

    def test_sqft_no_space(self):
        assert parse_area("950 sqft") == 950

    def test_sq_dot_ft(self):
        assert parse_area("1200 sq. ft.") == 1200

    def test_sft(self):
        assert parse_area("850 sft") == 850

    def test_with_comma(self):
        assert parse_area("1,200 sq ft") == 1200

    def test_empty(self):
        assert parse_area("") is None

    def test_none(self):
        assert parse_area(None) is None

    def test_garbage(self):
        assert parse_area("large") is None


class TestFormatPrice:
    def test_lakh(self):
        assert format_price_indian(7_000_000) == "70 Lakh"

    def test_crore(self):
        assert format_price_indian(10_000_000) == "1 Cr"

    def test_decimal_crore(self):
        assert format_price_indian(12_000_000) == "1.20 Cr"

    def test_below_lakh(self):
        result = format_price_indian(50_000)
        assert "50,000" in result


class TestFormatIndianNumber:
    def test_small(self):
        assert format_indian_number(999) == "999"

    def test_thousands(self):
        assert format_indian_number(50000) == "50,000"

    def test_lakhs(self):
        assert format_indian_number(5000000) == "50,00,000"

    def test_crores(self):
        assert format_indian_number(10000000) == "1,00,00,000"
