"""Agent loop: Groq chat completion with tool calling, capped at 5 iterations."""

import json
import logging
from typing import Optional
from pydantic import ValidationError

from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.tools.registry import TOOL_SCHEMAS, ALLOWED_TOOLS, TOOL_ARG_MODELS
from app.tools import search_properties, get_property_details, compare_properties
from app.tools import search_locality, calculate_emi, update_preferences
from app.ranking.weights import get_default_weights
from app.ranking.scorer import score_listings

logger = logging.getLogger(__name__)


class AgentState:
    """Per-session state for the agent."""

    def __init__(self) -> None:
        self.requirements: dict = {}
        self.weights: dict[str, float] = get_default_weights()
        self.last_shortlist: list[dict] = []
        self.conversation_history: list[dict] = []
        self.agent_steps: list[dict] = []
        self.tavily_calls_this_message: int = 0
        self.is_demo: bool = False

    def to_dict(self) -> dict:
        return {
            "requirements": self.requirements,
            "weights": self.weights,
            "last_shortlist": self.last_shortlist,
            "conversation_history": self.conversation_history,
            "agent_steps": self.agent_steps,
            "is_demo": self.is_demo,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        state = cls()
        if data:
            state.requirements = data.get("requirements", {})
            state.weights = data.get("weights", get_default_weights())
            state.last_shortlist = data.get("last_shortlist", [])
            state.conversation_history = data.get("conversation_history", [])
            state.agent_steps = data.get("agent_steps", [])
            state.is_demo = data.get("is_demo", False)
        return state


async def run_agent(
    user_message: str,
    state: AgentState,
) -> tuple[str, AgentState]:
    """Run the agent loop for a single user message.

    Returns (assistant_response, updated_state).
    """
    # Validate message length
    if len(user_message) > settings.MAX_MESSAGE_LENGTH:
        return (
            f"Message is too long ({len(user_message)} characters). "
            f"Please keep messages under {settings.MAX_MESSAGE_LENGTH} characters.",
            state,
        )

    # Check Groq availability
    if not settings.GROQ_API_KEY:
        return (
            "The language model is not configured. Set GROQ_API_KEY in the environment to enable the assistant.",
            state,
        )

    state.agent_steps = []
    state.tavily_calls_this_message = 0

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add recent conversation history (last 10 exchanges)
    recent_history = state.conversation_history[-20:]
    messages.extend(recent_history)

    messages.append({"role": "user", "content": user_message})

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
    except Exception as e:
        logger.error("Failed to initialize Groq client: %s", str(e))
        return ("The language model service is temporarily unavailable. Please try again.", state)

    # Tool calling loop (max 5 iterations)
    for iteration in range(settings.MAX_TOOL_ITERATIONS):
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=4000,
            )
        except Exception as e:
            error_msg = str(e)
            logger.error("Groq API error: %s", error_msg)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                return ("The service is currently busy. Please wait a moment and try again.", state)
            if "auth" in error_msg.lower() or "401" in error_msg:
                return ("Authentication error with the language model. Please check the API key.", state)
            return ("The language model service encountered an error. Please try again.", state)

        choice = response.choices[0]
        message = choice.message

        # If no tool calls, we have the final response
        if not message.tool_calls:
            assistant_text = message.content or "I could not generate a response. Please try rephrasing your question."
            break
        else:
            # Process tool calls
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments

                step = {
                    "tool": tool_name,
                    "arguments": {},
                    "result_summary": "",
                }

                # Whitelist check
                if tool_name not in ALLOWED_TOOLS:
                    step["result_summary"] = f"Unknown tool: {tool_name}"
                    state.agent_steps.append(step)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                    })
                    continue

                # Parse and validate arguments
                try:
                    args_dict = json.loads(tool_args_str)
                    step["arguments"] = args_dict
                except json.JSONDecodeError:
                    step["result_summary"] = "Invalid JSON arguments"
                    state.agent_steps.append(step)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"error": "Invalid tool arguments"}),
                    })
                    continue

                arg_model = TOOL_ARG_MODELS.get(tool_name)
                if arg_model:
                    try:
                        validated_args = arg_model(**args_dict)
                    except ValidationError as e:
                        step["result_summary"] = f"Validation error: {str(e)}"
                        state.agent_steps.append(step)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({"error": f"Invalid arguments: {str(e)}"}),
                        })
                        continue
                else:
                    validated_args = args_dict

                # Execute tool
                try:
                    tool_result = await _execute_tool(
                        tool_name, validated_args, state
                    )
                    step["result_summary"] = _summarize_result(tool_name, tool_result)
                    state.agent_steps.append(step)
                except Exception as e:
                    logger.error("Tool execution failed: %s - %s", tool_name, str(e))
                    step["result_summary"] = f"Tool error: {str(e)}"
                    state.agent_steps.append(step)
                    tool_result = {"error": "Tool execution failed. Please try again."}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, default=str),
                })
    else:
        # Max iterations reached
        assistant_text = "I reached the maximum number of steps. Here is what I found so far."
        if state.last_shortlist:
            assistant_text += f" I found {len(state.last_shortlist)} listings."

    # Store conversation
    state.conversation_history.append({"role": "user", "content": user_message})
    state.conversation_history.append({"role": "assistant", "content": assistant_text})

    # Keep conversation history manageable
    if len(state.conversation_history) > 30:
        state.conversation_history = state.conversation_history[-20:]

    return assistant_text, state


async def _execute_tool(
    tool_name: str,
    args: object,
    state: AgentState,
) -> dict:
    """Execute a tool and update state as needed."""

    if tool_name == "search_properties":
        # Update requirements from search args
        req = {
            "city": args.city,
            "locality": args.locality,
            "max_budget_inr": args.max_budget_inr,
            "bhk": args.bhk,
            "property_type": args.property_type,
        }
        state.requirements.update({k: v for k, v in req.items() if v is not None})

        result = await search_properties.execute(
            args=args,
            requirements=state.requirements,
            weights=state.weights,
            tavily_calls_this_message=state.tavily_calls_this_message,
        )
        state.tavily_calls_this_message += result.get("tavily_calls_used", 0)
        state.last_shortlist = result.get("listings", [])
        state.is_demo = result.get("is_demo", False)
        return result

    elif tool_name == "get_property_details":
        return await get_property_details.execute(args)

    elif tool_name == "compare_properties":
        return await compare_properties.execute(args)

    elif tool_name == "search_locality_information":
        result = await search_locality.execute(args)
        state.tavily_calls_this_message += 1
        return result

    elif tool_name == "calculate_emi":
        return await calculate_emi.execute(args)

    elif tool_name == "update_preferences":
        result = await update_preferences.execute(args, state.weights)
        state.weights = result.get("weights", state.weights)

        # Re-rank last shortlist with new weights
        if state.last_shortlist:
            from app.ranking.scorer import score_listings
            state.last_shortlist = score_listings(
                state.last_shortlist, state.requirements, state.weights
            )
            result["re_ranked_listings"] = state.last_shortlist
            result["message"] += f" Re-ranked {len(state.last_shortlist)} listings with new weights."

        return result

    return {"error": f"Tool {tool_name} not implemented"}


def _summarize_result(tool_name: str, result: dict) -> str:
    """Create a brief summary of a tool result for the agent steps panel."""
    if "error" in result:
        return f"Error: {result['error']}"

    if tool_name == "search_properties":
        n = result.get("total_found", 0)
        src = result.get("source", "web")
        return f"Found {n} listings (from {src})"

    if tool_name == "get_property_details":
        return f"Details for {result.get('title', 'listing')}"

    if tool_name == "compare_properties":
        n = len(result.get("listings", []))
        return f"Compared {n} listings"

    if tool_name == "search_locality_information":
        topics = result.get("info", {}).get("topics_found", [])
        return f"Locality info: {', '.join(topics) if topics else 'general info'}"

    if tool_name == "calculate_emi":
        emi = result.get("emi_formatted", "")
        return f"EMI: {emi}/month"

    if tool_name == "update_preferences":
        return result.get("message", "Preferences updated")

    return "Completed"
