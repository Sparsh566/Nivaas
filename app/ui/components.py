"""UI rendering helpers for listings, comparisons, EMI, and agent steps."""

import html
from app.ranking.parsers import format_price_indian, format_indian_number
from app.config import WEIGHT_LABELS


def _escape(text: str | None) -> str:
    """Escape HTML to prevent XSS."""
    if not text:
        return ""
    return html.escape(str(text))


def _safe_url(url: str | None) -> str:
    """Validate URL scheme (http/https only)."""
    if not url:
        return "#"
    url = str(url).strip()
    if url.startswith("http://") or url.startswith("https://"):
        return _escape(url)
    return "#"


def render_listing_card(listing: dict, rank: int) -> str:
    """Render a single listing as an HTML card."""
    title = _escape(listing.get("title") or "Property listing")
    locality = _escape(listing.get("locality", ""))
    city = _escape(listing.get("city", ""))
    price = listing.get("price_inr", 0)
    price_str = format_price_indian(price) if price else "Price not available"
    bhk = listing.get("bhk")
    bhk_str = f"{bhk} BHK" if bhk else "BHK not specified"
    area = listing.get("area_sqft")
    area_str = f"{area} sq ft" if area else "Area not specified"
    match_score = listing.get("match_score", 0)
    source_url = _safe_url(listing.get("source_url"))
    source_domain = _escape(listing.get("source_domain", "Source"))
    fetched_at = _escape(listing.get("fetched_at", ""))

    reasons = listing.get("reasons", [])
    considerations = listing.get("considerations", [])

    reasons_html = ""
    if reasons:
        items = "".join(f"<li>{_escape(r)}</li>" for r in reasons[:3])
        reasons_html = f"<ul style='margin:4px 0;padding-left:18px;font-size:13px;color:#1C1F23;'>{items}</ul>"

    considerations_html = ""
    if considerations:
        items = "".join(f"<li>{_escape(c)}</li>" for c in considerations[:2])
        considerations_html = f"<ul style='margin:4px 0;padding-left:18px;font-size:13px;color:#5B6068;'>{items}</ul>"

    # Factor breakdown
    breakdown = listing.get("factor_breakdown", [])
    breakdown_html = ""
    if breakdown:
        rows = ""
        for b in breakdown[:6]:
            label = _escape(b.get("label", b.get("factor", "")))
            score = b.get("score", 0)
            weight = b.get("weight", 0)
            contrib = b.get("contribution", 0)
            bar_width = int(score * 100)
            rows += f"""<tr>
                <td style='font-size:12px;padding:2px 6px;'>{label}</td>
                <td style='font-size:12px;padding:2px 6px;'>
                    <div style='background:#edece8;border-radius:3px;height:8px;width:60px;display:inline-block;vertical-align:middle;'>
                        <div style='background:#1F5F5B;border-radius:3px;height:8px;width:{bar_width}%;'></div>
                    </div>
                    <span style='font-size:11px;color:#5B6068;margin-left:4px;'>{score:.0%}</span>
                </td>
            </tr>"""
        breakdown_html = f"""<details style='margin-top:6px;'>
            <summary style='font-size:12px;color:#5B6068;cursor:pointer;'>Score breakdown</summary>
            <table style='width:100%;border-collapse:collapse;margin-top:4px;'>{rows}</table>
        </details>"""

    return f"""<div style='border:1px solid #D9D6CE;border-radius:6px;padding:12px;margin-bottom:8px;background:#FFFFFF;'>
        <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
            <div>
                <div style='font-size:11px;color:#5B6068;'>#{rank}</div>
                <div style='font-weight:600;font-size:15px;color:#1C1F23;'>{title}</div>
                <div style='font-size:13px;color:#5B6068;'>{locality}, {city}</div>
            </div>
            <div style='background:#1F5F5B;color:#FFFFFF;padding:2px 8px;border-radius:4px;font-size:13px;font-weight:600;'>
                {match_score}% match
            </div>
        </div>
        <div style='display:flex;gap:16px;margin-top:8px;font-size:14px;'>
            <span style='font-weight:600;'>{price_str}</span>
            <span>{bhk_str}</span>
            <span>{area_str}</span>
        </div>
        {reasons_html}
        {considerations_html}
        {breakdown_html}
        <div style='margin-top:8px;font-size:12px;color:#5B6068;border-top:1px solid #edece8;padding-top:6px;'>
            Source: <a href='{source_url}' target='_blank' rel='noopener noreferrer' style='color:#1F5F5B;'>{source_domain}</a>
            {f" | Fetched: {fetched_at[:19]}" if fetched_at else ""}
        </div>
    </div>"""


def render_shortlist(listings: list[dict], is_demo: bool = False) -> str:
    """Render the full shortlist as HTML."""
    if not listings:
        return "<div style='padding:24px;text-align:center;color:#5B6068;'>No listings found yet. Try searching for a property.</div>"

    parts = []
    if is_demo:
        parts.append(
            "<div style='background:#f0f7f6;border:1px solid #1F5F5B;border-radius:6px;padding:8px 12px;font-size:14px;color:#1F5F5B;margin-bottom:8px;'>"
            "Demo mode: these are sample listings, not live."
            "</div>"
        )

    parts.append(
        f"<div style='font-size:13px;color:#5B6068;margin-bottom:8px;'>"
        f"Found {len(listings)} listing(s). "
        f"Listings are read from public web pages and may be outdated or sold. Confirm with the source."
        f"</div>"
    )

    for i, listing in enumerate(listings, 1):
        parts.append(render_listing_card(listing, i))

    return "\n".join(parts)


def render_comparison_table(listings: list[dict], tradeoffs: list[str]) -> str:
    """Render a comparison table as HTML."""
    if not listings:
        return "<div style='padding:24px;color:#5B6068;'>Select 2 or 3 listings to compare.</div>"

    headers = ["Attribute"] + [_escape(l.get("title", f"Listing {i+1}"))[:30] for i, l in enumerate(listings)]
    header_row = "".join(f"<th style='padding:8px;text-align:left;border-bottom:2px solid #D9D6CE;font-size:13px;'>{h}</th>" for h in headers)

    attributes = [
        ("Price", "price_formatted"),
        ("BHK", "bhk"),
        ("Area (sq ft)", "area_sqft"),
        ("Price/sq ft", "price_per_sqft"),
        ("Type", "property_type"),
        ("Furnishing", "furnishing"),
        ("Parking", "parking"),
        ("Locality", "locality"),
        ("Source", "source_domain"),
    ]

    rows = ""
    for label, key in attributes:
        cells = f"<td style='padding:6px 8px;font-size:13px;font-weight:500;border-bottom:1px solid #edece8;'>{label}</td>"
        values = [l.get(key) for l in listings]
        for v in values:
            display = _escape(str(v)) if v is not None else "N/A"
            if key == "price_per_sqft" and v:
                display = f"{v:,}"
            cells += f"<td style='padding:6px 8px;font-size:13px;border-bottom:1px solid #edece8;'>{display}</td>"
        rows += f"<tr>{cells}</tr>"

    tradeoff_html = ""
    if tradeoffs:
        items = "".join(f"<li style='font-size:13px;margin-bottom:4px;'>{_escape(t)}</li>" for t in tradeoffs)
        tradeoff_html = f"<div style='margin-top:12px;'><strong style='font-size:13px;'>Trade-offs:</strong><ul style='padding-left:18px;margin-top:4px;'>{items}</ul></div>"

    return f"""<table style='width:100%;border-collapse:collapse;background:#FFFFFF;border:1px solid #D9D6CE;border-radius:6px;'>
        <thead><tr>{header_row}</tr></thead>
        <tbody>{rows}</tbody>
    </table>
    {tradeoff_html}"""


def render_emi_result(result: dict) -> str:
    """Render EMI calculation results as HTML."""
    if "error" in result:
        return f"<div style='color:#c0392b;padding:12px;'>{_escape(result['error'])}</div>"

    income_html = ""
    if result.get("emi_to_income_pct") is not None:
        pct = result["emi_to_income_pct"]
        note = result.get("income_note", "")
        color = "#c0392b" if result.get("income_warning") else "#1C1F23"
        income_html = f"""<tr>
            <td style='padding:6px 8px;font-size:14px;'>EMI to income ratio</td>
            <td style='padding:6px 8px;font-size:14px;font-weight:600;color:{color};'>{pct}%</td>
        </tr>"""
        if note:
            income_html += f"""<tr><td colspan='2' style='padding:4px 8px;font-size:12px;color:{color};'>{_escape(note)}</td></tr>"""

    return f"""<div style='background:#FFFFFF;border:1px solid #D9D6CE;border-radius:6px;padding:16px;'>
        <table style='width:100%;border-collapse:collapse;'>
            <tr>
                <td style='padding:6px 8px;font-size:14px;color:#5B6068;'>Loan amount</td>
                <td style='padding:6px 8px;font-size:14px;font-weight:600;'>{_escape(result.get('loan_amount_formatted', ''))}</td>
            </tr>
            <tr>
                <td style='padding:6px 8px;font-size:14px;color:#5B6068;'>Monthly EMI</td>
                <td style='padding:6px 8px;font-size:16px;font-weight:700;color:#1F5F5B;'>{_escape(result.get('emi_formatted', ''))}</td>
            </tr>
            <tr>
                <td style='padding:6px 8px;font-size:14px;color:#5B6068;'>Total interest</td>
                <td style='padding:6px 8px;font-size:14px;'>{_escape(result.get('total_interest_formatted', ''))}</td>
            </tr>
            <tr>
                <td style='padding:6px 8px;font-size:14px;color:#5B6068;'>Total payable</td>
                <td style='padding:6px 8px;font-size:14px;'>{_escape(result.get('total_payable_formatted', ''))}</td>
            </tr>
            {income_html}
        </table>
        <div style='margin-top:8px;font-size:12px;color:#5B6068;border-top:1px solid #edece8;padding-top:8px;'>
            This is an estimate. Actual EMI depends on the lender's terms and your credit profile.
        </div>
    </div>"""


def render_agent_steps(steps: list[dict]) -> str:
    """Render agent steps as HTML."""
    if not steps:
        return "<div style='font-size:13px;color:#5B6068;'>No tool calls made yet.</div>"

    parts = []
    for i, step in enumerate(steps, 1):
        tool = _escape(step.get("tool", "unknown"))
        args = step.get("arguments", {})
        args_str = ", ".join(f"{k}={_escape(str(v))}" for k, v in args.items() if v is not None)
        summary = _escape(step.get("result_summary", ""))
        parts.append(
            f"<div style='padding:4px 0;border-bottom:1px solid #edece8;font-size:12px;'>"
            f"<span style='color:#1F5F5B;font-weight:500;'>{i}. {tool}</span>"
            f"({args_str})"
            f"<br/><span style='color:#5B6068;'>{summary}</span>"
            f"</div>"
        )

    return "\n".join(parts)


def render_requirements_panel(requirements: dict, weights: dict) -> str:
    """Render the current requirements and weights."""
    if not requirements:
        return "<div style='font-size:13px;color:#5B6068;'>No search requirements yet.</div>"

    parts = ["<div style='font-size:13px;'>"]

    if requirements.get("city"):
        parts.append(f"<div><strong>City:</strong> {_escape(requirements['city'])}</div>")
    if requirements.get("locality"):
        parts.append(f"<div><strong>Locality:</strong> {_escape(requirements['locality'])}</div>")
    if requirements.get("max_budget_inr"):
        parts.append(f"<div><strong>Budget:</strong> up to {format_price_indian(requirements['max_budget_inr'])}</div>")
    if requirements.get("bhk"):
        parts.append(f"<div><strong>BHK:</strong> {requirements['bhk']}</div>")
    if requirements.get("property_type"):
        parts.append(f"<div><strong>Type:</strong> {_escape(requirements['property_type'])}</div>")

    parts.append("<div style='margin-top:8px;'><strong>Weights:</strong></div>")
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    for factor, weight in sorted_weights:
        label = WEIGHT_LABELS.get(factor, factor)
        pct = round(weight * 100)
        parts.append(
            f"<div style='display:flex;align-items:center;gap:6px;'>"
            f"<span style='width:140px;font-size:12px;'>{_escape(label)}</span>"
            f"<div style='background:#edece8;border-radius:3px;height:6px;width:80px;'>"
            f"<div style='background:#1F5F5B;border-radius:3px;height:6px;width:{pct}%;'></div>"
            f"</div>"
            f"<span style='font-size:11px;color:#5B6068;'>{pct}%</span>"
            f"</div>"
        )

    parts.append("</div>")
    return "\n".join(parts)


def render_how_matching_works() -> str:
    """Render the 'How Matching Works' explanation."""
    from app.config import DEFAULT_WEIGHTS

    rows = ""
    for factor, weight in sorted(DEFAULT_WEIGHTS.items(), key=lambda x: x[1], reverse=True):
        label = WEIGHT_LABELS.get(factor, factor)
        pct = round(weight * 100)
        rows += f"""<tr>
            <td style='padding:4px 8px;font-size:14px;'>{_escape(label)}</td>
            <td style='padding:4px 8px;font-size:14px;font-weight:500;'>{pct}%</td>
        </tr>"""

    return f"""<div style='padding:12px;'>
        <h3 style='font-size:16px;color:#1C1F23;margin-bottom:12px;'>How matching works</h3>
        <p style='font-size:14px;color:#5B6068;margin-bottom:12px;'>
            Each listing is scored against your requirements using these factors. Scores are
            between 0 and 100. When a factor's data is missing for a listing, it is skipped and
            the remaining weights are renormalized.
        </p>
        <table style='width:100%;border-collapse:collapse;border:1px solid #D9D6CE;border-radius:6px;background:#FFFFFF;'>
            <thead>
                <tr>
                    <th style='padding:6px 8px;text-align:left;border-bottom:2px solid #D9D6CE;font-size:13px;'>Factor</th>
                    <th style='padding:6px 8px;text-align:left;border-bottom:2px solid #D9D6CE;font-size:13px;'>Default weight</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style='font-size:13px;color:#5B6068;margin-top:12px;'>
            Say "prioritize metro" or "budget is more important" to adjust the weights.
            The named factor's weight is doubled and all weights renormalize to sum 100%.
        </p>
        <p style='font-size:13px;color:#5B6068;margin-top:8px;'>
            Tie-breakers use cosine similarity between your requirement profile and each listing's factor scores.
        </p>
    </div>"""
