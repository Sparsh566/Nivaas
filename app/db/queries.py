"""Database query functions. All use parameterized SQLAlchemy expressions."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ListingCache, ApiUsage, LocalityCache
from app.db.engine import AsyncSessionLocal


async def get_cached_listings(
    query_key: str, max_age_hours: int = 24
) -> list[ListingCache]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    async with AsyncSessionLocal() as session:
        stmt = select(ListingCache).where(
            and_(
                ListingCache.query_key == query_key,
                ListingCache.fetched_at >= cutoff,
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def save_listings(listings: list[dict]) -> list[ListingCache]:
    saved = []
    async with AsyncSessionLocal() as session:
        for data in listings:
            obj = ListingCache(**data)
            session.add(obj)
            saved.append(obj)
        await session.commit()
        for obj in saved:
            await session.refresh(obj)
    return saved


async def get_listing_by_id(listing_id: str) -> Optional[ListingCache]:
    async with AsyncSessionLocal() as session:
        stmt = select(ListingCache).where(
            ListingCache.id == uuid.UUID(listing_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_listings_by_ids(listing_ids: list[str]) -> list[ListingCache]:
    uuids = [uuid.UUID(lid) for lid in listing_ids]
    async with AsyncSessionLocal() as session:
        stmt = select(ListingCache).where(ListingCache.id.in_(uuids))
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def record_api_usage(
    service: str,
    endpoint: str,
    credits_used: int = 1,
    ip_address: Optional[str] = None,
) -> None:
    async with AsyncSessionLocal() as session:
        usage = ApiUsage(
            service=service,
            endpoint=endpoint,
            credits_used=credits_used,
            ip_address=ip_address,
        )
        session.add(usage)
        await session.commit()


async def get_daily_tavily_credits() -> int:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    async with AsyncSessionLocal() as session:
        stmt = select(func.coalesce(func.sum(ApiUsage.credits_used), 0)).where(
            and_(
                ApiUsage.service == "tavily",
                ApiUsage.created_at >= today_start,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one()


async def get_cached_locality(
    locality: str, city: str, max_age_days: int = 7
) -> Optional[LocalityCache]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    async with AsyncSessionLocal() as session:
        stmt = select(LocalityCache).where(
            and_(
                func.lower(LocalityCache.locality) == locality.lower(),
                func.lower(LocalityCache.city) == city.lower(),
                LocalityCache.fetched_at >= cutoff,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def save_locality_cache(
    locality: str,
    city: str,
    data: dict,
    source_urls: list[str],
) -> LocalityCache:
    async with AsyncSessionLocal() as session:
        obj = LocalityCache(
            locality=locality,
            city=city,
            data=data,
            source_urls=source_urls,
            fetched_at=datetime.now(timezone.utc),
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
    return obj


async def cleanup_old_data(listing_days: int = 30, usage_days: int = 30) -> None:
    listing_cutoff = datetime.now(timezone.utc) - timedelta(days=listing_days)
    usage_cutoff = datetime.now(timezone.utc) - timedelta(days=usage_days)
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(ListingCache).where(ListingCache.created_at < listing_cutoff)
        )
        await session.execute(
            delete(ApiUsage).where(ApiUsage.created_at < usage_cutoff)
        )
        await session.commit()
