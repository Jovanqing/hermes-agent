"""
Input resolver for workflow node execution.

Resolves variables and templates from workflow context:
- {{variable}} template substitution in prompts
- Input mapping from context sources to node inputs
- Node output references (e.g., node_1.output)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from workflow.models import (
    WorkflowContext,
    WorkflowNode,
    NodeType,
    InputNodeData,
    AgentNodeData,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template patterns
# ---------------------------------------------------------------------------

# Pattern for {{variable}} or {{node_id.field}}
TEMPLATE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')

# Pattern for node output references: node_id.output, node_id.field
NODE_OUTPUT_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_.]*)$')


# ---------------------------------------------------------------------------
# Input Resolver class
# ---------------------------------------------------------------------------


class InputResolver:
    """Resolves input values from workflow context.

    Handles:
    - Simple variable substitution: {{variable_name}}
    - Node output references: {{node_id.output}}
    - Nested field access: {{node_id.output.field}}
    - Default values: {{variable|default_value}}

    Example:
        >>> resolver = InputResolver(context)
        >>> resolver.resolve_template("Hello {{name}}!")
        "Hello World!"
        >>> resolver.resolve_template("Result: {{agent_1.output.summary}}")
        "Result: The analysis found..."
    """

    def __init__(
        self,
        context: WorkflowContext,
        strict: bool = False,
    ):
        """Initialize the resolver.

        Args:
            context: The workflow context with variables and outputs
            strict: If True, raise on missing variables. If False, leave as-is.
        """
        self.context = context
        self.strict = strict

    def resolve_template(
        self,
        template: str,
        additional_vars: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Resolve all {{variable}} placeholders in a template string.

        Args:
            template: The template string with placeholders
            additional_vars: Extra variables to use for resolution

        Returns:
            The resolved string
        """
        if not template or not isinstance(template, str):
            return template

        def replace_match(match: re.Match) -> str:
            var_path = match.group(1).strip()

            # Check for default value: {{var|default}}
            if '|' in var_path:
                var_path, default = var_path.split('|', 1)
                var_path = var_path.strip()
                default = default.strip()
            else:
                default = None

            # Try to resolve the value
            value = self._resolve_path(var_path, additional_vars)

            if value is None:
                if default is not None:
                    return default
                if self.strict:
                    raise ValueError(f"Cannot resolve variable: {var_path}")
                # Leave unresolved placeholders as-is
                return match.group(0)

            # Convert to string
            if isinstance(value, (dict, list)):
                import json
                return json.dumps(value, indent=2)
            return str(value)

        return TEMPLATE_PATTERN.sub(replace_match, template)

    def _resolve_path(
        self,
        path: str,
        additional_vars: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Resolve a variable path to its value.

        Handles:
        - Simple variables: "name" -> context.variables["name"]
        - Input variables: "input.name" -> context.input_variables["name"]
        - Node outputs: "node_id.output" -> context.node_outputs["node_id"].output
        - Nested fields: "node_id.output.field" -> output["field"]

        Args:
            path: The variable path to resolve
            additional_vars: Extra variables to check first

        Returns:
            The resolved value, or None if not found
        """
        # Check additional vars first
        if additional_vars and path in additional_vars:
            return additional_vars[path]

        # Check simple variables
        if path in self.context.variables:
            return self.context.variables[path]

        # Check input variables
        if path.startswith("input."):
            var_name = path[6:]  # Remove "input."
            if var_name in self.context.input_variables:
                return self.context.input_variables[var_name]

        # Check node outputs
        node_match = NODE_OUTPUT_PATTERN.match(path)
        if node_match:
            node_id = node_match.group(1)
            field_path = node_match.group(2)
            return self._resolve_node_output(node_id, field_path)

        # Try as a direct node_id for the output
        if path in self.context.node_outputs:
            return self.context.node_outputs[path].output

        return None

    def _resolve_node_output(
        self,
        node_id: str,
        field_path: str,
    ) -> Any:
        """Resolve a field from a node's output.

        Args:
            node_id: The node ID
            field_path: The field path (e.g., "output" or "output.summary")

        Returns:
            The resolved value, or None if not found
        """
        node_output = self.context.node_outputs.get(node_id)
        if node_output is None:
            return None

        # Handle common shortcuts
        if field_path == "output":
            return node_output.output

        if field_path == "status":
            return node_output.status.value

        if field_path == "duration":
            return node_output.duration

        if field_path == "tokens":
            return node_output.tokens

        # Handle nested field access on output
        if field_path.startswith("output."):
            remaining_path = field_path[7:]  # Remove "output."
            return self._get_nested_value(node_output.output, remaining_path)

        return None

    def _get_nested_value(
        self,
        obj: Any,
        path: str,
    ) -> Any:
        """Get a nested value from an object using dot notation.

        Args:
            obj: The object to access
            path: Dot-separated path (e.g., "user.name.first")

        Returns:
            The value at the path, or None if not found
        """
        parts = path.split('.')
        current = obj

        for part in parts:
            if current is None:
                return None

            # Handle dict access
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return None

            # Handle list indexing
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None

            # Handle object attributes
            elif hasattr(current, part):
                current = getattr(current, part)

            else:
                return None

        return current

    def resolve_mapping(
        self,
        mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """Resolve an input mapping to actual values.

        The mapping specifies how to build input variables from context:
        {"user_query": "input.question", "previous": "agent_1.output"}

        Args:
            mapping: Dict of variable name -> source path

        Returns:
            Dict of variable name -> resolved value
        """
        result = {}

        for var_name, source_path in mapping.items():
            value = self._resolve_path(source_path)
            if value is not None:
                result[var_name] = value
            elif self.strict:
                raise ValueError(f"Cannot resolve mapping source: {source_path}")

        return result


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def resolve_prompt_template(
    template: str,
    context: WorkflowContext,
    additional_vars: Optional[Dict[str, Any]] = None,
    strict: bool = False,
) -> str:
    """Resolve all placeholders in a prompt template.

    Convenience function that creates an InputResolver and resolves the template.

    Args:
        template: The prompt template with {{variable}} placeholders
        context: The workflow context
        additional_vars: Extra variables for resolution
        strict: If True, raise on missing variables

    Returns:
        The resolved prompt string
    """
    resolver = InputResolver(context, strict=strict)
    return resolver.resolve_template(template, additional_vars)


def resolve_input_mapping(
    mapping: Dict[str, str],
    context: WorkflowContext,
) -> Dict[str, Any]:
    """Resolve an input mapping to actual values.

    Convenience function that creates an InputResolver and resolves the mapping.

    Args:
        mapping: Dict of variable name -> source path
        context: The workflow context

    Returns:
        Dict of variable name -> resolved value
    """
    resolver = InputResolver(context)
    return resolver.resolve_mapping(mapping)


def get_template_variables(template: str) -> Set[str]:
    """Extract all variable names from a template.

    Args:
        template: The template string

    Returns:
        Set of variable names used in the template
    """
    matches = TEMPLATE_PATTERN.findall(template)
    # Strip default values
    variables = set()
    for match in matches:
        var_path = match.strip()
        if '|' in var_path:
            var_path = var_path.split('|')[0].strip()
        variables.add(var_path)
    return variables


def validate_template_dependencies(
    template: str,
    context: WorkflowContext,
    current_node_id: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Validate that all template dependencies are available.

    Checks that all variables referenced in the template are either:
    - Defined in context.variables
    - Defined in context.input_variables
    - Outputs from previously executed nodes

    Args:
        template: The template to validate
        context: The workflow context
        current_node_id: ID of the node being validated (to detect cycles)

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    variables = get_template_variables(template)
    errors = []

    for var in variables:
        # Check if it's a simple variable
        if var in context.variables:
            continue

        # Check input variables
        if var.startswith("input."):
            var_name = var[6:]
            if var_name in context.input_variables:
                continue
            errors.append(f"Input variable not found: {var_name}")
            continue

        # Check node output reference
        node_match = NODE_OUTPUT_PATTERN.match(var)
        if node_match:
            node_id = node_match.group(1)

            # Check for self-reference
            if current_node_id and node_id == current_node_id:
                errors.append(f"Node cannot reference its own output: {var}")
                continue

            # Check if node has been executed
            if node_id in context.node_outputs:
                continue

            # Node hasn't been executed yet - this might be OK if it's a
            # dependency that will be satisfied before execution
            errors.append(f"Node output not yet available: {var}")
            continue

        # Simple variable not found
        if var not in context.variables:
            errors.append(f"Variable not found: {var}")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Input node handling
# ---------------------------------------------------------------------------


def extract_input_variables(
    node: WorkflowNode,
    provided_inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract variables from an input node.

    Combines default values from the node with provided inputs.

    Args:
        node: The input node
        provided_inputs: Values provided at execution time

    Returns:
        Dict of variable name -> value
    """
    if node.type != NodeType.INPUT:
        return {}

    typed_data = node.get_typed_data()
    if not isinstance(typed_data, InputNodeData):
        return {}

    # Start with defaults
    variables = dict(typed_data.variables)

    # Override with provided inputs
    if provided_inputs:
        variables.update(provided_inputs)

    # Check required variables
    for required in typed_data.required:
        if required not in variables:
            raise ValueError(
                f"Required input variable not provided: {required}"
            )

    return variables


def prepare_agent_inputs(
    node: WorkflowNode,
    context: WorkflowContext,
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """Prepare inputs for an agent node.

    Resolves the prompt template and input mapping to produce
    the final prompt and variables for the agent.

    Args:
        node: The agent node
        context: The workflow context

    Returns:
        Tuple of (resolved_prompt, system_prompt, resolved_variables)
    """
    typed_data = node.get_typed_data()
    if not isinstance(typed_data, AgentNodeData):
        raise ValueError(f"Node {node.id} is not an agent node")

    resolver = InputResolver(context)

    # Resolve input mapping first to get variables
    resolved_vars = resolver.resolve_mapping(typed_data.input_mapping)

    # Resolve the prompt template with variables
    resolved_prompt = resolver.resolve_template(
        typed_data.prompt,
        additional_vars=resolved_vars,
    )

    # Resolve system prompt if present
    system_prompt = None
    if typed_data.system_prompt:
        system_prompt = resolver.resolve_template(
            typed_data.system_prompt,
            additional_vars=resolved_vars,
        )

    return resolved_prompt, system_prompt, resolved_vars
