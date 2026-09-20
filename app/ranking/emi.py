"""EMI calculator with standard amortization formula."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EMIResult:
    loan_amount: int
    emi: int
    total_payable: int
    total_interest: int
    emi_to_income_pct: Optional[float] = None
    income_warning: bool = False


def calculate_emi(
    price_inr: int,
    down_payment_pct: float = 20.0,
    annual_rate: float = 8.5,
    tenure_years: int = 20,
    monthly_income: Optional[int] = None,
) -> EMIResult:
    """Calculate EMI using standard amortization formula.

    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r = annual_rate / 12 / 100, n = tenure_years * 12.

    Handles rate = 0 as simple division: loan / n.
    """
    if price_inr <= 0:
        raise ValueError("Price must be positive")
    if tenure_years <= 0:
        raise ValueError("Tenure must be positive")
    if down_payment_pct < 0 or down_payment_pct >= 100:
        raise ValueError("Down payment percentage must be between 0 and 99")

    loan_amount = int(price_inr * (1 - down_payment_pct / 100))
    n = tenure_years * 12

    if annual_rate == 0:
        emi = loan_amount / n
    else:
        r = annual_rate / 12 / 100
        power = (1 + r) ** n
        emi = loan_amount * r * power / (power - 1)

    emi = round(emi)
    total_payable = emi * n
    total_interest = total_payable - loan_amount

    emi_to_income_pct = None
    income_warning = False
    if monthly_income and monthly_income > 0:
        emi_to_income_pct = round(emi / monthly_income * 100, 1)
        income_warning = emi_to_income_pct > 40

    return EMIResult(
        loan_amount=loan_amount,
        emi=emi,
        total_payable=total_payable,
        total_interest=total_interest,
        emi_to_income_pct=emi_to_income_pct,
        income_warning=income_warning,
    )
