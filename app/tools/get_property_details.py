"""Tool: get_property_details - Retrieve a single cached listing by ID."""

from pydantic import BaseModel, Field
from app.db.queries import get_listing_by_id
from app.ranking.parsers import format_price_indian


class GetPropertyDetailsArgs(BaseModel):
    listing_id: str = Field(..., description="UUID of the listing to retrieve")


GET_PROPERTY_DETAILS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_property_details",
        "description": "Get full details of a specific property listing by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "listing_id": {"type": "string", "description": "The listing ID"},
            },
            "required": ["listing_id"],
        },
    },
}


async def execute(args: GetPropertyDetailsArgs) -> dict:
    """Retrieve a single listing from cache."""
    listing = await get_listing_by_id(args.listing_id)
    if not listing:
        return {"error": "Listing not found. It may have expired from the cache."}

    return {
        "id": str(listing.id),
        "title": listing.title,
        "locality": listing.locality,
        "city": listing.city,
        "price_inr": listing.price_inr,
        "price_formatted": format_price_indian(listing.price_inr),
        "bhk": listing.bhk,
        "area_sqft": listing.area_sqft,
        "property_type": listing.property_type,
        "furnishing": listing.furnishing,
        "parking": listing.parking,
        "amenities": listing.amenities,
        "source_url": listing.source_url,
        "source_domain": listing.source_domain,
        "fetched_at": listing.fetched_at.isoformat() if listing.fetched_at else None,
    }
