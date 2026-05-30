"""
Workflow Error Recovery Module.

Provides error handling and recovery mechanisms:
- RetryPolicy: Configurable retry with backoff
- BreakpointManager: Pause/resume execution at breakpoints
- ErrorClassifier: Categorize errors for appropriate handling
- ExecutionHistory: Track and replay past executions
"""

from workflow.engine.recovery.retry import (
    RetryPolicy,
    RetryResult,
    RetryHandler,
    calculate_backoff,
    BackoffStrategy,
    aggressive_retry,
    conservative_retry,
    no_retry,
    network_retry,
)
from workflow.engine.recovery.breakpoints import (
    BreakpointManager,
    Breakpoint,
    BreakpointState,
)
from workflow.engine.recovery.error_classifier import (
    ErrorClassifier,
    ErrorCategory,
    ClassifiedError,
    classify_error,
    get_default_classifier,
)
from workflow.engine.recovery.history import (
    ExecutionHistory,
    ExecutionRecord,
)

__all__ = [
    "RetryPolicy",
    "RetryResult",
    "RetryHandler",
    "calculate_backoff",
    "BackoffStrategy",
    "BreakpointManager",
    "Breakpoint",
    "BreakpointState",
    "ErrorClassifier",
    "ErrorCategory",
    "ClassifiedError",
    "classify_error",
    "get_default_classifier",
    "ExecutionHistory",
    "ExecutionRecord",
]
