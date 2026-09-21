"""FastAPI router for authentication and user favorites."""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import AsyncSessionLocal
from app.db.models import User, UserFavorite
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


# Schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")
    full_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: UserResponse


class FavoriteCreateRequest(BaseModel):
    listing_id: Optional[str] = None
    title: str
    locality: Optional[str] = None
    city: Optional[str] = None
    price_inr: Optional[int] = None
    bhk: Optional[int] = None
    source_url: Optional[str] = None
    metadata_json: Optional[dict] = None


class FavoriteResponse(BaseModel):
    id: int
    listing_id: Optional[str] = None
    title: str
    locality: Optional[str] = None
    city: Optional[str] = None
    price_inr: Optional[int] = None
    bhk: Optional[int] = None
    source_url: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: Optional[str] = None


def format_user(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/api/auth/register", response_model=AuthResponse)
@router.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest, response: Response):
    """Register a new user account with email and password."""
    normalized_email = req.email.strip().lower()

    async with AsyncSessionLocal() as session:
        # Check if email is already taken
        stmt = select(User).where(User.email == normalized_email)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists.",
            )

        # Hash password and create user
        hashed = hash_password(req.password)
        new_user = User(
            email=normalized_email,
            hashed_password=hashed,
            full_name=req.full_name.strip() if req.full_name else None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

    # Generate JWT token
    token = create_access_token({"sub": str(new_user.id), "email": new_user.email})

    # Set secure HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=False,  # allows local testing; in prod use HTTPS
    )

    return AuthResponse(
        token=token,
        user=format_user(new_user),
    )


@router.post("/api/auth/login", response_model=AuthResponse)
@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest, response: Response):
    """Authenticate user with email and password."""
    normalized_email = req.email.strip().lower()

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == normalized_email)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=False,
    )

    return AuthResponse(
        token=token,
        user=format_user(user),
    )


@router.post("/api/auth/logout")
@router.post("/auth/logout")
async def logout(response: Response):
    """Log out by clearing authentication cookie."""
    response.delete_cookie(key="access_token", samesite="lax")
    return {"message": "Logged out successfully"}


@router.get("/api/auth/me", response_model=UserResponse)
@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return format_user(user)


@router.get("/api/user/favorites", response_model=List[FavoriteResponse])
@router.get("/user/favorites", response_model=List[FavoriteResponse])
async def list_favorites(user: User = Depends(get_current_user)):
    """List all saved favorites for the authenticated user."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(UserFavorite)
            .where(UserFavorite.user_id == user.id)
            .order_by(UserFavorite.created_at.desc())
        )
        res = await session.execute(stmt)
        favorites = res.scalars().all()

        return [
            FavoriteResponse(
                id=fav.id,
                listing_id=fav.listing_id,
                title=fav.title,
                locality=fav.locality,
                city=fav.city,
                price_inr=fav.price_inr,
                bhk=fav.bhk,
                source_url=fav.source_url,
                metadata_json=fav.metadata_json,
                created_at=fav.created_at.isoformat() if fav.created_at else None,
            )
            for fav in favorites
        ]


@router.post("/api/user/favorites", response_model=FavoriteResponse)
@router.post("/user/favorites", response_model=FavoriteResponse)
async def add_favorite(req: FavoriteCreateRequest, user: User = Depends(get_current_user)):
    """Save a property to the user's favorites."""
    async with AsyncSessionLocal() as session:
        # Check if already bookmarked
        conditions = [UserFavorite.user_id == user.id]
        if req.listing_id:
            conditions.append(UserFavorite.listing_id == req.listing_id)
        else:
            conditions.append(UserFavorite.title == req.title)

        stmt = select(UserFavorite).where(and_(*conditions))
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return FavoriteResponse(
                id=existing.id,
                listing_id=existing.listing_id,
                title=existing.title,
                locality=existing.locality,
                city=existing.city,
                price_inr=existing.price_inr,
                bhk=existing.bhk,
                source_url=existing.source_url,
                metadata_json=existing.metadata_json,
                created_at=existing.created_at.isoformat() if existing.created_at else None,
            )

        new_fav = UserFavorite(
            user_id=user.id,
            listing_id=req.listing_id,
            title=req.title,
            locality=req.locality,
            city=req.city,
            price_inr=req.price_inr,
            bhk=req.bhk,
            source_url=req.source_url,
            metadata_json=req.metadata_json,
            created_at=datetime.now(timezone.utc),
        )
        session.add(new_fav)
        await session.commit()
        await session.refresh(new_fav)

        return FavoriteResponse(
            id=new_fav.id,
            listing_id=new_fav.listing_id,
            title=new_fav.title,
            locality=new_fav.locality,
            city=new_fav.city,
            price_inr=new_fav.price_inr,
            bhk=new_fav.bhk,
            source_url=new_fav.source_url,
            metadata_json=new_fav.metadata_json,
            created_at=new_fav.created_at.isoformat() if new_fav.created_at else None,
        )


@router.delete("/api/user/favorites/{favorite_id}")
@router.delete("/user/favorites/{favorite_id}")
async def remove_favorite(favorite_id: int, user: User = Depends(get_current_user)):
    """Remove a property from favorites."""
    async with AsyncSessionLocal() as session:
        stmt = delete(UserFavorite).where(
            and_(UserFavorite.id == favorite_id, UserFavorite.user_id == user.id)
        )
        res = await session.execute(stmt)
        await session.commit()
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Favorite not found.")

    return {"message": "Favorite removed successfully"}
