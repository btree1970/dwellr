import logging
import uuid
from typing import AsyncGenerator, List, Optional

import logfire
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
)
from pydantic_ai.tools import ToolFuncEither
from sqlalchemy.orm.session import Session

from src.agents.deps import UserAgentDependencies
from src.agents.message_formatter import ChatMessage, MessageHistoryFormatter
from src.agents.stream_events import (
    TextChunkEvent,
    TextStartEvent,
    ToolCallEvent,
    UserAgentStreamEvent,
)
from src.agents.tools import tools
from src.models.user import User
from src.models.user_session import UserSession

logger = logging.getLogger(__name__)

logfire.configure()
logfire.instrument_pydantic_ai()


class UserAgent:
    is_new_session: bool

    _db_session: Session
    _user_session_id: str
    _user: User
    _agent_deps: UserAgentDependencies
    _agent: Agent[UserAgentDependencies]
    _message_history: list[ModelMessage]
    _tools: list[ToolFuncEither[UserAgentDependencies]]

    def __init__(self, db_session: Session, user: User):
        self._model = "openai:gpt-4o"
        self._user = user
        self._db_session = db_session
        self._agent_deps = UserAgentDependencies(db=db_session, user=user)
        self.is_new_session = False

        self._load_or_create_session()

        self._tools = tools
        self._agent = Agent(
            model=self._model, deps_type=UserAgentDependencies, tools=self._tools
        )
        self._set_system_prompt(self._agent)

    def _load_or_create_session(self):
        """Load existing session or create new one for user"""
        user_session = (
            self._db_session.query(UserSession).filter_by(user_id=self._user.id).first()
        )

        if user_session and user_session.session_id:
            self._user_session_id = user_session.session_id
            self.is_new_session = False
            try:
                history_data = user_session.get_message_history()
                self._message_history = ModelMessagesTypeAdapter.validate_python(
                    history_data
                )
                logger.info(
                    f"Loaded existing session {self._user_session_id} with {len(self._message_history)} messages"
                )

            except Exception as e:
                logger.error(
                    f"Failed to load message history for user {self._user.id}: {e}"
                )
                # If we can't load history, treat as new session
                # Overwriting existing session.
                self._create_new_session()
        else:
            self._create_new_session()

    def _create_new_session(self):
        self._user_session_id = str(uuid.uuid4())
        self._message_history = []
        self.is_new_session = True

        user_session = (
            self._db_session.query(UserSession).filter_by(user_id=self._user.id).first()
        )

        if user_session:
            user_session.session_id = self._user_session_id
            user_session.set_message_history([])
        else:
            user_session = UserSession(
                user_id=self._user.id,
                session_id=self._user_session_id,
            )
            user_session.set_message_history([])
            self._db_session.add(user_session)

        try:
            self._db_session.commit()
            logger.info(
                f"Created new session {self._user_session_id} for user {self._user.id}"
            )
        except Exception as e:
            self._db_session.rollback()
            logger.error(f"Failed to create session: {e}")
            raise e

    async def chat(
        self, user_prompt: Optional[str] = None
    ) -> AsyncGenerator[UserAgentStreamEvent, None]:
        """
        Chat with the agent. For new sessions, agent will initiate if no prompt provided.
        For existing sessions, user_prompt is required.
        Yields streaming responses from the agent.
        """

        # Determine if we need to start the conversation
        should_agent_initiate = self.is_new_session and (
            not user_prompt or not user_prompt.strip()
        )

        # For existing sessions, require user input
        if not self.is_new_session and (not user_prompt or not user_prompt.strip()):
            raise ValueError("User prompt required for existing conversations")

        # If agent should initiate the conversation run
        # the agent with empty prompt so the agent can start
        # the conversation
        prompt_to_use = "" if should_agent_initiate else user_prompt

        try:
            async with self._agent.iter(
                prompt_to_use,
                deps=self._agent_deps,
                message_history=self._message_history,
            ) as agent_run:
                async for node in agent_run:
                    if Agent.is_model_request_node(node):
                        async with node.stream(agent_run.ctx) as handle_stream:
                            async for event in handle_stream:
                                if isinstance(event, PartStartEvent):
                                    if isinstance(event.part, TextPart):
                                        # Text response starting
                                        yield TextStartEvent(content=event.part.content)
                                    elif isinstance(event.part, ToolCallPart):
                                        # Tool call starting
                                        yield ToolCallEvent(
                                            tool_name=event.part.tool_name
                                        )

                                elif isinstance(event, PartDeltaEvent):
                                    if isinstance(event.delta, TextPartDelta):
                                        yield TextChunkEvent(
                                            content=event.delta.content_delta
                                        )
                                    # Skip ToolCallPartDelta - we don't expose args

                if agent_run.result:
                    self._message_history = agent_run.result.all_messages()
                    self._save_message_history()

                if self.is_new_session:
                    self.is_new_session = False

        except Exception as e:
            logger.error(f"Error during chat: {e}")
            raise

    def get_message_history(self) -> List[ChatMessage]:
        """Get formatted message history as ChatMessage objects."""
        formatter = MessageHistoryFormatter(truncate_content=200, truncate_args=100)
        return formatter.format_history(self._message_history)

    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self._user_session_id

    def _save_message_history(self):
        """Save current message history to database"""
        try:
            user_session = (
                self._db_session.query(UserSession)
                .filter_by(user_id=self._user.id)
                .first()
            )

            if user_session:
                user_session.set_message_history(self._message_history)
                self._db_session.commit()
                logger.debug(
                    f"Saved {len(self._message_history)} messages to session {self._user_session_id}"
                )
            else:
                logger.error(
                    f"No user session found to save history for user {self._user.id}"
                )

        except Exception as e:
            self._db_session.rollback()
            logger.error(f"Failed to save message history: {e}")
            raise

    def _set_system_prompt(self, user_agent: Agent[UserAgentDependencies]):
        def system_prompt(ctx: RunContext[UserAgentDependencies]) -> str:
            return f"""
        You are an experienced real estate agent helping {ctx.deps.user.name} find their ideal housing. Your goal is to build a comprehensive, nuanced user profile that captures not just preferences, but also flexibility levels and dealbreakers.

        USER CONTEXT:
        - Name: {ctx.deps.user.name}
        - Occupation: {ctx.deps.user.occupation or "not specified"}
        - Bio: {ctx.deps.user.bio or "not specified"}

        EXISTING PREFERENCES:
        - Price range: ${ctx.deps.user.min_price or "no min"} - ${ctx.deps.user.max_price or "no max"}
        - Price period: {ctx.deps.user.price_period}
        - Dates: {ctx.deps.user.preferred_start_date or "flexible"} to {ctx.deps.user.preferred_end_date or "flexible"}
        - Date flexibility: ±{ctx.deps.user.date_flexibility_days} days
        - Listing type: {ctx.deps.user.preferred_listing_type.value if ctx.deps.user.preferred_listing_type else "any"}
        - Current preference profile: {ctx.deps.user.preference_profile if ctx.deps.user.preference_profile else "No detailed preferences captured yet"}

        PREFERENCE CAPTURE FRAMEWORK:
        For each preference area, determine:
        1. **Dealbreakers** (absolute requirements - non-negotiable)
        2. **Strong preferences** (important but some flexibility possible)
        3. **Nice-to-haves** (would be great but not essential)
        4. **Flexibility level** (rigid/somewhat flexible/very flexible)

        KEY AREAS TO EXPLORE SYSTEMATICALLY:

        **LOCATION & NEIGHBORHOOD:**
        - Specific neighborhoods/areas (probe: dealbreaker vs preference?)
        - Proximity requirements (work, friends, amenities, transit)
        - Neighborhood vibe (quiet/busy, residential/mixed-use, etc.)
        - Safety requirements and comfort levels

        **PROPERTY CHARACTERISTICS:**
        - Size requirements (bedrooms, bathrooms, square footage)
        - Building type preferences (apartment, house, condo, etc.)
        - Floor preferences, outdoor space needs
        - Parking requirements (street vs garage vs none)
        - Pet accommodation if applicable

        **LIFESTYLE & WORK PATTERNS:**
        - Work location and commute preferences/requirements
        - Work from home needs (office space, internet, noise levels)
        - Social patterns (hosting, entertaining, privacy needs)
        - Daily routines that impact housing needs

        **BUDGET & FINANCIAL:**
        - Absolute maximum budget (true dealbreaker)
        - Comfort range vs stretch range
        - Flexibility on price for the right place
        - Additional costs tolerance (utilities, parking, etc.)

        **TIMELINE & FLEXIBILITY:**
        - Must-move-by dates vs preferred dates
        - How much lead time needed for decisions
        - Seasonal preferences or constraints

        CONVERSATION GUIDELINES:
        - Ask follow-up questions to clarify specificity: "When you mention [specific area], is that a must-have or would you consider similar neighborhoods?"
        - Probe for underlying reasons: "What draws you to that area?" or "What would make you rule out a place?"
        - Validate captured information: "So it sounds like [X] is non-negotiable, but you're flexible on [Y] - is that right?"
        - Build on existing information rather than starting over
        - Use natural conversation flow while being thorough

        COMPLETION CRITERIA:
        Consider the profile complete when you have captured:
        ✓ Clear dealbreakers vs preferences for location
        ✓ Non-negotiable property requirements vs nice-to-haves
        ✓ Budget constraints (absolute max vs comfort range)
        ✓ Timeline requirements and flexibility levels
        ✓ Key lifestyle factors that impact housing choice
        ✓ Enough detail for another AI agent to make targeted recommendations

        Only say "done" when you have a rich, nuanced profile that goes beyond basic criteria to capture the user's flexibility levels and underlying motivations for their housing preferences.

        """

        user_agent.system_prompt(system_prompt)
