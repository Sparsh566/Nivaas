"""Weight management for ranking factors."""

from app.config import DEFAULT_WEIGHTS


def get_default_weights() -> dict[str, float]:
    """Return a copy of the default weights."""
    return dict(DEFAULT_WEIGHTS)


def reprioritize(weights: dict[str, float], factor_name: str) -> dict[str, float]:
    """Multiply the named factor's weight by 2, then renormalize all to sum 1.

    If the factor name is not in weights, return weights unchanged.
    """
    if factor_name not in weights:
        return dict(weights)

    new_weights = dict(weights)
    new_weights[factor_name] = new_weights[factor_name] * 2
    return normalize_weights(new_weights)


def normalize_weights(
    weights: dict[str, float],
    available_factors: set[str] | None = None,
) -> dict[str, float]:
    """Normalize weights to sum 1, optionally filtering to available factors.

    If available_factors is given, only those factors are included and
    renormalized. Missing factors are excluded.
    """
    if available_factors is not None:
        filtered = {k: v for k, v in weights.items() if k in available_factors}
    else:
        filtered = dict(weights)

    total = sum(filtered.values())
    if total == 0:
        # Equal weights as fallback
        n = len(filtered)
        if n == 0:
            return {}
        return {k: 1.0 / n for k in filtered}

    return {k: v / total for k, v in filtered.items()}


FACTOR_ALIASES: dict[str, str] = {
    "budget": "budget_fit",
    "price": "budget_fit",
    "cost": "budget_fit",
    "location": "location",
    "locality": "location",
    "area": "area",
    "size": "area",
    "carpet area": "area",
    "metro": "connectivity",
    "connectivity": "connectivity",
    "it park": "connectivity",
    "transport": "connectivity",
    "amenities": "amenities",
    "amenity": "amenities",
    "type": "property_type",
    "property type": "property_type",
    "furnishing": "furnishing",
    "furnished": "furnishing",
    "parking": "parking",
}


def resolve_factor_name(user_input: str) -> str | None:
    """Resolve a user-stated preference to a canonical factor name."""
    normalized = user_input.strip().lower()
    return FACTOR_ALIASES.get(normalized)
