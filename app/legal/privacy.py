"""Privacy Policy page content."""

import html
from app.config import settings
from app.legal.config import OPERATOR_NAME, CONTACT_EMAIL, LAST_UPDATED, JURISDICTION_CITY


def _e(text: str) -> str:
    return html.escape(text)


def render_privacy() -> str:
    app = _e(settings.APP_NAME)
    operator = _e(OPERATOR_NAME)
    email = _e(CONTACT_EMAIL)
    updated = _e(LAST_UPDATED)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - {app}</title>
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
            <a href="/terms">Terms of Service</a> |
            <strong>Privacy Policy</strong>
        </div>

        <h1>Privacy Policy</h1>
        <div class="meta">Last updated: {updated}</div>

        <p>This policy explains what data {app} collects, how it is used, and your rights regarding that data.</p>

        <h2>1. What we collect</h2>
        <p>{app} collects the following data during your use of the service:</p>
        <ol>
            <li><strong>Chat messages:</strong> The text you type in the chat is sent to Groq (a third-party language model provider) to generate responses. Chat messages are not stored on {app}'s servers after your session ends.</li>
            <li><strong>Search queries:</strong> Property search queries derived from your messages are sent to Tavily (a third-party search API) to retrieve listing data.</li>
            <li><strong>Session identifier:</strong> Gradio assigns a session identifier (cookie) to manage your session state. This is anonymous and not linked to any personal account.</li>
            <li><strong>Server logs:</strong> The server records your IP address and request timestamps for rate limiting and basic operational monitoring. These logs are retained for up to 30 days.</li>
            <li><strong>Cached listing data:</strong> Property listings retrieved from web searches are cached in a database for up to 24 hours to reduce redundant API calls. Locality information is cached for up to 7 days. These caches are automatically cleaned.</li>
            <li><strong>API usage counters:</strong> We track the number of search API calls per day (not linked to individual users) to manage service costs. These counters are retained for up to 30 days.</li>
        </ol>

        <h2>2. No accounts, no data sale</h2>
        <p>{app} does not require user accounts, registration, or login. We do not sell, rent, or share your data with third parties for marketing or advertising purposes.</p>

        <h2>3. No advertising or analytics trackers</h2>
        <p>{app} does not use any advertising trackers, analytics services, or third-party tracking scripts. No tracking pixels, fingerprinting, or behavioral profiling is performed.</p>

        <h2>4. Third-party data processing</h2>
        <p>Your interactions with {app} involve the following third-party services:</p>
        <ol>
            <li><strong>Groq:</strong> Your chat messages are sent to Groq's API for language model processing. Groq's privacy policy is available at <a href="https://groq.com/privacy-policy/" target="_blank" rel="noopener noreferrer">groq.com/privacy-policy</a>.</li>
            <li><strong>Tavily:</strong> Property search queries and locality queries are sent to Tavily's API. Tavily's privacy policy is available at <a href="https://tavily.com/privacy" target="_blank" rel="noopener noreferrer">tavily.com/privacy</a>.</li>
        </ol>
        <p>We encourage you to review these providers' policies to understand how they handle data.</p>

        <h2>5. Data retention</h2>
        <ol>
            <li>Chat messages: Not stored on the server. They exist only in your browser session and are sent to Groq during the session.</li>
            <li>Cached listings: Automatically deleted after 24 hours.</li>
            <li>Locality cache: Automatically deleted after 7 days.</li>
            <li>API usage logs: Automatically deleted after 30 days.</li>
            <li>Server logs: Retained for up to 30 days for operational purposes.</li>
        </ol>

        <h2>6. Your rights</h2>
        <p>In line with the Digital Personal Data Protection Act, 2023 (India), you have the right to:</p>
        <ol>
            <li><strong>Access:</strong> Request information about what data, if any, is associated with your use of the service.</li>
            <li><strong>Correction:</strong> Request correction of any inaccurate data.</li>
            <li><strong>Erasure:</strong> Request deletion of any data related to your use.</li>
        </ol>
        <p>To exercise these rights, send an email to <a href="mailto:{email}">{email}</a> with a description of your request. We will respond within 30 days.</p>

        <h2>7. Children</h2>
        <p>{app} is not intended for use by individuals under 18 years of age. We do not knowingly collect data from children. If you believe a child has used the service, contact us and we will take appropriate action.</p>

        <h2>8. Security measures</h2>
        <p>We implement reasonable security measures to protect data during transmission and storage:</p>
        <ol>
            <li>API keys and credentials are stored as environment variables, never in code or client-side.</li>
            <li>All inputs are validated and sanitized.</li>
            <li>Database queries use parameterized statements to prevent injection.</li>
            <li>Rate limiting is applied to prevent abuse.</li>
        </ol>
        <p>No system is perfectly secure. We cannot guarantee absolute security of data transmitted over the internet.</p>

        <h2>9. Cookies</h2>
        <p>Gradio, the UI framework used by {app}, sets a session cookie to manage application state. This cookie is essential for the service to function and is not used for tracking or analytics. No other cookies are set by {app}.</p>

        <h2>10. Changes to this policy</h2>
        <p>We may update this privacy policy from time to time. Changes take effect when posted on this page. We recommend checking this page periodically.</p>

        <h2>11. Grievance contact</h2>
        <p>For any privacy-related concerns or grievances, contact: <a href="mailto:{email}">{email}</a></p>
        <p>We aim to resolve all grievances within 30 days of receipt.</p>

        <h2>12. Legal framework</h2>
        <p>This policy is drafted with reference to India's Digital Personal Data Protection Act, 2023. We are committed to complying with applicable data protection laws. This reference is for informational purposes and does not constitute a certification or legal opinion.</p>

        <div class="footer">
            <a href="/">{app}</a> |
            <a href="/terms">Terms</a> |
            <a href="/privacy">Privacy</a>
        </div>
    </div>
</body>
</html>"""
