"""Custom CSS for Nivaas. Flat solid colors, no glassmorphism, no heavy shadows."""

CUSTOM_CSS = """
/* Base styles */
.gradio-container {
    max-width: 1120px !important;
    margin: 0 auto !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    background-color: #F7F6F2 !important;
    color: #1C1F23 !important;
    font-size: 16px !important;
    line-height: 1.5 !important;
}

/* Hide Gradio footer */
footer {
    display: none !important;
}

/* Hide API link */
.api-link,
[class*="api-link"],
.built-with {
    display: none !important;
}

/* Solid backgrounds only */
* {
    background-image: none !important;
}

/* Button styles */
button.primary {
    background-color: #1F5F5B !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    transition: background-color 150ms, opacity 150ms !important;
    font-weight: 500 !important;
}

button.primary:hover {
    background-color: #154544 !important;
}

button.secondary {
    background-color: #FFFFFF !important;
    color: #1C1F23 !important;
    border: 1px solid #D9D6CE !important;
    border-radius: 6px !important;
    transition: background-color 150ms, border-color 150ms !important;
}

button.secondary:hover {
    border-color: #1F5F5B !important;
}

/* Input styles */
input, textarea, select {
    border: 1px solid #D9D6CE !important;
    border-radius: 6px !important;
    background-color: #FFFFFF !important;
    color: #1C1F23 !important;
    transition: border-color 150ms !important;
}

input:focus, textarea:focus, select:focus {
    border-color: #1F5F5B !important;
    outline: 2px solid #1F5F5B !important;
    outline-offset: 2px !important;
}

/* Chatbot styles */
.chatbot {
    background-color: #FFFFFF !important;
    border: 1px solid #D9D6CE !important;
    border-radius: 6px !important;
}

.chatbot .message {
    border-radius: 6px !important;
}

.chatbot .user {
    background-color: #f0f7f6 !important;
}

.chatbot .bot {
    background-color: #FFFFFF !important;
}

/* Tab styles */
.tab-nav button {
    border-radius: 6px 6px 0 0 !important;
    transition: color 150ms, border-color 150ms !important;
}

.tab-nav button.selected {
    color: #1F5F5B !important;
    border-bottom-color: #1F5F5B !important;
}

/* Accordion styles */
.accordion {
    border: 1px solid #D9D6CE !important;
    border-radius: 6px !important;
}

/* Card-like panels */
.panel {
    background-color: #FFFFFF !important;
    border: 1px solid #D9D6CE !important;
    border-radius: 6px !important;
    padding: 16px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}

/* Links */
a {
    color: #1F5F5B !important;
    transition: opacity 150ms !important;
}

a:hover {
    opacity: 0.8 !important;
}

/* Focus ring for keyboard accessibility */
*:focus-visible {
    outline: 2px solid #1F5F5B !important;
    outline-offset: 2px !important;
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
    * {
        transition: none !important;
        animation: none !important;
    }
}

/* Responsive */
@media (max-width: 768px) {
    .gradio-container {
        padding: 8px !important;
    }
}

/* Muted text */
.muted {
    color: #5B6068 !important;
}

/* Disclaimer text */
.disclaimer {
    font-size: 13px !important;
    color: #5B6068 !important;
    border-top: 1px solid #D9D6CE !important;
    padding-top: 8px !important;
    margin-top: 8px !important;
}

/* Demo banner */
.demo-banner {
    background-color: #f0f7f6 !important;
    border: 1px solid #1F5F5B !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 14px !important;
    color: #1F5F5B !important;
    margin-bottom: 8px !important;
}

/* Agent steps */
.agent-steps {
    font-size: 13px !important;
    color: #5B6068 !important;
}

.agent-steps .step {
    padding: 4px 0 !important;
    border-bottom: 1px solid #edece8 !important;
}

/* Listing card */
.listing-card {
    border: 1px solid #D9D6CE !important;
    border-radius: 6px !important;
    padding: 12px !important;
    margin-bottom: 8px !important;
    background-color: #FFFFFF !important;
}

/* Score badge */
.match-score {
    display: inline-block !important;
    background-color: #1F5F5B !important;
    color: #FFFFFF !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}

/* Footer */
.app-footer {
    text-align: center !important;
    padding: 16px 0 !important;
    border-top: 1px solid #D9D6CE !important;
    margin-top: 24px !important;
    font-size: 13px !important;
    color: #5B6068 !important;
}

.app-footer a {
    color: #1F5F5B !important;
    text-decoration: none !important;
}
"""
