"""Terms of Service page content."""

import html
from app.config import settings
from app.legal.config import OPERATOR_NAME, CONTACT_EMAIL, LAST_UPDATED, JURISDICTION_CITY


def _e(text: str) -> str:
    return html.escape(text)


def render_terms() -> str:
    app = _e(settings.APP_NAME)
    operator = _e(OPERATOR_NAME)
    email = _e(CONTACT_EMAIL)
    updated = _e(LAST_UPDATED)
    city = _e(JURISDICTION_CITY)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - {app}</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #F7F6F2;
            color: #1C1F23;
            line-height: 1.6;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 720px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 4px;
        }}
        h2 {{
            font-size: 18px;
            margin-top: 32px;
            color: #1C1F23;
        }}
        p, li {{
            font-size: 15px;
            color: #393c42;
        }}
        a {{
            color: #1F5F5B;
            text-decoration: none;
        }}
        a:hover {{
            opacity: 0.8;
        }}
        .meta {{
            font-size: 13px;
            color: #5B6068;
            margin-bottom: 24px;
        }}
        .nav {{
            font-size: 14px;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 1px solid #D9D6CE;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #D9D6CE;
            font-size: 13px;
            color: #5B6068;
        }}
        ol {{
            padding-left: 20px;
        }}
        ol > li {{
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/">{app}</a> |
            <strong>Terms of Service</strong> |
            <a href="/privacy">Privacy Policy</a>
        </div>

        <h1>Terms of Service</h1>
        <div class="meta">Last updated: {updated}</div>

        <p>By using {app}, you agree to these terms. If you do not agree, do not use the service.</p>

        <h2>1. What this service is</h2>
        <p>{app} is an informational tool that searches for property listings on public real estate websites and presents them in a structured format. Listings are retrieved from third-party websites via a search service and are not created, verified, or endorsed by {app}. The service operates over publicly available web data and does not maintain its own property inventory.</p>

        <h2>2. Not professional advice</h2>
        <p>{app} does not provide financial, legal, or real estate advice. Information presented, including property details, match scores, and locality information, is for informational purposes only. Consult qualified professionals before making any property purchase decision.</p>

        <h2>3. EMI estimates</h2>
        <p>The EMI calculator provides estimates based on the standard amortization formula. Actual loan terms, interest rates, and EMI amounts depend on the lender, your credit profile, and market conditions. EMI figures shown by {app} are not offers, quotes, or guarantees from any financial institution.</p>

        <h2>4. Third-party content</h2>
        <p>Property listings and locality information are sourced from third-party websites via web search. This content may be outdated, inaccurate, or no longer available. {app} displays the source and retrieval time for each listing. Always verify details directly with the source before acting on any information.</p>

        <h2>5. No guarantee of accuracy or availability</h2>
        <p>{app} is provided "as is" without warranties of any kind. We do not guarantee that the service will be available, uninterrupted, or error-free, or that the information presented is complete, accurate, or current. Search results depend on third-party services (property portals, search APIs, and language models) that may change or become unavailable.</p>

        <h2>6. Acceptable use</h2>
        <p>You agree not to:</p>
        <ol>
            <li>Scrape, crawl, or bulk-download content from {app}.</li>
            <li>Use the service for any unlawful purpose.</li>
            <li>Attempt to circumvent rate limits or access controls.</li>
            <li>Attempt to override, manipulate, or inject instructions into the AI assistant.</li>
            <li>Misrepresent the output as verified market data or professional advice.</li>
        </ol>

        <h2>7. Intellectual property</h2>
        <p>The {app} application code, design, and branding are the property of the operator. Property listings belong to their respective publishers. {app} claims no ownership of third-party content.</p>

        <h2>8. Limitation of liability</h2>
        <p>To the maximum extent permitted by law, {app} and its operator shall not be liable for any direct, indirect, incidental, or consequential damages arising from the use of this service, including but not limited to financial loss from reliance on property information or EMI estimates.</p>

        <h2>9. Changes to these terms</h2>
        <p>We may update these terms at any time. Changes take effect when posted on this page. Continued use after changes constitutes acceptance. Check this page periodically.</p>

        <h2>10. Governing law</h2>
        <p>These terms are governed by the laws of India. Any disputes shall be subject to the jurisdiction of the courts in {city if city and city != "[City to be filled]" else "India"}.</p>

        <h2>11. Contact</h2>
        <p>For questions about these terms, contact: <a href="mailto:{email}">{email}</a></p>

        <div class="footer">
            <a href="/">{app}</a> |
            <a href="/terms">Terms</a> |
            <a href="/privacy">Privacy</a>
        </div>
    </div>
</body>
</html>"""
