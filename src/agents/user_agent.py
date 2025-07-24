import json
from typing import Any, Dict, List, Optional, cast

from openai import OpenAI
from openai.types.responses import FunctionToolParam, ResponseFunctionToolCall
from sqlalchemy.orm import Session

from src.agents.tools.preferences import (
    PREFERENCES_TOOL_DEFINITION,
    update_user_preferences,
)
from src.agents.tools.recommendations import (
    RECOMMENDATIONS_TOOL_DEFINITION,
    get_listing_recommendations,
)
from src.config import settings
from src.models.user import User


class UserAgent:
    def __init__(self, user: User, db: Session, openai_api_key: Optional[str] = None):
        self.db = db
        self.user = user
        self.client = OpenAI(api_key=openai_api_key or settings.openai_api_key)
        self.conversation_history: List[Dict[str, str]] = []
        self.model = "gpt-4o"

        self.tools: List[FunctionToolParam] = []
        self._register_tools()

        # Tool function mapping for cleaner execution
        self.tool_functions = {
            PREFERENCES_TOOL_DEFINITION.name: update_user_preferences,
            RECOMMENDATIONS_TOOL_DEFINITION.name: get_listing_recommendations,
        }

    def _register_tools(self) -> None:
        self.tools = [
            PREFERENCES_TOOL_DEFINITION,
            RECOMMENDATIONS_TOOL_DEFINITION,
        ]

    def _build_system_prompt(self) -> str:
        return f"""
You are an experienced real estate agent helping {self.user.name} find housing.

USER CONTEXT:
- Name: {self.user.name}
- Occupation: {self.user.occupation or "Not specified"}
- Bio: {self.user.bio or "Not specified"}

EXISTING PREFERENCES:
- Price range: ${self.user.min_price or "no min"} - ${self.user.max_price or "no max"}
- Price period: ${self.user.price_period}
- Dates: {self.user.preferred_start_date or "flexible"} to {self.user.preferred_end_date or "flexible"}
- Flexibility: ±{self.user.date_flexibility_days}
- Listing type: {self.user.preferred_listing_type.value if self.user.preferred_listing_type else "any"}
- Preference Profile: {self.user.preference_profile if self.user.preference_profile else "N/A"}

YOUR ROLE:
Help the user find housing through natural conversation. You can update their preferences,
get listing recommendations, and check evaluation status. Be conversational and helpful.
"""

    def chat(self, user_message: str) -> str:
        try:
            system_prompt = self._build_system_prompt()

            # Add user message to history
            self.conversation_history.append({"role": "user", "content": user_message})

            # Build full message context
            messages = [
                {"role": "system", "content": system_prompt}
            ] + self.conversation_history

            response = self.client.responses.create(
                model=self.model,
                input=messages,
                tools=self.tools,
            )
        except Exception as e:
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}"

        # Add response outputs to history
        for output in response.output:
            self.conversation_history.append(output)

        message = response.output[0]

        if message.type == "function_call":
            tool_calls = cast(List[ResponseFunctionToolCall], response.output)
            for tool_call in tool_calls:
                tool_call_result = self._execute_tool(
                    tool_name=tool_call.name, output=tool_call
                )
                self.conversation_history.append(tool_call_result)

            try:
                # Rebuild full message context with tool results
                messages = [
                    {"role": "system", "content": system_prompt}
                ] + self.conversation_history

                response = self.client.responses.create(
                    model=self.model,
                    input=messages,
                    tools=self.tools,
                )
                self.conversation_history.append(response.output[0])
            except Exception as e:
                return f"I encountered an error while processing tool results: {str(e)}"

        # Extract the final assistant response
        final_message = self.conversation_history[-1]
        return final_message.content

    def _execute_tool(
        self, tool_name: str, output: ResponseFunctionToolCall
    ) -> Dict[str, Any]:
        try:
            args = json.loads(output.arguments)

            if tool_name not in self.tool_functions:
                return {
                    "call_id": output.call_id,
                    "output": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                    "type": "function_call_output",
                }

            tool_function = self.tool_functions[tool_name]
            tool_response = tool_function(user=self.user, db=self.db, **args)

            return {
                "call_id": output.call_id,
                "output": json.dumps(tool_response),
                "type": "function_call_output",
            }

        except json.JSONDecodeError as e:
            return {
                "call_id": output.call_id,
                "output": json.dumps({"error": f"Invalid tool arguments: {str(e)}"}),
                "type": "function_call_output",
            }
        except Exception as e:
            return {
                "call_id": output.call_id,
                "output": json.dumps({"error": f"Tool execution failed: {str(e)}"}),
                "type": "function_call_output",
            }

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return self.conversation_history.copy()

    def reset_conversation(self) -> None:
        self.conversation_history = []
