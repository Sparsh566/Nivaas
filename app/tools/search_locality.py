"""Tool: search_locality_information - Get locality details via web search."""

import logging
from pydantic import BaseModel, Field
from app.tools.tavily_client import tavily_wrapper
from app.db.queries import get_cached_locality, save_locality_cache
from app.config import settings

logger = logging.getLogger(__name__)


class SearchLocalityArgs(BaseModel):
    locality: str = Field(..., description="Locality name, e.g. Hinjewadi")
    city: str = Field(..., description="City name, e.g. Pune")


SEARCH_LOCALITY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_locality_information",
        "description": "Search for locality information including metro stations, IT parks, hospitals, schools, and infrastructure.",
        "parameters": {
            "type": "object",
            "properties": {
                "locality": {"type": "string", "description": "Locality name"},
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["locality", "city"],
        },
    },
}


async def execute(args: SearchLocalityArgs) -> dict:
    """Search for locality information via Tavily."""

    # Check cache first
    cached = await get_cached_locality(
        args.locality, args.city, settings.LOCALITY_CACHE_DAYS
    )
    if cached:
        return {
            "locality": args.locality,
            "city": args.city,
            "info": cached.data,
            "source_urls": cached.source_urls or [],
            "source": "cache",
            "note": "Information from the web, verify before deciding.",
        }

    if not tavily_wrapper.is_configured:
        return {
            "locality": args.locality,
            "city": args.city,
            "info": {},
            "error": "Web search is not configured.",
            "note": "Set TAVILY_API_KEY to enable locality information search.",
        }

    query = f"{args.locality} {args.city} metro IT parks hospitals schools infrastructure connectivity"

    result = await tavily_wrapper.search(
        query=query,
        max_results=5,
        search_depth="basic",
    )

    if "error" in result:
        return {
            "locality": args.locality,
            "city": args.city,
            "info": {},
            "error": result["error"],
        }

    search_results = result.get("results", [])
    info = {
        "summaries": [],
        "topics_found": [],
    }
    source_urls = []

    topics = ["metro", "it park", "hospital", "school", "road", "connectivity"]

    for sr in search_results:
        title = sr.get("title", "")
        content = sr.get("content", "")
        url = sr.get("url", "")

        if content:
            info["summaries"].append({
                "title": title,
                "snippet": content[:500],
                "url": url,
            })
            source_urls.append(url)

            for topic in topics:
                if topic in content.lower() and topic not in info["topics_found"]:
                    info["topics_found"].append(topic)

    # Cache the results
    try:
        await save_locality_cache(
            locality=args.locality,
            city=args.city,
            data=info,
            source_urls=source_urls,
        )
    except Exception as e:
        logger.error("Failed to cache locality info: %s", str(e))

    return {
        "locality": args.locality,
        "city": args.city,
        "info": info,
        "source_urls": source_urls,
        "note": "Information from the web, verify before deciding.",
    }
