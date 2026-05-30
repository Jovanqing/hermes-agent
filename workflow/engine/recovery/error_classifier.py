"""
Error classifier for workflow execution.

Categorizes errors to determine appropriate handling:
- Transient errors: Should retry
- Permanent errors: Should not retry
- User errors: Bad input, should report
- System errors: Infrastructure issues
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error categories
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
    """Categories of errors."""

    # Transient - can retry
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK = "network"
    TEMPORARY_UNAVAILABLE = "temporary_unavailable"

    # Permanent - should not retry
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    INVALID_INPUT = "invalid_input"
    QUOTA_EXCEEDED = "quota_exceeded"

    # User errors - bad input
    VALIDATION = "validation"
    SYNTAX = "syntax"
    CONFIGURATION = "configuration"

    # System errors
    INTERNAL = "internal"
    RESOURCE_EXHAUSTED = "resource_exhausted"

    # Unknown
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Classified error
# ---------------------------------------------------------------------------


@dataclass
class ClassifiedError:
    """An error with classification metadata.

    Attributes:
        category: The error category
        original_error: The original exception
        message: Human-readable error message
        retry_recommended: Whether retry is recommended
        user_action: Suggested action for the user
        details: Additional error details
    """

    category: ErrorCategory
    original_error: Optional[Exception] = None
    message: str = ""
    retry_recommended: bool = False
    user_action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def error_type(self) -> str:
        """Get the error type name."""
        if self.original_error:
            return type(self.original_error).__name__
        return "Unknown"

    @property
    def is_transient(self) -> bool:
        """Check if this is a transient error."""
        return self.category in {
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.NETWORK,
            ErrorCategory.TEMPORARY_UNAVAILABLE,
        }

    @property
    def is_user_error(self) -> bool:
        """Check if this is a user error."""
        return self.category in {
            ErrorCategory.VALIDATION,
            ErrorCategory.SYNTAX,
            ErrorCategory.CONFIGURATION,
            ErrorCategory.INVALID_INPUT,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "error_type": self.error_type,
            "message": self.message,
            "retry_recommended": self.retry_recommended,
            "user_action": self.user_action,
            "is_transient": self.is_transient,
            "is_user_error": self.is_user_error,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Error classifier
# ---------------------------------------------------------------------------


class ErrorClassifier:
    """Classifies errors into categories.

    Uses pattern matching and error type inspection to categorize errors
    and provide appropriate handling recommendations.

    Example:
        >>> classifier = ErrorClassifier()
        >>> classified = classifier.classify(some_exception)
        >>> if classified.retry_recommended:
        ...     # Retry the operation
    """

    def __init__(self):
        self._patterns: List[tuple] = self._build_patterns()

    def _build_patterns(self) -> List[tuple]:
        """Build the pattern matching rules."""
        return [
            # Rate limiting
            (ErrorCategory.RATE_LIMIT, [
                re.compile(r"rate.?limit", re.I),
                re.compile(r"too many requests", re.I),
                re.compile(r"429", re.I),
                re.compile(r"throttl", re.I),
            ]),

            # Timeouts
            (ErrorCategory.TIMEOUT, [
                re.compile(r"timeout", re.I),
                re.compile(r"timed out", re.I),
                re.compile(r"deadline exceeded", re.I),
            ]),

            # Network errors
            (ErrorCategory.NETWORK, [
                re.compile(r"connection (refused|reset|aborted)", re.I),
                re.compile(r"network (unreachable|error)", re.I),
                re.compile(r"dns (resolution|error)", re.I),
                re.compile(r"socket (error|timeout)", re.I),
            ]),

            # Temporary unavailability
            (ErrorCategory.TEMPORARY_UNAVAILABLE, [
                re.compile(r"service (unavailable|temporarily)", re.I),
                re.compile(r"503", re.I),
                re.compile(r"try again (later|soon)", re.I),
            ]),

            # Authentication
            (ErrorCategory.AUTHENTICATION, [
                re.compile(r"(unauthorized|authentication)", re.I),
                re.compile(r"invalid (api ?key|token|credentials)", re.I),
                re.compile(r"401", re.I),
            ]),

            # Permission
            (ErrorCategory.PERMISSION, [
                re.compile(r"(forbidden|permission denied)", re.I),
                re.compile(r"access denied", re.I),
                re.compile(r"403", re.I),
            ]),

            # Not found
            (ErrorCategory.NOT_FOUND, [
                re.compile(r"(not found|does not exist)", re.I),
                re.compile(r"404", re.I),
                re.compile(r"no such", re.I),
            ]),

            # Invalid input
            (ErrorCategory.INVALID_INPUT, [
                re.compile(r"invalid (input|request|parameter)", re.I),
                re.compile(r"bad request", re.I),
                re.compile(r"400", re.I),
            ]),

            # Quota exceeded
            (ErrorCategory.QUOTA_EXCEEDED, [
                re.compile(r"quota (exceeded|limit)", re.I),
                re.compile(r"(usage|billing) limit", re.I),
                re.compile(r"insufficient (funds|credits|balance)", re.I),
            ]),

            # Validation
            (ErrorCategory.VALIDATION, [
                re.compile(r"validation (error|failed)", re.I),
                re.compile(r"invalid (format|value|type)", re.I),
                re.compile(r"must be", re.I),
            ]),

            # Syntax
            (ErrorCategory.SYNTAX, [
                re.compile(r"syntax error", re.I),
                re.compile(r"parse error", re.I),
                re.compile(r"unexpected token", re.I),
            ]),

            # Configuration
            (ErrorCategory.CONFIGURATION, [
                re.compile(r"(missing|required) (config|setting)", re.I),
                re.compile(r"configuration (error|invalid)", re.I),
            ]),

            # Resource exhausted
            (ErrorCategory.RESOURCE_EXHAUSTED, [
                re.compile(r"(memory|disk|cpu) (exhausted|full|limit)", re.I),
                re.compile(r"out of memory", re.I),
                re.compile(r"no space left", re.I),
            ]),
        ]

    def classify(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassifiedError:
        """Classify an error.

        Args:
            error: The exception to classify
            context: Optional additional context

        Returns:
            ClassifiedError with category and recommendations
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Check patterns
        category = self._match_patterns(error_message)

        # Check error type
        if category == ErrorCategory.UNKNOWN:
            category = self._classify_by_type(error)

        # Determine retry recommendation
        retry_recommended = category in {
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.NETWORK,
            ErrorCategory.TEMPORARY_UNAVAILABLE,
        }

        # Generate user action suggestion
        user_action = self._suggest_action(category)

        return ClassifiedError(
            category=category,
            original_error=error,
            message=error_message,
            retry_recommended=retry_recommended,
            user_action=user_action,
            details={
                "error_type": error_type,
                "context": context or {},
            },
        )

    def _match_patterns(self, message: str) -> ErrorCategory:
        """Match error message against known patterns."""
        for category, patterns in self._patterns:
            for pattern in patterns:
                if pattern.search(message):
                    return category
        return ErrorCategory.UNKNOWN

    def _classify_by_type(self, error: Exception) -> ErrorCategory:
        """Classify by exception type."""
        error_type = type(error).__name__

        # Common Python exceptions
        type_mapping = {
            "TimeoutError": ErrorCategory.TIMEOUT,
            "ConnectionError": ErrorCategory.NETWORK,
            "ConnectionResetError": ErrorCategory.NETWORK,
            "ConnectionAbortedError": ErrorCategory.NETWORK,
            "ConnectionRefusedError": ErrorCategory.NETWORK,
            "OSError": ErrorCategory.NETWORK,
            "PermissionError": ErrorCategory.PERMISSION,
            "FileNotFoundError": ErrorCategory.NOT_FOUND,
            "ValueError": ErrorCategory.VALIDATION,
            "TypeError": ErrorCategory.VALIDATION,
            "KeyError": ErrorCategory.INVALID_INPUT,
            "IndexError": ErrorCategory.INVALID_INPUT,
            "SyntaxError": ErrorCategory.SYNTAX,
            "MemoryError": ErrorCategory.RESOURCE_EXHAUSTED,
        }

        return type_mapping.get(error_type, ErrorCategory.UNKNOWN)

    def _suggest_action(self, category: ErrorCategory) -> str:
        """Suggest a user action based on error category."""
        actions = {
            ErrorCategory.RATE_LIMIT: "Wait a moment and try again, or reduce request frequency.",
            ErrorCategory.TIMEOUT: "The operation took too long. Try again or check your network connection.",
            ErrorCategory.NETWORK: "Check your network connection and try again.",
            ErrorCategory.TEMPORARY_UNAVAILABLE: "The service is temporarily unavailable. Try again in a few minutes.",
            ErrorCategory.AUTHENTICATION: "Check your API key or authentication credentials.",
            ErrorCategory.PERMISSION: "You don't have permission for this action. Contact your administrator.",
            ErrorCategory.NOT_FOUND: "The requested resource was not found. Check the ID or path.",
            ErrorCategory.INVALID_INPUT: "Check your input parameters and try again.",
            ErrorCategory.QUOTA_EXCEEDED: "You've exceeded your quota. Upgrade your plan or wait for quota reset.",
            ErrorCategory.VALIDATION: "Check your input values and format.",
            ErrorCategory.SYNTAX: "Check the syntax of your input.",
            ErrorCategory.CONFIGURATION: "Check your configuration settings.",
            ErrorCategory.INTERNAL: "An internal error occurred. Please try again or contact support.",
            ErrorCategory.RESOURCE_EXHAUSTED: "System resources are exhausted. Try reducing the workload.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again.",
        }
        return actions.get(category, "Please try again or contact support.")


# ---------------------------------------------------------------------------
# Default classifier instance
# ---------------------------------------------------------------------------

_default_classifier: Optional[ErrorClassifier] = None


def get_default_classifier() -> ErrorClassifier:
    """Get the default error classifier instance."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = ErrorClassifier()
    return _default_classifier


def classify_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> ClassifiedError:
    """Classify an error using the default classifier.

    Convenience function.

    Args:
        error: The exception to classify
        context: Optional additional context

    Returns:
        ClassifiedError
    """
    classifier = get_default_classifier()
    return classifier.classify(error, context)
