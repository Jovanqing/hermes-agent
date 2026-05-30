"""
Prompt interpolator for workflow execution.

Resolves template variables in prompts:
- {{variable}} - simple variable substitution
- {{input.name}} - input variable access
- {{node_id.output}} - node output access
- {{node_id.output.field}} - nested field access
- {{variable|default}} - default value syntax
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from workflow.context.accumulator import ContextAccumulator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InterpolationError(Exception):
    """Raised when interpolation fails."""

    def __init__(
        self,
        message: str,
        variable: str,
        position: Optional[Tuple[int, int]] = None,
    ):
        super().__init__(message)
        self.variable = variable
        self.position = position


# ---------------------------------------------------------------------------
# Interpolation result
# ---------------------------------------------------------------------------


@dataclass
class InterpolationResult:
    """Result of prompt interpolation.

    Attributes:
        original: The original template
        resolved: The resolved prompt
        variables_used: Set of variables that were resolved
        variables_missing: Set of variables that could not be resolved
        warnings: List of warnings generated during interpolation
    """

    original: str
    resolved: str
    variables_used: Set[str] = field(default_factory=set)
    variables_missing: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if all variables were resolved."""
        return len(self.variables_missing) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original": self.original,
            "resolved": self.resolved,
            "variables_used": list(self.variables_used),
            "variables_missing": list(self.variables_missing),
            "warnings": self.warnings,
            "is_complete": self.is_complete,
        }


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Pattern for {{variable}} or {{variable|default}}
VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')

# Pattern for variable paths like "node_id.output.field"
PATH_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$')

# Pattern for input variable access
INPUT_PREFIX = "input."


# ---------------------------------------------------------------------------
# Prompt interpolator
# ---------------------------------------------------------------------------


class PromptInterpolator:
    """Interpolates variables in prompt templates.

    Supports:
    - Simple variables: {{name}}
    - Input variables: {{input.question}}
    - Node outputs: {{agent_1.output}}
    - Nested fields: {{agent_1.output.summary}}
    - Default values: {{name|World}}

    Example:
        >>> interpolator = PromptInterpolator()
        >>> result = interpolator.interpolate(
        ...     "Hello {{name}}!",
        ...     context
        ... )
        >>> result.resolved
        "Hello World!"
    """

    def __init__(
        self,
        strict: bool = False,
        custom_resolvers: Optional[Dict[str, Callable[[str, Any], Any]]] = None,
    ):
        """Initialize the interpolator.

        Args:
            strict: If True, raise on missing variables
            custom_resolvers: Optional dict of prefix -> resolver function
        """
        self.strict = strict
        self.custom_resolvers = custom_resolvers or {}

    def interpolate(
        self,
        template: str,
        context: ContextAccumulator,
        additional_vars: Optional[Dict[str, Any]] = None,
    ) -> InterpolationResult:
        """Interpolate variables in a template.

        Args:
            template: The prompt template with {{variable}} placeholders
            context: The context accumulator with variables
            additional_vars: Extra variables to use for resolution

        Returns:
            InterpolationResult with resolved prompt and metadata
        """
        if not template:
            return InterpolationResult(
                original=template,
                resolved=template,
            )

        variables_used: Set[str] = set()
        variables_missing: Set[str] = set()
        warnings: List[str] = []

        def replace_match(match: re.Match) -> str:
            expr = match.group(1).strip()

            # Check for default value: {{var|default}}
            if '|' in expr:
                var_path, default = expr.split('|', 1)
                var_path = var_path.strip()
                default = default.strip()
            else:
                var_path = expr
                default = None

            # Try to resolve the value
            value = self._resolve(
                var_path,
                context,
                additional_vars,
            )

            if value is not None:
                variables_used.add(var_path)
                return self._format_value(value)

            # Value not found
            if default is not None:
                variables_used.add(var_path)
                return default

            variables_missing.add(var_path)

            if self.strict:
                raise InterpolationError(
                    f"Cannot resolve variable: {var_path}",
                    variable=var_path,
                    position=match.span(),
                )

            warnings.append(f"Unresolved variable: {var_path}")
            return match.group(0)  # Leave as-is

        resolved = VARIABLE_PATTERN.sub(replace_match, template)

        return InterpolationResult(
            original=template,
            resolved=resolved,
            variables_used=variables_used,
            variables_missing=variables_missing,
            warnings=warnings,
        )

    def _resolve(
        self,
        path: str,
        context: ContextAccumulator,
        additional_vars: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Resolve a variable path to its value.

        Args:
            path: The variable path
            context: The context accumulator
            additional_vars: Extra variables

        Returns:
            The resolved value or None
        """
        # Check additional vars first
        if additional_vars and path in additional_vars:
            return additional_vars[path]

        # Check custom resolvers
        for prefix, resolver in self.custom_resolvers.items():
            if path.startswith(prefix):
                try:
                    return resolver(path, context)
                except Exception as e:
                    logger.warning("Custom resolver failed for %s: %s", path, e)

        # Use context's resolve_path
        return context.resolve_path(path)

    def _format_value(self, value: Any) -> str:
        """Format a value for interpolation.

        Args:
            value: The value to format

        Returns:
            Formatted string
        """
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)
        return str(value)

    def extract_variables(self, template: str) -> Set[str]:
        """Extract all variable names from a template.

        Args:
            template: The template string

        Returns:
            Set of variable names
        """
        variables: Set[str] = set()

        for match in VARIABLE_PATTERN.finditer(template):
            expr = match.group(1).strip()
            # Strip default value
            if '|' in expr:
                expr = expr.split('|')[0].strip()
            variables.add(expr)

        return variables

    def validate_template(
        self,
        template: str,
        context: ContextAccumulator,
    ) -> Tuple[bool, List[str]]:
        """Validate that all variables in a template can be resolved.

        Args:
            template: The template to validate
            context: The context to validate against

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        result = self.interpolate(template, context)
        errors = []

        for var in result.variables_missing:
            errors.append(f"Cannot resolve variable: {var}")

        return result.is_complete, errors


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


_default_interpolator: Optional[PromptInterpolator] = None


def get_default_interpolator() -> PromptInterpolator:
    """Get the default interpolator instance."""
    global _default_interpolator
    if _default_interpolator is None:
        _default_interpolator = PromptInterpolator()
    return _default_interpolator


def interpolate_prompt(
    template: str,
    context: ContextAccumulator,
    additional_vars: Optional[Dict[str, Any]] = None,
) -> str:
    """Interpolate a prompt template.

    Convenience function using the default interpolator.

    Args:
        template: The prompt template
        context: The context accumulator
        additional_vars: Extra variables

    Returns:
        The resolved prompt
    """
    interpolator = get_default_interpolator()
    result = interpolator.interpolate(template, context, additional_vars)
    return result.resolved


def extract_template_variables(template: str) -> Set[str]:
    """Extract variables from a template.

    Convenience function using the default interpolator.

    Args:
        template: The template string

    Returns:
        Set of variable names
    """
    interpolator = get_default_interpolator()
    return interpolator.extract_variables(template)
