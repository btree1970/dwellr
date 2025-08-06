from unittest.mock import MagicMock, patch

import pytest

from src.agents.user_agent import ConversationResponse, UserAgent
from src.models.user import User


@pytest.fixture
def sample_user():
    return User(
        name="John Doe",
        email="john@example.com",
        occupation="Software Engineer",
        bio="Looking for a quiet place to work from home",
        min_price=2000.0,
        max_price=4000.0,
    )


@pytest.fixture
def user_agent(sample_user):
    return UserAgent(sample_user, openai_api_key="test-key")


@pytest.fixture
def mock_openai_response():
    return {
        "broker_message": "Hi John! I see you're a Software Engineer. What's most important to you in your living space?",
        "is_complete": False,
        "extracted_preferences": None,
    }


class TestUserAgent:
    def test_initialization(self, sample_user):
        agent = UserAgent(sample_user, openai_api_key="test-key")

        assert agent.user == sample_user
        assert agent.conversation_history == []
        assert agent.model == "gpt-4o-mini"

    def test_build_system_prompt(self, user_agent):
        prompt = user_agent._build_system_prompt()

        assert "John Doe" in prompt
        assert "Software Engineer" in prompt
        assert "quiet place to work from home" in prompt
        assert "$2000.0" in prompt
        assert "$4000.0" in prompt
        assert "real estate broker" in prompt

    @patch("src.agents.user_agent.OpenAI")
    def test_chat_first_message(self, mock_openai, user_agent, mock_openai_response):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        user_agent.client = mock_client

        mock_response = MagicMock()
        mock_parsed = ConversationResponse(
            broker_message=mock_openai_response["broker_message"],
            is_complete=False,
            extracted_preferences=None,
        )
        mock_response.output_parsed = mock_parsed
        mock_client.responses.parse.return_value = mock_response

        result = user_agent.chat("Hi, I'm looking for help finding housing.")

        assert isinstance(result, ConversationResponse)
        assert result.broker_message == mock_openai_response["broker_message"]
        assert not result.is_complete
        assert result.extracted_preferences is None
        assert len(user_agent.conversation_history) == 2
        assert user_agent.conversation_history[0]["role"] == "user"
        assert user_agent.conversation_history[1]["role"] == "assistant"

    @patch("src.agents.user_agent.OpenAI")
    def test_chat_subsequent_message(
        self, mock_openai, user_agent, mock_openai_response
    ):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        user_agent.client = mock_client

        mock_response = MagicMock()
        mock_parsed = ConversationResponse(
            broker_message=mock_openai_response["broker_message"],
            is_complete=False,
            extracted_preferences=None,
        )
        mock_response.output_parsed = mock_parsed
        mock_client.responses.parse.return_value = mock_response

        user_response = "I need a quiet space with good internet for work"
        result = user_agent.chat(user_response)

        assert isinstance(result, ConversationResponse)
        assert result.broker_message == mock_openai_response["broker_message"]
        assert not result.is_complete
        assert result.extracted_preferences is None
        assert len(user_agent.conversation_history) == 2

    @patch("src.agents.user_agent.OpenAI")
    def test_chat_completion(self, mock_openai, user_agent):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        user_agent.client = mock_client

        completion_response = ConversationResponse(
            broker_message="Perfect! I have everything I need.",
            is_complete=True,
            extracted_preferences="Client prefers quiet environments with excellent internet connectivity for remote work.",
        )

        mock_response = MagicMock()
        mock_response.output_parsed = completion_response
        mock_client.responses.parse.return_value = mock_response

        result = user_agent.chat("That sounds great!")

        assert result.is_complete
        assert result.extracted_preferences == completion_response.extracted_preferences
