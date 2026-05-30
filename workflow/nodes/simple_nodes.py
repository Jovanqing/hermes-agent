"""
Simple node executors for input, output, and transform nodes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from workflow.models import (
    InputNodeData,
    NodeExecutionStatus,
    NodeType,
    OutputNodeData,
    TransformNodeData,
    WorkflowNode,
)
from workflow.nodes.base import (
    BaseNodeExecutor,
    ExecutionContext,
    NodeExecutionResult,
)
from workflow.nodes.input_resolver import (
    InputResolver,
    extract_input_variables,
)

logger = logging.getLogger(__name__)


class InputNodeExecutor(BaseNodeExecutor):
    """Executor for input nodes.

    Input nodes define the initial variables for a workflow.
    They don't execute any LLM calls - they just expose their
    configured variables to the workflow context.
    """

    node_type = "input"

    async def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        """Execute an input node.

        Extracts variables from the node and input context,
        and stores them in the workflow context.
        """
        node = context.node

        try:
            # Get typed data
            typed_data = node.get_typed_data()
            if not isinstance(typed_data, InputNodeData):
                return NodeExecutionResult.error(
                    node_id=node.id,
                    error="Node data is not InputNodeData",
                )

            # Extract variables (combining defaults with provided inputs)
            variables = extract_input_variables(
                node,
                context.workflow_context.input_variables,
            )

            # Store variables in workflow context
            for name, value in variables.items():
                context.workflow_context.set_variable(name, value)

            context.emit_event("input_processed", {
                "variables": list(variables.keys()),
            })

            return NodeExecutionResult.success(
                node_id=node.id,
                output=variables,
                variable_count=len(variables),
            )

        except Exception as e:
            logger.exception("Input node %s execution failed", node.id)
            return NodeExecutionResult.error(
                node_id=node.id,
                error=str(e),
            )


class OutputNodeExecutor(BaseNodeExecutor):
    """Executor for output nodes.

    Output nodes collect and format the final results of a workflow.
    """

    node_type = "output"

    async def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        """Execute an output node.

        Resolves the output mapping and collects final results.
        """
        node = context.node

        try:
            # Get typed data
            typed_data = node.get_typed_data()
            if not isinstance(typed_data, OutputNodeData):
                return NodeExecutionResult.error(
                    node_id=node.id,
                    error="Node data is not OutputNodeData",
                )

            # Resolve output mapping
            resolver = InputResolver(context.workflow_context)
            output = {}

            for key, source_path in typed_data.output_mapping.items():
                value = resolver._resolve_path(source_path)
                output[key] = value

            context.emit_event("output_collected", {
                "keys": list(output.keys()),
            })

            return NodeExecutionResult.success(
                node_id=node.id,
                output=output,
                format=typed_data.format,
            )

        except Exception as e:
            logger.exception("Output node %s execution failed", node.id)
            return NodeExecutionResult.error(
                node_id=node.id,
                error=str(e),
            )


class TransformNodeExecutor(BaseNodeExecutor):
    """Executor for transform nodes.

    Transform nodes apply simple transformations to data
    without invoking an LLM.
    """

    node_type = "transform"

    async def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        """Execute a transform node."""
        node = context.node

        try:
            typed_data = node.get_typed_data()
            if not isinstance(typed_data, TransformNodeData):
                return NodeExecutionResult.error(
                    node_id=node.id,
                    error="Node data is not TransformNodeData",
                )

            resolver = InputResolver(context.workflow_context)

            if typed_data.transform_type == "template":
                # Template transformation
                template = typed_data.transform_config.get("template", "")
                output = resolver.resolve_template(template)

            elif typed_data.transform_type == "json_path":
                # JSON path extraction
                source = typed_data.transform_config.get("source", "")
                path = typed_data.transform_config.get("path", "")
                value = resolver._resolve_path(source)
                if value and path:
                    output = resolver._get_nested_value(value, path)
                else:
                    output = value

            elif typed_data.transform_type == "script":
                # Simple script transformation (limited for safety)
                # In production, this would use a sandboxed environment
                code = typed_data.transform_config.get("code", "output = input")
                input_value = typed_data.transform_config.get("input", "")
                resolved_input = resolver.resolve_template(str(input_value))

                # Simple eval with restricted globals
                safe_globals = {"__builtins__": {}}
                local_vars = {"input": resolved_input, "output": None}
                exec(code, safe_globals, local_vars)
                output = local_vars.get("output", resolved_input)

            else:
                return NodeExecutionResult.error(
                    node_id=node.id,
                    error=f"Unknown transform type: {typed_data.transform_type}",
                )

            return NodeExecutionResult.success(
                node_id=node.id,
                output=output,
            )

        except Exception as e:
            logger.exception("Transform node %s execution failed", node.id)
            return NodeExecutionResult.error(
                node_id=node.id,
                error=str(e),
            )


def register_simple_executors(registry) -> None:
    """Register all simple node executors with a registry.

    Args:
        registry: NodeExecutorRegistry to register with
    """
    registry.register("input", InputNodeExecutor())
    registry.register("output", OutputNodeExecutor())
    registry.register("transform", TransformNodeExecutor())
