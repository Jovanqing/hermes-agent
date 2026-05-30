"""
Retry handling for workflow node execution.

Provides configurable retry policies with:
- Maximum retry attempts
- Exponential or linear backoff
- Jitter to prevent thundering herd
- Error filtering (retry only specific errors)
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Backoff strategies
# ---------------------------------------------------------------------------


class BackoffStrategy(str, Enum):
    """Backoff strategy for retry delays."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


def calculate_backoff(
    attempt: int,
    base_delay: float,
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    max_delay: float = 60.0,
    jitter: bool = True,
    jitter_factor: float = 0.1,
) -> float:
    """Calculate backoff delay for a retry attempt.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        strategy: Backoff strategy to use
        max_delay: Maximum delay cap
        jitter: Whether to add random jitter
        jitter_factor: Jitter as a fraction of delay (0.1 = ±10%)

    Returns:
        Delay in seconds
    """
    if strategy == BackoffStrategy.EXPONENTIAL:
        delay = base_delay * (2 ** attempt)
    elif strategy == BackoffStrategy.LINEAR:
        delay = base_delay * (attempt + 1)
    else:  # CONSTANT
        delay = base_delay

    # Cap at max delay
    delay = min(delay, max_delay)

    # Add jitter
    if jitter:
        jitter_amount = delay * jitter_factor
        delay += random.uniform(-jitter_amount, jitter_amount)
        delay = max(0, delay)  # Ensure non-negative

    return delay


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retry)
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay cap in seconds
        strategy: Backoff strategy (exponential, linear, constant)
        jitter: Whether to add random jitter to delays
        retry_on_errors: Set of error types to retry (empty = retry all)
        retry_on_messages: Set of error message patterns to retry
        timeout: Per-attempt timeout in seconds (None = no timeout)
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True
    retry_on_errors: Set[str] = field(default_factory=set)
    retry_on_messages: Set[str] = field(default_factory=set)
    timeout: Optional[float] = None

    def should_retry(
        self,
        attempt: int,
        error: Optional[Exception] = None,
    ) -> bool:
        """Check if a retry should be attempted.

        Args:
            attempt: Current attempt number (0-indexed)
            error: The error that occurred (if any)

        Returns:
            True if should retry
        """
        # Check max retries
        if attempt >= self.max_retries:
            return False

        # If no error filters, retry all errors
        if not self.retry_on_errors and not self.retry_on_messages:
            return True

        if error is None:
            return True

        # Check error type
        error_type = type(error).__name__
        if self.retry_on_errors and error_type in self.retry_on_errors:
            return True

        # Check error message
        error_msg = str(error).lower()
        for pattern in self.retry_on_messages:
            if pattern.lower() in error_msg:
                return True

        return False

    def get_delay(self, attempt: int) -> float:
        """Get the delay before a retry attempt.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        return calculate_backoff(
            attempt=attempt,
            base_delay=self.base_delay,
            strategy=self.strategy,
            max_delay=self.max_delay,
            jitter=self.jitter,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "strategy": self.strategy.value,
            "jitter": self.jitter,
            "retry_on_errors": list(self.retry_on_errors),
            "retry_on_messages": list(self.retry_on_messages),
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RetryPolicy:
        """Create from dictionary."""
        return cls(
            max_retries=data.get("max_retries", 3),
            base_delay=data.get("base_delay", 1.0),
            max_delay=data.get("max_delay", 60.0),
            strategy=BackoffStrategy(data.get("strategy", "exponential")),
            jitter=data.get("jitter", True),
            retry_on_errors=set(data.get("retry_on_errors", [])),
            retry_on_messages=set(data.get("retry_on_messages", [])),
            timeout=data.get("timeout"),
        )


# ---------------------------------------------------------------------------
# Retry result
# ---------------------------------------------------------------------------


@dataclass
class RetryResult:
    """Result of a retry operation.

    Attributes:
        success: Whether the operation eventually succeeded
        attempts: Number of attempts made
        result: The result value (if successful)
        error: The final error (if failed)
        errors: List of all errors encountered
        total_duration: Total time spent retrying
    """

    success: bool
    attempts: int
    result: Any = None
    error: Optional[Exception] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    total_duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "attempts": self.attempts,
            "error": str(self.error) if self.error else None,
            "errors": self.errors,
            "total_duration": self.total_duration,
        }


# ---------------------------------------------------------------------------
# Retry handler
# ---------------------------------------------------------------------------


class RetryHandler:
    """Handles retry logic for async operations.

    Example:
        >>> policy = RetryPolicy(max_retries=3, base_delay=1.0)
        >>> handler = RetryHandler(policy)
        >>> result = await handler.execute(my_async_function, arg1, arg2)
        >>> if result.success:
        ...     print(f"Succeeded after {result.attempts} attempts")
    """

    def __init__(
        self,
        policy: RetryPolicy,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    ):
        """Initialize the retry handler.

        Args:
            policy: Retry policy configuration
            on_retry: Optional callback for each retry (attempt, error, delay)
        """
        self.policy = policy
        self.on_retry = on_retry

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> RetryResult:
        """Execute a function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            RetryResult with the outcome
        """
        start_time = time.time()
        errors: List[Dict[str, Any]] = []
        last_error: Optional[Exception] = None

        for attempt in range(self.policy.max_retries + 1):
            try:
                # Execute with optional timeout
                if self.policy.timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.policy.timeout,
                    )
                else:
                    result = await func(*args, **kwargs)

                return RetryResult(
                    success=True,
                    attempts=attempt + 1,
                    result=result,
                    errors=errors,
                    total_duration=time.time() - start_time,
                )

            except asyncio.TimeoutError as e:
                last_error = e
                errors.append({
                    "attempt": attempt,
                    "error_type": "TimeoutError",
                    "error_message": f"Operation timed out after {self.policy.timeout}s",
                    "timestamp": datetime.now().isoformat(),
                })

            except Exception as e:
                last_error = e
                errors.append({
                    "attempt": attempt,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

            # Check if we should retry
            if not self.policy.should_retry(attempt, last_error):
                break

            # Calculate delay
            delay = self.policy.get_delay(attempt)

            # Notify callback
            if self.on_retry and last_error:
                self.on_retry(attempt, last_error, delay)

            logger.info(
                "Retrying after %.2fs (attempt %d/%d): %s",
                delay,
                attempt + 1,
                self.policy.max_retries,
                str(last_error)[:100],
            )

            # Wait before retry
            await asyncio.sleep(delay)

        return RetryResult(
            success=False,
            attempts=len(errors),
            error=last_error,
            errors=errors,
            total_duration=time.time() - start_time,
        )


# ---------------------------------------------------------------------------
# Preset policies
# ---------------------------------------------------------------------------


def aggressive_retry(max_retries: int = 5) -> RetryPolicy:
    """Create an aggressive retry policy.

    Good for operations that frequently fail transiently.
    """
    return RetryPolicy(
        max_retries=max_retries,
        base_delay=0.5,
        max_delay=30.0,
        strategy=BackoffStrategy.EXPONENTIAL,
    )


def conservative_retry(max_retries: int = 2) -> RetryPolicy:
    """Create a conservative retry policy.

    Good for operations that rarely fail and are expensive.
    """
    return RetryPolicy(
        max_retries=max_retries,
        base_delay=2.0,
        max_delay=60.0,
        strategy=BackoffStrategy.LINEAR,
    )


def no_retry() -> RetryPolicy:
    """Create a no-retry policy."""
    return RetryPolicy(max_retries=0)


def network_retry() -> RetryPolicy:
    """Create a retry policy optimized for network operations.

    Retries on common network errors with exponential backoff.
    """
    return RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        strategy=BackoffStrategy.EXPONENTIAL,
        retry_on_errors={
            "ConnectionError",
            "TimeoutError",
            "ConnectionResetError",
            "ConnectionAbortedError",
        },
        retry_on_messages={
            "connection refused",
            "connection reset",
            "timed out",
            "network unreachable",
        },
    )
