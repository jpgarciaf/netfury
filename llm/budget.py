"""Atomic budget manager for LLM API usage.

Enforces three configurable limits per pipeline run:
- Maximum number of LLM calls
- Maximum total tokens consumed
- Maximum USD cost

Thread-safe via threading.Lock for concurrent usage.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

from settings import LLM_PRICING

logger = logging.getLogger(__name__)


@dataclass
class Budget:
    """Budget configuration for a pipeline run.

    Set any limit to None for unlimited.
    """

    max_llm_calls: int | None = None
    max_tokens: int | None = None
    max_cost_usd: float | None = None


class BudgetManager:
    """Thread-safe budget tracker that enforces limits.

    Usage:
        budget = BudgetManager(Budget(max_llm_calls=20, max_cost_usd=1.0))

        if budget.can_call():
            response = llm_client.extract(...)
            budget.record_call(
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                model="gpt-4o",
            )
    """

    def __init__(self, budget: Budget | None = None) -> None:
        self._budget = budget or Budget()
        self._lock = threading.Lock()
        self._calls: int = 0
        self._tokens: int = 0
        self._cost_usd: float = 0.0

    def can_call(self) -> bool:
        """Check if all limits still have headroom.

        Returns:
            True if another LLM call is allowed.
        """
        with self._lock:
            return self._check_limits() is None

    def record_call(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float | None = None,
        model: str | None = None,
    ) -> None:
        """Record a completed LLM call.

        Args:
            input_tokens: Tokens consumed in the prompt.
            output_tokens: Tokens generated in the response.
            cost_usd: Explicit cost. If None, calculated from model pricing.
            model: Model name for auto-calculating cost.
        """
        if cost_usd is None and model:
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

        with self._lock:
            self._calls += 1
            self._tokens += input_tokens + output_tokens
            self._cost_usd += cost_usd or 0.0

        logger.debug(
            "Budget: call #%d | tokens=%d | cost=$%.4f",
            self._calls, self._tokens, self._cost_usd,
        )

    def exhausted_reason(self) -> str | None:
        """Return which limit was hit, or None if budget remains.

        Returns:
            Human-readable reason string, or None.
        """
        with self._lock:
            return self._check_limits()

    def remaining(self) -> dict:
        """Return remaining budget for logging.

        Returns:
            Dict with remaining calls, tokens, and cost.
        """
        with self._lock:
            b = self._budget
            return {
                "calls_used": self._calls,
                "calls_remaining": (
                    b.max_llm_calls - self._calls
                    if b.max_llm_calls is not None else None
                ),
                "tokens_used": self._tokens,
                "tokens_remaining": (
                    b.max_tokens - self._tokens
                    if b.max_tokens is not None else None
                ),
                "cost_used_usd": round(self._cost_usd, 4),
                "cost_remaining_usd": (
                    round(b.max_cost_usd - self._cost_usd, 4)
                    if b.max_cost_usd is not None else None
                ),
            }

    @property
    def calls(self) -> int:
        """Total LLM calls made so far."""
        return self._calls

    @property
    def tokens(self) -> int:
        """Total tokens consumed so far."""
        return self._tokens

    @property
    def cost_usd(self) -> float:
        """Total USD cost so far."""
        return self._cost_usd

    def _check_limits(self) -> str | None:
        """Check limits (must be called under lock).

        Returns:
            Reason string if any limit is exhausted, None otherwise.
        """
        b = self._budget
        if b.max_llm_calls is not None and self._calls >= b.max_llm_calls:
            return f"Max LLM calls reached ({self._calls}/{b.max_llm_calls})"
        if b.max_tokens is not None and self._tokens >= b.max_tokens:
            return f"Max tokens reached ({self._tokens}/{b.max_tokens})"
        if b.max_cost_usd is not None and self._cost_usd >= b.max_cost_usd:
            return f"Max cost reached (${self._cost_usd:.4f}/${b.max_cost_usd:.2f})"
        return None

    @staticmethod
    def _calculate_cost(
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate USD cost from token counts and model pricing.

        Args:
            model: Model identifier.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost in USD.
        """
        pricing = LLM_PRICING.get(model, {"input": 0.0, "output": 0.0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
