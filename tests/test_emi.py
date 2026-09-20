"""Tests for EMI calculator including reference values and edge cases."""

import pytest
from app.ranking.emi import calculate_emi


class TestEMI:
    def test_reference_case(self):
        """50,00,000 at 8.5% for 20 years = approx 43,391 per month."""
        result = calculate_emi(
            price_inr=6_250_000,  # price so that loan = 50,00,000 after 20% DP
            down_payment_pct=20.0,
            annual_rate=8.5,
            tenure_years=20,
        )
        assert result.loan_amount == 5_000_000
        assert abs(result.emi - 43391) <= 2

    def test_reference_case_direct_loan(self):
        """Direct: loan = 50,00,000, rate 8.5%, 20 years."""
        result = calculate_emi(
            price_inr=5_000_000,
            down_payment_pct=0,
            annual_rate=8.5,
            tenure_years=20,
        )
        assert abs(result.emi - 43391) <= 2

    def test_zero_rate(self):
        """Rate = 0: EMI = loan / n."""
        result = calculate_emi(
            price_inr=5_000_000,
            down_payment_pct=0,
            annual_rate=0,
            tenure_years=20,
        )
        expected_emi = 5_000_000 / (20 * 12)
        assert result.emi == round(expected_emi)

    def test_total_interest(self):
        """Total interest = total payable - loan amount."""
        result = calculate_emi(
            price_inr=5_000_000,
            down_payment_pct=0,
            annual_rate=8.5,
            tenure_years=20,
        )
        assert result.total_interest == result.total_payable - result.loan_amount

    def test_with_income_below_threshold(self):
        """EMI to income ratio below 40% should not warn."""
        result = calculate_emi(
            price_inr=5_000_000,
            down_payment_pct=20,
            annual_rate=8.5,
            tenure_years=20,
            monthly_income=200_000,
        )
        assert result.emi_to_income_pct is not None
        assert result.income_warning is False

    def test_with_income_above_threshold(self):
        """EMI to income ratio above 40% should warn."""
        result = calculate_emi(
            price_inr=10_000_000,
            down_payment_pct=0,
            annual_rate=10.0,
            tenure_years=20,
            monthly_income=50_000,
        )
        assert result.income_warning is True

    def test_zero_price_raises(self):
        with pytest.raises(ValueError):
            calculate_emi(price_inr=0, annual_rate=8.5, tenure_years=20)

    def test_zero_tenure_raises(self):
        with pytest.raises(ValueError):
            calculate_emi(price_inr=5_000_000, annual_rate=8.5, tenure_years=0)

    def test_invalid_dp_raises(self):
        with pytest.raises(ValueError):
            calculate_emi(price_inr=5_000_000, down_payment_pct=100, annual_rate=8.5, tenure_years=20)

    def test_down_payment_reduces_loan(self):
        result = calculate_emi(
            price_inr=10_000_000,
            down_payment_pct=30,
            annual_rate=8.5,
            tenure_years=20,
        )
        assert result.loan_amount == 7_000_000
