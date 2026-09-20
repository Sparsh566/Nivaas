"""Deterministic scoring engine for property listings.

Uses pandas/numpy for vectorized scoring. Each factor is scored [0,1].
Missing factors are skipped and weights renormalized per listing.
"""

import math
from typing import Optional
from rapidfuzz import fuzz

from app.ranking.weights import normalize_weights
from app.config import WEIGHT_LABELS


def score_listings(
    listings: list[dict],
    requirements: dict,
    weights: dict[str, float],
) -> list[dict]:
    """Score and rank listings against requirements.

    Args:
        listings: list of listing dicts with fields from ListingCache.
        requirements: dict with keys like city, locality, max_budget_inr, bhk,
                      min_area_sqft, property_type, furnishing, amenities, parking.
        weights: dict of factor_name to weight value.

    Returns:
        List of listing dicts augmented with match_score, factor_breakdown,
        reasons, and considerations, sorted by match_score descending.
    """
    if not listings:
        return []

    max_budget = requirements.get("max_budget_inr", 0)
    req_locality = requirements.get("locality", "")
    req_bhk = requirements.get("bhk")
    req_min_area = requirements.get("min_area_sqft")
    req_property_type = requirements.get("property_type", "")
    req_furnishing = requirements.get("furnishing", "")
    req_amenities = set(
        a.lower().strip() for a in requirements.get("amenities", []) if a
    )
    req_parking = requirements.get("parking")
    has_connectivity = requirements.get("has_connectivity_data", False)

    scored = []
    for listing in listings:
        factors = {}
        available = set()

        # Budget fit
        if max_budget and listing.get("price_inr"):
            price = listing["price_inr"]
            ratio = price / max_budget if max_budget > 0 else 1
            if 0.70 <= ratio <= 1.0:
                factors["budget_fit"] = 1.0
            elif ratio < 0.70:
                factors["budget_fit"] = 0.8
            elif 1.0 < ratio <= 1.05:
                factors["budget_fit"] = 0.5
            else:
                factors["budget_fit"] = 0.0
            available.add("budget_fit")

        # Location match
        if req_locality and listing.get("locality"):
            listing_loc = listing["locality"].strip().lower()
            req_loc = req_locality.strip().lower()
            if listing_loc == req_loc:
                factors["location"] = 1.0
            else:
                fuzzy_score = fuzz.ratio(listing_loc, req_loc) / 100.0
                if fuzzy_score > 0.7:
                    factors["location"] = fuzzy_score
                else:
                    factors["location"] = 0.3
            available.add("location")
        elif not req_locality:
            factors["location"] = 0.7
            available.add("location")

        # Area
        if req_min_area and listing.get("area_sqft"):
            if listing["area_sqft"] >= req_min_area:
                factors["area"] = 1.0
            else:
                factors["area"] = listing["area_sqft"] / req_min_area
            available.add("area")
        elif listing.get("area_sqft"):
            factors["area"] = 0.8
            available.add("area")

        # Property type
        if req_property_type and listing.get("property_type"):
            if listing["property_type"].lower() == req_property_type.lower():
                factors["property_type"] = 1.0
            else:
                factors["property_type"] = 0.0
            available.add("property_type")
        elif listing.get("property_type"):
            factors["property_type"] = 0.8
            available.add("property_type")

        # Furnishing
        if req_furnishing and listing.get("furnishing"):
            if listing["furnishing"].lower() == req_furnishing.lower():
                factors["furnishing"] = 1.0
            else:
                factors["furnishing"] = 0.3
            available.add("furnishing")
        elif listing.get("furnishing"):
            factors["furnishing"] = 0.7
            available.add("furnishing")

        # Amenities
        if req_amenities and listing.get("amenities"):
            listing_amenities = set(
                a.lower().strip() for a in listing["amenities"] if a
            )
            if req_amenities:
                overlap = len(req_amenities & listing_amenities)
                factors["amenities"] = overlap / len(req_amenities)
            else:
                factors["amenities"] = 0.5
            available.add("amenities")

        # Parking
        if listing.get("parking"):
            parking_val = listing["parking"].lower()
            if req_parking:
                factors["parking"] = 1.0 if "yes" in parking_val or "available" in parking_val else 0.0
            else:
                factors["parking"] = 0.7 if "yes" in parking_val or "available" in parking_val else 0.3
            available.add("parking")

        # Connectivity (only if we have data)
        if has_connectivity and listing.get("connectivity_score") is not None:
            factors["connectivity"] = listing["connectivity_score"]
            available.add("connectivity")

        # Compute weighted score
        local_weights = normalize_weights(weights, available)
        if not local_weights:
            final_score = 0
        else:
            final_score = sum(
                local_weights.get(f, 0) * factors.get(f, 0) for f in local_weights
            )

        match_score = round(final_score * 100)

        # Build factor breakdown
        breakdown = []
        for factor_name, score in factors.items():
            breakdown.append({
                "factor": factor_name,
                "label": WEIGHT_LABELS.get(factor_name, factor_name),
                "score": round(score, 2),
                "weight": round(local_weights.get(factor_name, 0), 3),
                "contribution": round(
                    local_weights.get(factor_name, 0) * score * 100, 1
                ),
            })

        # Deterministic reasons and considerations
        reasons, considerations = _generate_explanations(factors, listing, requirements)

        scored.append({
            **listing,
            "match_score": match_score,
            "factor_breakdown": sorted(
                breakdown, key=lambda x: x["contribution"], reverse=True
            ),
            "reasons": reasons,
            "considerations": considerations,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["match_score"], reverse=True)

    # Tie-breaker using cosine similarity
    scored = _apply_tiebreaker(scored, requirements, weights)

    return scored


def _generate_explanations(
    factors: dict[str, float],
    listing: dict,
    requirements: dict,
) -> tuple[list[str], list[str]]:
    """Generate deterministic reasons and considerations from factor scores."""
    reasons = []
    considerations = []

    budget_score = factors.get("budget_fit")
    if budget_score is not None:
        if budget_score >= 0.9:
            reasons.append("Well within your budget")
        elif budget_score >= 0.7:
            reasons.append("Below your budget range")
        elif budget_score == 0.5:
            considerations.append("Slightly over your stated budget (within 5%)")
        elif budget_score < 0.5:
            considerations.append("Over your budget")

    location_score = factors.get("location")
    if location_score is not None:
        if location_score >= 0.95:
            reasons.append("Exact locality match")
        elif location_score >= 0.7:
            reasons.append("Close locality match")
        elif location_score < 0.5:
            considerations.append("Different locality from your preference")

    area_score = factors.get("area")
    if area_score is not None:
        if area_score >= 1.0:
            reasons.append("Meets your area requirement")
        elif area_score >= 0.9:
            pass  # close enough, no note needed
        elif area_score < 0.9:
            considerations.append("Area is smaller than your minimum")

    pt_score = factors.get("property_type")
    if pt_score is not None:
        if pt_score >= 1.0:
            reasons.append("Matches your preferred property type")
        elif pt_score == 0.0:
            considerations.append("Different property type than requested")

    furnishing_score = factors.get("furnishing")
    if furnishing_score is not None:
        if furnishing_score >= 1.0:
            reasons.append("Furnishing matches your preference")
        elif furnishing_score < 0.5:
            considerations.append("Different furnishing level")

    amenity_score = factors.get("amenities")
    if amenity_score is not None:
        if amenity_score >= 0.8:
            reasons.append("Most requested amenities available")
        elif amenity_score >= 0.5:
            reasons.append("Some requested amenities available")
        elif amenity_score < 0.5:
            considerations.append("Few of your requested amenities found")

    parking_score = factors.get("parking")
    if parking_score is not None:
        if parking_score >= 0.8:
            reasons.append("Parking available")
        elif parking_score == 0.0:
            considerations.append("Parking may not be available")

    connectivity_score = factors.get("connectivity")
    if connectivity_score is not None:
        if connectivity_score >= 0.7:
            reasons.append("Good connectivity to metro/IT parks")
        elif connectivity_score < 0.4:
            considerations.append("Limited connectivity data available")

    return reasons, considerations


def _apply_tiebreaker(
    scored: list[dict],
    requirements: dict,
    weights: dict[str, float],
) -> list[dict]:
    """Use cosine similarity as a tie-breaker when two listings have the same score."""
    if len(scored) <= 1:
        return scored

    # Group by match_score
    groups: dict[int, list[int]] = {}
    for i, item in enumerate(scored):
        score = item["match_score"]
        if score not in groups:
            groups[score] = []
        groups[score].append(i)

    # For groups with ties, compute cosine similarity
    factor_names = sorted(weights.keys())
    req_vector = [weights.get(f, 0.0) for f in factor_names]
    norm_req = math.sqrt(sum(x * x for x in req_vector))

    for score, indices in groups.items():
        if len(indices) <= 1:
            continue

        similarities = []
        for idx in indices:
            item = scored[idx]
            listing_vector = []
            for f in factor_names:
                bd = [b for b in item.get("factor_breakdown", []) if b["factor"] == f]
                if bd:
                    listing_vector.append(float(bd[0]["score"]))
                else:
                    listing_vector.append(0.0)

            norm_list = math.sqrt(sum(x * x for x in listing_vector))
            if norm_req > 0 and norm_list > 0:
                dot = sum(a * b for a, b in zip(req_vector, listing_vector))
                sim = dot / (norm_req * norm_list)
            else:
                sim = 0.0
            similarities.append((idx, sim))

        # Sort by similarity descending within the tie group
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Reorder indices
        sorted_indices = [s[0] for s in similarities]
        items_in_group = [scored[i] for i in sorted_indices]

        for new_pos, orig_idx in enumerate(indices):
            if new_pos < len(items_in_group):
                scored[orig_idx] = items_in_group[new_pos]

    return scored
