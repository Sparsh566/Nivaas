"""Tool: search_properties - Search for properties via web and extract structured listings."""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.config import settings, SEARCH_DOMAINS
from app.tools.tavily_client import tavily_wrapper
from app.db.queries import get_cached_listings, save_listings
from app.ranking.parsers import parse_price
from app.ranking.scorer import score_listings

logger = logging.getLogger(__name__)


class SearchPropertiesArgs(BaseModel):
    city: str = Field(..., description="City to search in, e.g. Pune")
    locality: Optional[str] = Field(None, description="Preferred locality, e.g. Hinjewadi")
    max_budget_inr: int = Field(..., description="Maximum budget in INR")
    bhk: Optional[int] = Field(None, description="Number of bedrooms (BHK)")
    property_type: Optional[str] = Field(None, description="Type: flat, apartment, villa, plot")
    extras: Optional[str] = Field(None, description="Additional requirements like amenities")


SEARCH_PROPERTIES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_properties",
        "description": "Search for property listings matching the user's requirements. Returns ranked results from real estate portals.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City to search in"},
                "locality": {"type": "string", "description": "Preferred locality"},
                "max_budget_inr": {"type": "integer", "description": "Maximum budget in INR"},
                "bhk": {"type": "integer", "description": "Number of bedrooms (BHK)"},
                "property_type": {"type": "string", "description": "Property type: flat, apartment, villa"},
                "extras": {"type": "string", "description": "Additional requirements"},
            },
            "required": ["city", "max_budget_inr"],
        },
    },
}


def _build_query_key(args: SearchPropertiesArgs) -> str:
    """Build a normalized cache key from search arguments."""
    parts = [args.city.lower().strip()]
    if args.locality:
        parts.append(args.locality.lower().strip())
    parts.append(str(args.max_budget_inr))
    if args.bhk:
        parts.append(f"{args.bhk}bhk")
    if args.property_type:
        parts.append(args.property_type.lower().strip())
    return "|".join(parts)


def _build_search_queries(args: SearchPropertiesArgs) -> list[str]:
    """Build 1 to 2 search queries from the arguments."""
    queries = []
    bhk_str = f"{args.bhk} BHK" if args.bhk else ""
    budget_lakh = args.max_budget_inr / 100000
    budget_str = f"under {budget_lakh:.0f} lakh" if budget_lakh < 100 else f"under {budget_lakh/100:.1f} crore"

    type_str = args.property_type or "flat"
    locality_str = args.locality or ""

    q1 = f"{bhk_str} {type_str} in {locality_str} {args.city} {budget_str}".strip()
    q1 = re.sub(r"\s+", " ", q1)
    queries.append(q1)

    if args.locality:
        q2 = f"{bhk_str} {type_str} for sale {args.city} {locality_str} price".strip()
        q2 = re.sub(r"\s+", " ", q2)
        queries.append(q2)

    return queries


def _ground_check(extracted: dict, source_text: str) -> tuple[bool, list[str]]:
    """Verify extracted values appear in the source text.
    Returns (passed, list_of_issues).
    """
    issues = []
    text_lower = source_text.lower() if source_text else ""

    # Check price
    price = extracted.get("price_inr")
    if price:
        price_str = str(price)
        # Check various representations
        price_lakh = price / 100000
        price_cr = price / 10000000
        found = False
        for candidate in [
            price_str,
            f"{price_lakh:.0f}",
            f"{price_lakh:.1f}",
            f"{price_lakh:.2f}",
            f"{price_cr:.1f}",
            f"{price_cr:.2f}",
        ]:
            if candidate in text_lower or candidate in source_text:
                found = True
                break
        if not found:
            # Check if price evidence snippet was provided
            evidence = extracted.get("evidence", {})
            if evidence and evidence.get("price"):
                parsed = parse_price(evidence["price"])
                if parsed and abs(parsed - price) < price * 0.05:
                    found = True
        if not found:
            issues.append(f"Price {price} not found in source text")

    # Check BHK
    bhk = extracted.get("bhk")
    if bhk:
        bhk_patterns = [f"{bhk}bhk", f"{bhk} bhk", f"{bhk}-bhk", f"{bhk} bedroom"]
        if not any(p in text_lower for p in bhk_patterns):
            issues.append(f"BHK {bhk} not found in source text")

    # Check area
    area = extracted.get("area_sqft")
    if area:
        area_str = str(area)
        if area_str not in source_text and area_str not in text_lower:
            issues.append(f"Area {area} not found in source text")

    passed = len(issues) == 0
    return passed, issues


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return "unknown"


async def _extract_listings_with_llm(
    text: str, source_url: str, args: SearchPropertiesArgs
) -> list[dict]:
    """Use Groq to extract structured listing data from page text."""
    if not settings.GROQ_API_KEY:
        return []

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        extraction_prompt = f"""Extract property listings from the following text.
Rules:
- Extract ONLY listings explicitly stated in the text.
- Any field not clearly stated must be null.
- Never infer, compute, or guess a value.
- A page may contain several listings or none.
- For price, extract the exact value in INR. Convert lakh/crore to full number.
- For evidence, copy the exact text snippet where each value (price, BHK, area) appears.

Return a JSON array of objects with these fields:
- title (string or null)
- locality (string or null)
- city (string or null)
- price_inr (integer in full INR or null)
- bhk (integer or null)
- area_sqft (integer or null)
- property_type (string: flat/apartment/villa/plot or null)
- furnishing (string: furnished/semi-furnished/unfurnished or null)
- parking (string or null)
- amenities (array of strings or null)
- evidence (object with keys price, bhk, area mapping to the exact text snippets)

Text to extract from:
{text[:8000]}"""

        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You extract structured property listing data from web page text. Return valid JSON only. Never invent data."},
                {"role": "user", "content": extraction_prompt},
            ],
            temperature=0.0,
            max_tokens=4000,
        )

        content = response.choices[0].message.content
        # Try to parse JSON from the response
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        listings = json.loads(content)
        if isinstance(listings, dict):
            listings = [listings]
        if not isinstance(listings, list):
            return []

        # Add source info
        domain = _extract_domain(source_url)
        for listing in listings:
            listing["source_url"] = source_url
            listing["source_domain"] = domain

        return listings

    except Exception as e:
        logger.error("LLM extraction failed: %s", str(e))
        return []


async def execute(
    args: SearchPropertiesArgs,
    requirements: dict,
    weights: dict[str, float],
    tavily_calls_this_message: int = 0,
) -> dict:
    """Execute property search: cache check, web search, extraction, grounding, ranking."""

    query_key = _build_query_key(args)

    # Check cache first
    cached = await get_cached_listings(query_key, settings.LISTING_CACHE_HOURS)
    if len(cached) >= 3:
        listing_dicts = [
            {
                "id": str(c.id),
                "title": c.title,
                "locality": c.locality,
                "city": c.city,
                "price_inr": c.price_inr,
                "bhk": c.bhk,
                "area_sqft": c.area_sqft,
                "property_type": c.property_type,
                "furnishing": c.furnishing,
                "parking": c.parking,
                "amenities": c.amenities,
                "source_url": c.source_url,
                "source_domain": c.source_domain,
                "evidence": c.evidence,
                "fetched_at": c.fetched_at.isoformat(),
            }
            for c in cached
        ]
        ranked = score_listings(listing_dicts, requirements, weights)
        return {
            "listings": ranked,
            "source": "cache",
            "total_found": len(ranked),
            "tavily_calls_used": 0,
        }

    # Check demo mode
    if settings.DEMO_MODE:
        return await _demo_search(args, requirements, weights, query_key)

    # Check Tavily availability
    if not tavily_wrapper.is_configured:
        if settings.DEMO_MODE:
            return await _demo_search(args, requirements, weights, query_key)
        return {
            "listings": [],
            "error": "Web search is not configured. Set TAVILY_API_KEY to enable property search.",
            "total_found": 0,
            "tavily_calls_used": 0,
        }

    # Build and execute search queries
    queries = _build_search_queries(args)
    all_results = []
    tavily_calls = tavily_calls_this_message
    steps = []

    for query in queries:
        if tavily_calls >= settings.MAX_TAVILY_CALLS_PER_MESSAGE:
            break

        result = await tavily_wrapper.search(
            query=query,
            include_domains=SEARCH_DOMAINS,
            max_results=8,
            search_depth="basic",
        )
        tavily_calls += 1

        if "error" in result:
            steps.append({"action": "search", "query": query, "error": result["error"]})
            continue

        search_results = result.get("results", [])
        steps.append({
            "action": "search",
            "query": query,
            "pages_found": len(search_results),
        })

        # Collect URLs needing extraction
        urls_needing_extract = []
        for sr in search_results:
            raw = sr.get("raw_content", "") or ""
            if len(raw) < 200:
                urls_needing_extract.append(sr.get("url", ""))
            else:
                all_results.append({
                    "url": sr.get("url", ""),
                    "text": raw,
                    "title": sr.get("title", ""),
                })

        # Extract content for URLs with insufficient text
        if urls_needing_extract and tavily_calls < settings.MAX_TAVILY_CALLS_PER_MESSAGE:
            extract_result = await tavily_wrapper.extract(
                urls=urls_needing_extract[:5]
            )
            tavily_calls += 1

            if "error" not in extract_result:
                for er in extract_result.get("results", []):
                    all_results.append({
                        "url": er.get("url", ""),
                        "text": er.get("raw_content", ""),
                        "title": "",
                    })

    # Extract listings from page texts using LLM
    all_extracted = []
    for page in all_results:
        if not page.get("text"):
            continue
        extracted = await _extract_listings_with_llm(
            page["text"], page["url"], args
        )
        for listing in extracted:
            listing["_source_text"] = page["text"]
        all_extracted.extend(extracted)

    steps.append({
        "action": "extraction",
        "pages_processed": len(all_results),
        "listings_extracted": len(all_extracted),
    })

    # Grounding check
    validated = []
    dropped = []
    for listing in all_extracted:
        source_text = listing.pop("_source_text", "")
        passed, issues = _ground_check(listing, source_text)
        if not passed:
            dropped.append({"listing": listing.get("title", "unknown"), "issues": issues})
            continue

        # Validation: city must match
        listing_city = (listing.get("city") or "").lower()
        if listing_city and args.city.lower() not in listing_city and listing_city not in args.city.lower():
            dropped.append({"listing": listing.get("title", "unknown"), "issues": ["City mismatch"]})
            continue

        # BHK must match if specified
        if args.bhk and listing.get("bhk") and listing["bhk"] != args.bhk:
            dropped.append({"listing": listing.get("title", "unknown"), "issues": ["BHK mismatch"]})
            continue

        # Price must not exceed budget
        if listing.get("price_inr") and listing["price_inr"] > args.max_budget_inr * 1.05:
            dropped.append({"listing": listing.get("title", "unknown"), "issues": ["Over budget"]})
            continue

        validated.append(listing)

    # Deduplicate by (locality, price, area, bhk)
    seen = set()
    deduped = []
    for listing in validated:
        key = (
            (listing.get("locality") or "").lower(),
            listing.get("price_inr"),
            listing.get("area_sqft"),
            listing.get("bhk"),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(listing)

    steps.append({
        "action": "validation",
        "validated": len(deduped),
        "dropped": len(dropped),
        "drop_details": dropped[:5],
    })

    # Cache validated listings
    if deduped:
        cache_entries = []
        for listing in deduped:
            entry = {
                "id": uuid.uuid4(),
                "title": listing.get("title"),
                "locality": listing.get("locality") or args.locality or args.city,
                "city": listing.get("city") or args.city,
                "price_inr": listing.get("price_inr") or 0,
                "bhk": listing.get("bhk"),
                "area_sqft": listing.get("area_sqft"),
                "property_type": listing.get("property_type"),
                "furnishing": listing.get("furnishing"),
                "parking": listing.get("parking"),
                "amenities": listing.get("amenities"),
                "source_url": listing.get("source_url", ""),
                "source_domain": listing.get("source_domain", ""),
                "evidence": listing.get("evidence"),
                "query_key": query_key,
                "fetched_at": datetime.now(timezone.utc),
            }
            cache_entries.append(entry)
            listing["id"] = str(entry["id"])
            listing["fetched_at"] = entry["fetched_at"].isoformat()

        try:
            await save_listings(cache_entries)
        except Exception as e:
            logger.error("Failed to cache listings: %s", str(e))

    # Score and rank
    listing_dicts = []
    for listing in deduped:
        listing_dicts.append({
            "id": listing.get("id", str(uuid.uuid4())),
            "title": listing.get("title"),
            "locality": listing.get("locality") or args.locality or args.city,
            "city": listing.get("city") or args.city,
            "price_inr": listing.get("price_inr") or 0,
            "bhk": listing.get("bhk"),
            "area_sqft": listing.get("area_sqft"),
            "property_type": listing.get("property_type"),
            "furnishing": listing.get("furnishing"),
            "parking": listing.get("parking"),
            "amenities": listing.get("amenities"),
            "source_url": listing.get("source_url", ""),
            "source_domain": listing.get("source_domain", ""),
            "fetched_at": listing.get("fetched_at", ""),
        })

    ranked = score_listings(listing_dicts, requirements, weights)

    honest_message = None
    if len(ranked) < 3:
        honest_message = (
            f"Found only {len(ranked)} listing(s) matching your criteria. "
            "Consider widening your budget, trying a different locality, or reducing requirements."
        )

    return {
        "listings": ranked,
        "total_found": len(ranked),
        "tavily_calls_used": tavily_calls - tavily_calls_this_message,
        "steps": steps,
        "honest_message": honest_message,
    }


async def _demo_search(
    args: SearchPropertiesArgs,
    requirements: dict,
    weights: dict[str, float],
    query_key: str,
) -> dict:
    """Return demo listings when DEMO_MODE is true."""
    import os
    demo_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "demo_listings.json")
    try:
        with open(demo_path, "r", encoding="utf-8") as f:
            demo_data = json.load(f)
    except FileNotFoundError:
        return {
            "listings": [],
            "error": "Demo data file not found.",
            "total_found": 0,
            "tavily_calls_used": 0,
            "is_demo": True,
        }

    # Filter demo listings
    filtered = []
    for listing in demo_data:
        if args.city.lower() not in (listing.get("city") or "").lower():
            continue
        if args.bhk and listing.get("bhk") and listing["bhk"] != args.bhk:
            continue
        if listing.get("price_inr") and listing["price_inr"] > args.max_budget_inr * 1.05:
            continue
        if args.locality:
            listing_loc = (listing.get("locality") or "").lower()
            if args.locality.lower() not in listing_loc and listing_loc not in args.locality.lower():
                continue
        filtered.append(listing)

    ranked = score_listings(filtered, requirements, weights)

    honest_message = None
    if len(ranked) < 3:
        honest_message = (
            f"Found only {len(ranked)} demo listing(s) matching your criteria. "
            "Try widening your budget or locality."
        )

    return {
        "listings": ranked,
        "total_found": len(ranked),
        "tavily_calls_used": 0,
        "is_demo": True,
        "honest_message": honest_message,
    }
