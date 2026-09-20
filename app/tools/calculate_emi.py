"""Tool: calculate_emi - EMI calculator wrapper for the agent."""

from pydantic import BaseModel, Field
from typing import Optional
from app.ranking.emi import calculate_emi as compute_emi
from app.ranking.parsers import format_indian_number


class CalculateEMIArgs(BaseModel):
    price_inr: int = Field(..., description="Property price in INR")
    down_payment_pct: float = Field(20.0, description="Down payment percentage (default 20)")
    annual_rate: float = Field(8.5, description="Annual interest rate in percent")
    tenure_years: int = Field(20, description="Loan tenure in years")
    monthly_income: Optional[int] = Field(None, description="Monthly income in INR (optional)")


CALCULATE_EMI_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate_emi",
        "description": "Calculate EMI (Equated Monthly Installment) for a property loan. Returns loan amount, EMI, total interest, and affordability ratio if income is provided.",
        "parameters": {
            "type": "object",
            "properties": {
                "price_inr": {"type": "integer", "description": "Property price in INR"},
                "down_payment_pct": {"type": "number", "description": "Down payment as percentage (default 20)"},
                "annual_rate": {"type": "number", "description": "Annual interest rate percent (default 8.5)"},
                "tenure_years": {"type": "integer", "description": "Loan tenure in years (default 20)"},
                "monthly_income": {"type": "integer", "description": "Monthly income in INR (optional)"},
            },
            "required": ["price_inr"],
        },
    },
}


async def execute(args: CalculateEMIArgs) -> dict:
    """Calculate EMI and return formatted results."""
    try:
        result = compute_emi(
            price_inr=args.price_inr,
            down_payment_pct=args.down_payment_pct,
            annual_rate=args.annual_rate,
            tenure_years=args.tenure_years,
            monthly_income=args.monthly_income,
        )

        response = {
            "loan_amount": result.loan_amount,
            "loan_amount_formatted": format_indian_number(result.loan_amount),
            "emi": result.emi,
            "emi_formatted": format_indian_number(result.emi),
            "total_payable": result.total_payable,
            "total_payable_formatted": format_indian_number(result.total_payable),
            "total_interest": result.total_interest,
            "total_interest_formatted": format_indian_number(result.total_interest),
            "inputs": {
                "price_inr": args.price_inr,
                "down_payment_pct": args.down_payment_pct,
                "annual_rate": args.annual_rate,
                "tenure_years": args.tenure_years,
            },
            "note": "This is an estimate. Actual EMI may vary based on the lender's terms.",
        }

        if result.emi_to_income_pct is not None:
            response["emi_to_income_pct"] = result.emi_to_income_pct
            if result.income_warning:
                response["income_note"] = (
                    f"EMI is {result.emi_to_income_pct}% of your monthly income. "
                    "Generally, keeping EMI below 40% of income is considered manageable."
                )

        return response

    except ValueError as e:
        return {"error": str(e)}
