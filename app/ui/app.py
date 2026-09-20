"""Gradio Blocks application for Nivaas."""

import asyncio
import gradio as gr
from app.config import settings, DEFAULT_WEIGHTS, WEIGHT_LABELS
from app.ui.theme import NivaasTheme
from app.ui.css import CUSTOM_CSS
from app.ui.components import (
    render_shortlist,
    render_comparison_table,
    render_emi_result,
    render_agent_steps,
    render_requirements_panel,
    render_how_matching_works,
)
from app.agent.loop import AgentState, run_agent
from app.ranking.emi import calculate_emi
from app.ranking.parsers import format_indian_number


HEAD_HTML = f"""
<title>{settings.APP_NAME}: Find a property by describing what you need</title>
<meta name="description" content="{settings.APP_NAME} helps you search for properties in Indian cities by describing your requirements in plain language. Compare listings and estimate EMI.">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="icon" type="image/x-icon" href="/static/favicon.ico">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
"""


def create_gradio_app() -> gr.Blocks:
    """Create and return the Gradio Blocks application."""

    with gr.Blocks(
        theme=NivaasTheme(),
        css=CUSTOM_CSS,
        head=HEAD_HTML,
        title=f"{settings.APP_NAME}",
    ) as demo:

        # State
        agent_state = gr.State(value=AgentState().to_dict())

        # Header
        gr.Markdown(
            f"## {settings.APP_NAME}\n"
            "Find a property by describing what you need."
        )
        gr.Markdown(
            "Search by city, locality, budget, BHK, area, amenities, and connectivity. "
            "See how each match was scored, then check the EMI.",
            elem_classes=["muted"],
        )

        # Demo mode banner
        if settings.DEMO_MODE:
            gr.Markdown(
                "Demo mode: these are sample listings, not live.",
                elem_classes=["demo-banner"],
            )

        with gr.Row():
            # Left column: Chat
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    label="Chat",
                    show_label=False,
                    height=460,
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Describe the property you're looking for...",
                        show_label=False,
                        max_lines=3,
                        scale=4,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

                gr.Examples(
                    examples=[
                        "2BHK in Hinjewadi Pune under 70 lakh, near IT parks",
                        "3BHK flat in Baner Pune under 1.2 crore with parking",
                        "1BHK in Wakad Pune under 45 lakh, semi-furnished",
                    ],
                    inputs=msg_input,
                    label="Try these queries",
                )

                # Requirements panel
                with gr.Accordion("Understood requirements", open=False):
                    requirements_panel = gr.HTML(
                        value="<div style='font-size:13px;color:#5B6068;'>No search requirements yet.</div>"
                    )
                    reset_btn = gr.Button("Reset", variant="secondary", size="sm")

                # Agent steps
                with gr.Accordion("Agent steps", open=False):
                    steps_panel = gr.HTML(
                        value="<div style='font-size:13px;color:#5B6068;'>No tool calls made yet.</div>"
                    )

                gr.Markdown(
                    "Answers are generated from listings found on the web. Check details with the source before acting.",
                    elem_classes=["disclaimer"],
                )

            # Right column: Results tabs
            with gr.Column(scale=1):
                with gr.Tabs():
                    with gr.Tab("Shortlist"):
                        shortlist_panel = gr.HTML(
                            value="<div style='padding:24px;text-align:center;color:#5B6068;'>No listings found yet. Try searching for a property.</div>"
                        )

                    with gr.Tab("Compare"):
                        gr.Markdown(
                            "Enter 2 or 3 listing IDs (from the shortlist) separated by commas to compare.",
                            elem_classes=["muted"],
                        )
                        compare_input = gr.Textbox(
                            placeholder="Enter listing IDs, e.g.: id1, id2",
                            show_label=False,
                        )
                        compare_btn = gr.Button("Compare", variant="primary")
                        compare_panel = gr.HTML(
                            value="<div style='padding:24px;color:#5B6068;'>Select listings to compare.</div>"
                        )

                    with gr.Tab("EMI Calculator"):
                        with gr.Row():
                            emi_price = gr.Number(label="Property price (INR)", value=7000000)
                            emi_dp = gr.Number(label="Down payment (%)", value=20)
                        with gr.Row():
                            emi_rate = gr.Number(label="Interest rate (%)", value=8.5)
                            emi_tenure = gr.Number(label="Tenure (years)", value=20)
                        emi_income = gr.Number(label="Monthly income (INR, optional)", value=0)
                        emi_btn = gr.Button("Calculate EMI", variant="primary")
                        emi_panel = gr.HTML(
                            value="<div style='padding:12px;color:#5B6068;'>Enter values and click Calculate.</div>"
                        )

                    with gr.Tab("How Matching Works"):
                        matching_info = gr.HTML(value=render_how_matching_works())

        # Footer
        footer_links = f'<a href="/terms">Terms</a> | <a href="/privacy">Privacy</a>'
        if settings.CONTACT_EMAIL:
            footer_links += f' | <a href="mailto:{settings.CONTACT_EMAIL}">{settings.CONTACT_EMAIL}</a>'
        gr.HTML(
            f"""<div class='app-footer'>
                {settings.APP_NAME} | {footer_links}<br/>
                Listings are read from public web pages and may be outdated. Not financial or legal advice.
            </div>"""
        )

        # Event handlers
        async def handle_message(message, history, state_dict):
            state = AgentState.from_dict(state_dict)
            if not message or not message.strip():
                yield (
                    history or [],
                    state_dict,
                    render_shortlist(state.last_shortlist, state.is_demo),
                    render_requirements_panel(state.requirements, state.weights),
                    render_agent_steps(state.agent_steps),
                    "",
                )
                return

            # Add user message to chat
            history = history or []
            history.append({"role": "user", "content": message})

            # Show loading state
            yield (
                history + [{"role": "assistant", "content": "Searching..."}],
                state_dict,
                render_shortlist(state.last_shortlist, state.is_demo),
                render_requirements_panel(state.requirements, state.weights),
                render_agent_steps(state.agent_steps),
                "",
            )

            # Run agent
            response, state = await run_agent(message, state)

            # Update history
            history.append({"role": "assistant", "content": response})

            # Update state dict
            new_state_dict = state.to_dict()

            yield (
                history,
                new_state_dict,
                render_shortlist(state.last_shortlist, state.is_demo),
                render_requirements_panel(state.requirements, state.weights),
                render_agent_steps(state.agent_steps),
                "",
            )

        send_btn.click(
            fn=handle_message,
            inputs=[msg_input, chatbot, agent_state],
            outputs=[chatbot, agent_state, shortlist_panel, requirements_panel, steps_panel, msg_input],
        )

        msg_input.submit(
            fn=handle_message,
            inputs=[msg_input, chatbot, agent_state],
            outputs=[chatbot, agent_state, shortlist_panel, requirements_panel, steps_panel, msg_input],
        )

        # Reset handler
        def handle_reset():
            new_state = AgentState()
            return (
                [],
                new_state.to_dict(),
                render_shortlist([], False),
                render_requirements_panel({}, new_state.weights),
                render_agent_steps([]),
            )

        reset_btn.click(
            fn=handle_reset,
            inputs=[],
            outputs=[chatbot, agent_state, shortlist_panel, requirements_panel, steps_panel],
        )

        # Compare handler
        async def handle_compare(ids_str, state_dict):
            if not ids_str or not ids_str.strip():
                return "<div style='padding:12px;color:#5B6068;'>Enter listing IDs to compare.</div>"

            ids = [i.strip() for i in ids_str.split(",") if i.strip()]
            if len(ids) < 2 or len(ids) > 3:
                return "<div style='padding:12px;color:#c0392b;'>Enter 2 or 3 listing IDs.</div>"

            # Look up from last shortlist in state
            state = AgentState.from_dict(state_dict)
            listings = [l for l in state.last_shortlist if l.get("id") in ids]

            if len(listings) < 2:
                # Try database lookup
                from app.tools.compare_properties import ComparePropertiesArgs, execute
                try:
                    args = ComparePropertiesArgs(listing_ids=ids)
                    result = await execute(args)
                    if "error" in result:
                        return f"<div style='padding:12px;color:#c0392b;'>{result['error']}</div>"
                    return render_comparison_table(result["listings"], result.get("tradeoffs", []))
                except Exception as e:
                    return f"<div style='padding:12px;color:#c0392b;'>Could not compare: {str(e)}</div>"

            # Generate trade-offs
            from app.tools.compare_properties import _generate_tradeoffs
            tradeoffs = _generate_tradeoffs(listings)
            return render_comparison_table(listings, tradeoffs)

        compare_btn.click(
            fn=handle_compare,
            inputs=[compare_input, agent_state],
            outputs=[compare_panel],
        )

        # EMI handler
        def handle_emi(price, dp_pct, rate, tenure, income):
            try:
                price = int(price) if price else 0
                dp_pct = float(dp_pct) if dp_pct else 20
                rate = float(rate) if rate else 8.5
                tenure = int(tenure) if tenure else 20
                income = int(income) if income and income > 0 else None

                if price <= 0:
                    return "<div style='padding:12px;color:#c0392b;'>Enter a valid property price.</div>"
                if tenure <= 0:
                    return "<div style='padding:12px;color:#c0392b;'>Enter a valid tenure.</div>"
                if dp_pct < 0 or dp_pct >= 100:
                    return "<div style='padding:12px;color:#c0392b;'>Down payment must be between 0% and 99%.</div>"

                result = calculate_emi(price, dp_pct, rate, tenure, income)
                return render_emi_result({
                    "loan_amount_formatted": format_indian_number(result.loan_amount),
                    "emi_formatted": format_indian_number(result.emi),
                    "total_interest_formatted": format_indian_number(result.total_interest),
                    "total_payable_formatted": format_indian_number(result.total_payable),
                    "emi_to_income_pct": result.emi_to_income_pct,
                    "income_warning": result.income_warning,
                    "income_note": (
                        f"EMI is {result.emi_to_income_pct}% of your monthly income. "
                        "Generally, keeping EMI below 40% of income is considered manageable."
                    ) if result.income_warning else None,
                })
            except ValueError as e:
                return f"<div style='padding:12px;color:#c0392b;'>{str(e)}</div>"
            except Exception:
                return "<div style='padding:12px;color:#c0392b;'>Could not calculate EMI. Check your inputs.</div>"

        emi_btn.click(
            fn=handle_emi,
            inputs=[emi_price, emi_dp, emi_rate, emi_tenure, emi_income],
            outputs=[emi_panel],
        )

    return demo
