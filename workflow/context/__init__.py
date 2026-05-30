"""
Workflow Context Management Module.

Provides tools for managing workflow context during execution:
- ContextAccumulator: Builds context from node outputs
- PromptInterpolator: Resolves variables in prompts
"""

from workflow.context.accumulator import (
    ContextAccumulator,
    ContextSnapshot,
)
from workflow.context.interpolator import (
    PromptInterpolator,
    InterpolationResult,
    InterpolationError,
)

__all__ = [
    "ContextAccumulator",
    "ContextSnapshot",
    "PromptInterpolator",
    "InterpolationResult",
    "InterpolationError",
]
