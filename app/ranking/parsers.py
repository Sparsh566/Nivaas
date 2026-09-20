"""Parsers for Indian price, BHK, and area formats."""

import re
from typing import Optional


def parse_price(text: str) -> Optional[int]:
    """Parse Indian price formats to integer rupees.

    Supported: "70 lakh", "70L", "0.7 cr", "1.2 crore", "50,00,000", "7000000".
    Returns None if parsing fails.
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip().lower().replace(",", "").replace("rs.", "").replace("rs", "")
    text = text.replace("inr", "").replace("/-", "").strip()

    # Match patterns with crore/cr
    cr_match = re.match(r"^([\d.]+)\s*(?:crore|crores|cr)s?$", text)
    if cr_match:
        try:
            return int(float(cr_match.group(1)) * 10_000_000)
        except (ValueError, OverflowError):
            return None

    # Match patterns with lakh/lac/l
    lakh_match = re.match(r"^([\d.]+)\s*(?:lakh|lakhs|lac|lacs|l)$", text)
    if lakh_match:
        try:
            return int(float(lakh_match.group(1)) * 100_000)
        except (ValueError, OverflowError):
            return None

    # Match patterns with k (thousands)
    k_match = re.match(r"^([\d.]+)\s*k$", text)
    if k_match:
        try:
            return int(float(k_match.group(1)) * 1_000)
        except (ValueError, OverflowError):
            return None

    # Plain number
    plain_match = re.match(r"^[\d.]+$", text)
    if plain_match:
        try:
            val = float(text)
            return int(val) if val > 0 else None
        except (ValueError, OverflowError):
            return None

    return None


def parse_bhk(text: str) -> Optional[int]:
    """Parse BHK formats: '2BHK', '2 bhk', '2 BHK', '3bhk'.

    Returns None if parsing fails.
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip().lower()
    bhk_match = re.match(r"^(\d+)\s*bhk$", text)
    if bhk_match:
        return int(bhk_match.group(1))

    # Also match plain numbers 1-9 (likely BHK if in context)
    if text.isdigit() and 1 <= int(text) <= 9:
        return int(text)

    return None


def parse_area(text: str) -> Optional[int]:
    """Parse area formats: '950 sq ft', '950 sqft', '1200 sq. ft.', '950 sft'.

    Returns None if parsing fails.
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip().lower()
    area_match = re.match(
        r"^([\d,.]+)\s*(?:sq\.?\s*ft\.?|sqft|sft|square\s*feet?)$", text
    )
    if area_match:
        try:
            val = area_match.group(1).replace(",", "")
            return int(float(val))
        except (ValueError, OverflowError):
            return None

    # Plain number (assume sqft if large enough)
    if text.replace(",", "").replace(".", "").isdigit():
        try:
            val = int(float(text.replace(",", "")))
            return val if val > 50 else None
        except (ValueError, OverflowError):
            return None

    return None


def format_price_indian(price_inr: int) -> str:
    """Format price in Indian lakh/crore format."""
    if price_inr >= 10_000_000:
        crore = price_inr / 10_000_000
        if crore == int(crore):
            return f"{int(crore)} Cr"
        return f"{crore:.2f} Cr"
    elif price_inr >= 100_000:
        lakh = price_inr / 100_000
        if lakh == int(lakh):
            return f"{int(lakh)} Lakh"
        return f"{lakh:.1f} Lakh"
    else:
        return f"{price_inr:,}"


def format_indian_number(num: int) -> str:
    """Format a number in Indian numbering system (e.g. 50,00,000)."""
    s = str(num)
    if len(s) <= 3:
        return s
    last_three = s[-3:]
    remaining = s[:-3]
    groups = []
    while remaining:
        groups.append(remaining[-2:])
        remaining = remaining[:-2]
    groups.reverse()
    return ",".join(groups) + "," + last_three
