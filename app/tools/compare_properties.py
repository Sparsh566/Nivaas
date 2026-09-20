"""Tool: compare_properties - Side-by-side comparison of 2-3 listings."""

from pydantic import BaseModel, Field, field_validator
from app.db.queries import get_listings_by_ids
from app.ranking.parsers import format_price_indian


class ComparePropertiesArgs(BaseModel):
    listing_ids: list[str] = Field(..., description="List of 2-3 listing IDs to compare")

    @field_validator("listing_ids")
    @classmethod
    def validate_count(cls, v: list[str]) -> list[str]:
        if len(v) < 2 or len(v) > 3:
            raise ValueError("Provide 2 or 3 listing IDs to compare")
        return v


COMPARE_PROPERTIES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "compare_properties",
        "description": "Compare 2 to 3 property listings side by side. Shows differences in price, area, BHK, and other attributes.",
        "parameters": {
            "type": "object",
            "properties": {
                "listing_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2-3 listing IDs",
                    "minItems": 2,
                    "maxItems": 3,
                },
            },
            "required": ["listing_ids"],
        },
    },
}


async def execute(args: ComparePropertiesArgs) -> dict:
    """Compare 2-3 cached listings side by side."""
    listings = await get_listings_by_ids(args.listing_ids)

    if len(listings) < 2:
        return {"error": "Could not find enough listings to compare. Some may have expired."}

    comparison = []
    for listing in listings:
        price_per_sqft = None
        if listing.area_sqft and listing.area_sqft > 0:
            price_per_sqft = round(listing.price_inr / listing.area_sqft)

        comparison.append({
            "id": str(listing.id),
            "title": listing.title or "Untitled",
            "locality": listing.locality,
            "city": listing.city,
            "price_inr": listing.price_inr,
            "price_formatted": format_price_indian(listing.price_inr),
            "bhk": listing.bhk,
            "area_sqft": listing.area_sqft,
            "price_per_sqft": price_per_sqft,
            "property_type": listing.property_type,
            "furnishing": listing.furnishing,
            "parking": listing.parking,
            "amenities": listing.amenities or [],
            "source_url": listing.source_url,
            "source_domain": listing.source_domain,
        })

    # Generate trade-off notes
    tradeoffs = _generate_tradeoffs(comparison)

    return {
        "listings": comparison,
        "tradeoffs": tradeoffs,
    }


def _generate_tradeoffs(listings: list[dict]) -> list[str]:
    """Generate deterministic trade-off notes from listing comparisons."""
    notes = []

    prices = [(l["title"], l["price_inr"]) for l in listings if l.get("price_inr")]
    if len(prices) >= 2:
        cheapest = min(prices, key=lambda x: x[1])
        costliest = max(prices, key=lambda x: x[1])
        if cheapest[1] != costliest[1]:
            diff_lakh = (costliest[1] - cheapest[1]) / 100000
            notes.append(
                f"{cheapest[0]} is {diff_lakh:.1f} lakh cheaper than {costliest[0]}"
            )

    areas = [(l["title"], l["area_sqft"]) for l in listings if l.get("area_sqft")]
    if len(areas) >= 2:
        largest = max(areas, key=lambda x: x[1])
        smallest = min(areas, key=lambda x: x[1])
        if largest[1] != smallest[1]:
            notes.append(
                f"{largest[0]} offers {largest[1] - smallest[1]} sq ft more area"
            )

    ppsf = [(l["title"], l["price_per_sqft"]) for l in listings if l.get("price_per_sqft")]
    if len(ppsf) >= 2:
        best_value = min(ppsf, key=lambda x: x[1])
        notes.append(f"{best_value[0]} has the lowest price per sq ft at {best_value[1]:,}/sq ft")

    return notes
