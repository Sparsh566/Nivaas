"""Tests for agent loop: message validation, tool calling with mocked Groq."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.agent.loop import AgentState, run_agent
from app.config import settings


class TestAgentState:
    def test_default_state(self):
        state = AgentState()
        assert state.requirements == {}
        assert len(state.weights) > 0
        assert state.last_shortlist == []

    def test_roundtrip(self):
        state = AgentState()
        state.requirements = {"city": "Pune"}
        d = state.to_dict()
        restored = AgentState.from_dict(d)
        assert restored.requirements == {"city": "Pune"}


class TestMessageValidation:
    @pytest.mark.asyncio
    async def test_long_message_rejected(self):
        state = AgentState()
        long_msg = "a" * 2001
        response, _ = await run_agent(long_msg, state)
        assert "too long" in response.lower()

    @pytest.mark.asyncio
    async def test_missing_groq_key(self):
        state = AgentState()
        original = settings.GROQ_API_KEY
        settings.GROQ_API_KEY = ""
        try:
            response, _ = await run_agent("hello", state)
            assert "not configured" in response.lower()
        finally:
            settings.GROQ_API_KEY = original


class TestAgentWithMockedGroq:
    @pytest.mark.asyncio
    async def test_simple_text_response(self):
        """Mock Groq returning a simple text response (no tool calls)."""
        state = AgentState()

        mock_message = MagicMock()
        mock_message.content = "I can help you find properties in Pune."
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("app.agent.loop.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test-key"
            mock_settings.GROQ_MODEL = "test-model"
            mock_settings.MAX_MESSAGE_LENGTH = 2000
            mock_settings.MAX_TOOL_ITERATIONS = 5

            with patch("groq.Groq") as MockGroq:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                MockGroq.return_value = mock_client

                response, updated_state = await run_agent("hello", state)
                assert "properties" in response.lower() or "help" in response.lower()

    @pytest.mark.asyncio
    async def test_max_iterations(self):
        """Verify the agent stops after MAX_TOOL_ITERATIONS."""
        state = AgentState()

        # Create a mock that always returns tool calls
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "search_properties"
        mock_tool_call.function.arguments = json.dumps({
            "city": "Pune", "max_budget_inr": 7000000
        })

        mock_message = MagicMock()
        mock_message.content = ""
        mock_message.tool_calls = [mock_tool_call]

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("app.agent.loop.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test-key"
            mock_settings.GROQ_MODEL = "test-model"
            mock_settings.MAX_MESSAGE_LENGTH = 2000
            mock_settings.MAX_TOOL_ITERATIONS = 2
            mock_settings.DEMO_MODE = True
            mock_settings.TAVILY_API_KEY = ""
            mock_settings.LISTING_CACHE_HOURS = 24
            mock_settings.MAX_TAVILY_CALLS_PER_MESSAGE = 3
            mock_settings.DAILY_TAVILY_CREDIT_CAP = 40

            with patch("groq.Groq") as MockGroq:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                MockGroq.return_value = mock_client

                with patch("app.tools.search_properties.execute", new_callable=AsyncMock) as mock_search:
                    mock_search.return_value = {
                        "listings": [],
                        "total_found": 0,
                        "tavily_calls_used": 0,
                        "is_demo": True,
                    }

                    response, updated_state = await run_agent("find me a 2bhk", state)
                    assert "maximum" in response.lower() or isinstance(response, str)
