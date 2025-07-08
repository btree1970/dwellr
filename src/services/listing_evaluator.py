from typing import Dict, Any, Optional, cast
from dataclasses import dataclass
from datetime import datetime
import time

from openai import OpenAI
from pydantic import BaseModel, Field
from src.models.user import User
from src.models.listing import Listing
from src.config import settings


class EvaluationResponse(BaseModel):
    score: int = Field(
        ge=1, le=10, 
        description="Rating from 1-10 where 1=poor match, 10=excellent match"
    )
    reasoning: str = Field(
        min_length=20, max_length=200,
        description="Brief explanation of the score focusing on key factors"
    )


@dataclass
class EvaluationResult:
    score: int  # 1-10 rating
    reasoning: str  # Brief explanation
    user_id: str
    listing_id: str
    
    # Cost tracking
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    evaluation_time_ms: int
    model_used: str
    evaluated_at: datetime


class ListingEvaluator:
    """Service for evaluating listings against user preferences using LLM"""
    
    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """Initialize the listing evaluator
        
        Args:
            openai_api_key: OpenAI API key (defaults to settings)
            model: Model to use for evaluation (default: gpt-4o-mini for cost efficiency)
        """
        api_key = openai_api_key or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key must be provided via parameter or settings")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        self.token_costs = {
            "gpt-4o-mini": {
                "input": 0.000150 / 1000,   # $0.150 per 1M input tokens
                "output": 0.000600 / 1000   # $0.600 per 1M output tokens
            },
            "gpt-4.1-mini":  {
                "input": 0.000400 / 1000, # $0.400 per 1M input tokens
                "output": 0.001600 / 1000  # $1.600 per 1M output tokens

            }
        }
    
    def evaluate_listing(self, user: User, listing: Listing) -> EvaluationResult:
        """Evaluate a listing against user preferences
        
        Args:
            user: User with preferences
            listing: Listing to evaluate
            
        Returns:
            EvaluationResult with score, reasoning, and cost data
        """
        start_time = time.time()
        
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(user, listing)
        
        # Call OpenAI API with structured output
        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful apartment hunting assistant. Evaluate listings based on user preferences."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=200, 
            temperature=0.3, 
            response_format=EvaluationResponse
        )
        
        end_time = time.time()
        evaluation_time_ms = int((end_time - start_time) * 1000)


        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        cost_usd = 0.0
        
        evaluation_response =  response.choices[0].message.parsed
        if evaluation_response:
            score = evaluation_response.score
            reasoning = evaluation_response.reasoning
        else:
            raise ValueError("Expected a valid EvaluationResponse from LLM, got None")
        
        # Calculate costs
        usage = response.usage
        if usage:
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            cost_usd = self._calculate_cost(input_tokens, output_tokens)
        
        return EvaluationResult(
            score=score,
            reasoning=reasoning,
            user_id=user.id,
            listing_id=listing.id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            evaluation_time_ms=evaluation_time_ms,
            model_used=self.model,
            evaluated_at=datetime.utcnow()
        )
    
    def _build_evaluation_prompt(self, user: User, listing: Listing) -> str:
        """Build the evaluation prompt for the LLM"""
        
        # Get user context
        hard_filters = user.get_hard_filters()
        
        # Build user preferences section
        user_context = f"""
USER PROFILE:
- Name: {user.name}
- Occupation: {user.occupation or 'Not specified'}
- Bio: {user.bio or 'Not specified'}

HARD REQUIREMENTS (already filtered):
- Price range: ${hard_filters.get('min_price', 'no min')} - ${hard_filters.get('max_price', 'no max')}
- Dates: {hard_filters.get('preferred_start_date', 'flexible')} to {hard_filters.get('preferred_end_date', 'flexible')}
- Listing type: {hard_filters.get('preferred_listing_type', 'any')}

DETAILED PREFERENCES:
{user.preference_profile or 'No specific preferences provided'}
"""

        # Build listing context
        listing_context = f"""
LISTING TO EVALUATE:
- Title: {listing.title or 'No title'}
- Price: ${listing.price}/{listing.price_period} ({listing.price_period} rate)
- Dates: {listing.start_date} to {listing.end_date}
- Neighborhood: {listing.neighborhood or 'Not specified'}
- Contact: {listing.contact_name or 'Anonymous'}
- Description: {(listing.full_description or listing.brief_description or 'No description available')[:500]}
- URL: {listing.url}
"""

        # Main evaluation instruction
        instruction = """
Evaluate how well this listing matches the user's preferences and requirements.

Consider:
1. How well the listing aligns with the user's lifestyle and preferences
2. Whether the location fits their needs
3. If the price offers good value for what's described
4. How the dates align with their needs
5. Overall quality and appeal of the listing

Provide a score from 1-10 where:
- 1-3: Poor match, significant issues or misalignment
- 4-6: Moderate match, some concerns but potentially workable
- 7-8: Good match, meets most requirements well
- 9-10: Excellent match, exceeds expectations

Include a brief explanation of your score focusing on the key factors that influenced your rating.
"""

        return f"{user_context}\n{listing_context}\n{instruction}"
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for the evaluation"""
        if self.model not in self.token_costs:
            # Default to gpt-4o-mini pricing if model not found
            costs = self.token_costs["gpt-4o-mini"]
        else:
            costs = self.token_costs[self.model]
        
        input_cost = input_tokens * costs["input"]
        output_cost = output_tokens * costs["output"]
        
        return input_cost + output_cost
    
    def get_cost_summary(self, evaluations: list[EvaluationResult]) -> Dict[str, Any]:
        """Generate cost summary from multiple evaluations"""
        if not evaluations:
            return {"total_evaluations": 0}
        
        total_cost = sum(eval.cost_usd for eval in evaluations)
        total_tokens = sum(eval.total_tokens for eval in evaluations)
        avg_cost = total_cost / len(evaluations)
        avg_tokens = total_tokens / len(evaluations)
        avg_time = sum(eval.evaluation_time_ms for eval in evaluations) / len(evaluations)
        
        return {
            "total_evaluations": len(evaluations),
            "total_cost_usd": round(total_cost, 6),
            "average_cost_per_evaluation": round(avg_cost, 6),
            "total_tokens": total_tokens,
            "average_tokens_per_evaluation": round(avg_tokens, 1),
            "average_evaluation_time_ms": round(avg_time, 1),
            "model_used": evaluations[0].model_used,
            "cost_per_1000_evaluations": round(avg_cost * 1000, 2)
        }
