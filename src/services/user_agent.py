from typing import Dict, List, Optional

from openai import OpenAI
from openai.types.responses import ResponseInputItemParam
from pydantic import BaseModel

from src.config import settings
from src.models.user import User


class ConversationResponse(BaseModel):
    broker_message: str
    is_complete: bool
    extracted_preferences: Optional[str] = None


class UserAgent:
    def __init__(self, user: User, openai_api_key: Optional[str] = None):
        self.user = user
        self.client = OpenAI(api_key=openai_api_key or settings.openai_api_key)
        self.conversation_history: List[Dict[str, str]] = []
        self.model = "gpt-4o-mini"
        # TODO: Support streaming responses for real-time conversation experience

    def _build_system_prompt(self) -> str:
        """Build system prompt for broker persona with user context"""
        user_context = f"""
You are an experienced real estate broker conducting an intake conversation with a new client.

CLIENT CONTEXT:
- Name: {self.user.name}
- Occupation: {self.user.occupation or "Not specified"}
- Bio: {self.user.bio or "Not specified"}

EXISTING PREFERENCES (already provided):
- Price range: ${self.user.min_price or "no min"} - ${self.user.max_price or "no max"} per {self.user.price_period.value if self.user.price_period else "month"}
- Dates: {self.user.preferred_start_date or "flexible"} to {self.user.preferred_end_date or "flexible"}
- Listing type: {self.user.preferred_listing_type.value if self.user.preferred_listing_type else "any"}

YOUR ROLE:
You are a knowledgeable broker who asks thoughtful, relevant questions to understand what this client REALLY wants beyond the basic filters. Focus on lifestyle preferences, location priorities, deal-breakers, and what would make them truly happy in their housing situation.

CONVERSATION STYLE:
- Ask ONE question at a time
- Be conversational and friendly, not formal
- Reference their background naturally when relevant
- Build on previous responses to ask smart follow-up questions
- Know when you have enough information to complete the intake

RESPONSE BEHAVIOR:
- Provide your next question or comment in the broker_message field
- Set is_complete to false while gathering information
- When you have sufficient information about their preferences, set is_complete to true and provide a comprehensive summary of their preferences in the extracted_preferences field
"""
        return user_context.strip()

    def chat(self, user_message: str) -> ConversationResponse:
        """Send a message and get broker's response"""

        system_prompt = self._build_system_prompt()
        self.conversation_history.append({"role": "user", "message": user_message})

        messages: List[ResponseInputItemParam] = [
            {"role": "system", "content": system_prompt}
        ]
        for entry in self.conversation_history:
            role = "assistant" if entry["role"] == "assistant" else "user"
            messages.append({"role": role, "content": entry["message"]})

        response = self.client.responses.parse(
            model=self.model,
            input=messages,
            text_format=ConversationResponse,
            temperature=0.7,
        )

        parsed_response = response.output_parsed
        if not parsed_response:
            raise ValueError("No parsed response from OpenAI")

        broker_message = parsed_response.broker_message
        is_complete = parsed_response.is_complete
        extracted_preferences = parsed_response.extracted_preferences

        self.conversation_history.append(
            {"role": "assistant", "message": broker_message}
        )

        return ConversationResponse(
            broker_message=broker_message,
            is_complete=is_complete,
            extracted_preferences=extracted_preferences,
        )
