"""Initial tables: listings_cache, api_usage, locality_cache

Revision ID: 001
Revises:
Create Date: 2026-09-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listings_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("locality", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("price_inr", sa.BigInteger, nullable=False),
        sa.Column("bhk", sa.Integer, nullable=True),
        sa.Column("area_sqft", sa.Integer, nullable=True),
        sa.Column("property_type", sa.String(50), nullable=True),
        sa.Column("furnishing", sa.String(50), nullable=True),
        sa.Column("parking", sa.String(50), nullable=True),
        sa.Column("amenities", ARRAY(sa.String), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("source_domain", sa.String(200), nullable=False),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column("query_key", sa.String(500), nullable=False, index=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("endpoint", sa.String(100), nullable=False),
        sa.Column("credits_used", sa.Integer, nullable=False, server_default="1"),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "locality_cache",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("locality", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("source_urls", ARRAY(sa.String), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("locality_cache")
    op.drop_table("api_usage")
    op.drop_table("listings_cache")
