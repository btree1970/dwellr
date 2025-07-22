from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import settings
from src.models.user import User


class UserAgent:
    def __init__(self, user: User, openai_api_key: Optional[str] = None):
        self.user = user
        self.client = OpenAI(api_key=openai_api_key or settings.openai_api_key)
        self.conversation_history: List[Dict[str, str]] = []
        self.model = "gpt-4o"

        self.tools: List[Dict[str, Any]] = []
        self._register_tools()

    def _register_tools(self) -> None:
        from src.agents.tools.evaluation import EVALUATION_TOOL_DEFINITION
        from src.agents.tools.preferences import PREFERENCES_TOOL_DEFINITION
        from src.agents.tools.recommendations import RECOMMENDATIONS_TOOL_DEFINITION

        self.tools = [
            PREFERENCES_TOOL_DEFINITION,
            RECOMMENDATIONS_TOOL_DEFINITION,
            EVALUATION_TOOL_DEFINITION,
        ]

        # TODO: Implement tool function mapping for execution

    def _build_system_prompt(self) -> str:
        # TODO: Implement system prompt building
        return f"""
You are an experienced real estate agent helping {self.user.name} find housing.

USER CONTEXT:
- Name: {self.user.name}
- Occupation: {self.user.occupation or "Not specified"}
- Bio: {self.user.bio or "Not specified"}

EXISTING PREFERENCES:
- Price range: ${self.user.min_price or "no min"} - ${self.user.max_price or "no max"}
- Dates: {self.user.preferred_start_date or "flexible"} to {self.user.preferred_end_date or "flexible"}
- Listing type: {self.user.preferred_listing_type.value if self.user.preferred_listing_type else "any"}

AVAILABLE TOOLS:
TODO: List available tools and their descriptions

YOUR ROLE:
Help the user find housing through natural conversation. You can update their preferences,
get listing recommendations, and check evaluation status. Be conversational and helpful.
"""

    def chat(self, user_message: str) -> str:
        # TODO: Implement agentic chat with tool calling
        self.conversation_history.append({"role": "user", "content": user_message})

        # TODO: Implement OpenAI function calling
        # TODO: Execute tool calls
        # TODO: Handle tool responses
        # TODO: Return final agent response

        # Placeholder response
        return "TODO: Implement agentic chat with tool calling"

    def _execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        # TODO: Implement tool execution
        # TODO: Route to tool implementations
        return {"error": "Tool execution not implemented"}

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return self.conversation_history.copy()

    def reset_conversation(self) -> None:
        # TODO: Consider if we need to preserve any context
        self.conversation_history = []
