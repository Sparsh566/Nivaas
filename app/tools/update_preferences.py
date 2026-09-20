"""Tool: update_preferences - Update ranking weights based on user preferences."""

from pydantic import BaseModel, Field
from app.ranking.weights import reprioritize, resolve_factor_name


class UpdatePreferencesArgs(BaseModel):
    priorities: list[str] = Field(
        ..., description="List of factors to prioritize, e.g. ['metro', 'budget']"
    )
    filters: dict | None = Field(
        None, description="Additional filters to apply"
    )


UPDATE_PREFERENCES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_preferences",
        "description": "Update the user's ranking preferences. Use when the user says things like 'prioritize metro' or 'budget is more important'.",
        "parameters": {
            "type": "object",
            "properties": {
                "priorities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Factors to prioritize: budget, location, metro, connectivity, area, amenities, furnishing, parking, property_type",
                },
                "filters": {
                    "type": "object",
                    "description": "Additional filters to apply",
                },
            },
            "required": ["priorities"],
        },
    },
}


async def execute(
    args: UpdatePreferencesArgs, current_weights: dict[str, float]
) -> dict:
    """Update weights based on user priorities."""
    updated_weights = dict(current_weights)
    applied = []
    unknown = []

    for priority in args.priorities:
        factor = resolve_factor_name(priority)
        if factor:
            updated_weights = reprioritize(updated_weights, factor)
            applied.append({"input": priority, "factor": factor})
        else:
            unknown.append(priority)

    result = {
        "weights": updated_weights,
        "applied": applied,
        "message": "",
    }

    if applied:
        factor_names = [a["factor"] for a in applied]
        result["message"] = f"Updated priorities: {', '.join(factor_names)} now have higher weight."

    if unknown:
        result["message"] += (
            f" Could not resolve these preferences: {', '.join(unknown)}. "
            "Known factors: budget, location, metro/connectivity, area, amenities, furnishing, parking, property type."
        )

    return result
