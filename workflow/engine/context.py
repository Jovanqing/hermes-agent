"""
Context manager for workflow execution.

Manages the workflow context during execution:
- Variable storage and retrieval
- Node output accumulation
- Input variable handling
- Context snapshots for debugging
"""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from workflow.models import (
    NodeExecutionStatus,
    NodeOutput,
    WorkflowContext,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class ContextManager:
    """Manager for workflow execution context.

    Provides thread-safe access to the workflow context with
    change tracking and snapshot capabilities.

    Example:
        >>> manager = ContextManager(input_variables={"name": "World"})
        >>> manager.set_variable("greeting", "Hello!")
        >>> manager.record_output("node_1", NodeOutput(...))
        >>> context = manager.get_context()
    """

    def __init__(
        self,
        initial_context: Optional[WorkflowContext] = None,
        input_variables: Optional[Dict[str, Any]] = None,
        on_change: Optional[Callable[[str, Any], None]] = None,
    ):
        """Initialize the context manager.

        Args:
            initial_context: Optional pre-existing context
            input_variables: Variables provided at execution start
            on_change: Optional callback for context changes
        """
        if initial_context:
            self._context = initial_context
        else:
            self._context = WorkflowContext()

        # Set input variables
        if input_variables:
            self._context.input_variables.update(input_variables)

        self._on_change = on_change
        self._snapshots: List[Dict[str, Any]] = []
        self._change_log: List[Dict[str, Any]] = []

    @property
    def context(self) -> WorkflowContext:
        """Get the current context."""
        return self._context

    # -----------------------------------------------------------------------
    # Variable operations
    # -----------------------------------------------------------------------

    def get_variable(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """Get a context variable.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            The variable value or default
        """
        return self._context.variables.get(name, default)

    def set_variable(
        self,
        name: str,
        value: Any,
        source: str = "user",
    ) -> None:
        """Set a context variable.

        Args:
            name: Variable name
            value: Variable value
            source: Source of the variable (for tracking)
        """
        old_value = self._context.variables.get(name)
        self._context.variables[name] = value

        self._log_change("set_variable", {
            "name": name,
            "old_value": old_value,
            "new_value": value,
            "source": source,
        })

        if self._on_change:
            self._on_change("variable", {"name": name, "value": value})

    def get_variables(self) -> Dict[str, Any]:
        """Get all context variables."""
        return dict(self._context.variables)

    def update_variables(
        self,
        variables: Dict[str, Any],
        source: str = "bulk",
    ) -> None:
        """Update multiple variables at once.

        Args:
            variables: Dict of variable name -> value
            source: Source of the variables
        """
        for name, value in variables.items():
            self.set_variable(name, value, source=source)

    # -----------------------------------------------------------------------
    # Input variable operations
    # -----------------------------------------------------------------------

    def get_input_variable(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """Get an input variable.

        Args:
            name: Variable name (without 'input.' prefix)
            default: Default value if not found

        Returns:
            The variable value or default
        """
        return self._context.input_variables.get(name, default)

    def set_input_variable(self, name: str, value: Any) -> None:
        """Set an input variable.

        Args:
            name: Variable name
            value: Variable value
        """
        self._context.input_variables[name] = value

    def get_input_variables(self) -> Dict[str, Any]:
        """Get all input variables."""
        return dict(self._context.input_variables)

    # -----------------------------------------------------------------------
    # Node output operations
    # -----------------------------------------------------------------------

    def get_node_output(self, node_id: str) -> Optional[NodeOutput]:
        """Get the output of a specific node.

        Args:
            node_id: The node ID

        Returns:
            NodeOutput if the node has executed, None otherwise
        """
        return self._context.node_outputs.get(node_id)

    def record_output(
        self,
        node_id: str,
        output: NodeOutput,
    ) -> None:
        """Record a node's output.

        Args:
            node_id: The node ID
            output: The node output
        """
        self._context.node_outputs[node_id] = output

        # Add to execution history if successful
        if output.status == NodeExecutionStatus.SUCCESS:
            if node_id not in self._context.execution_history:
                self._context.execution_history.append(node_id)

        self._log_change("record_output", {
            "node_id": node_id,
            "status": output.status.value,
            "output_preview": str(output.output)[:100] if output.output else None,
        })

        if self._on_change:
            self._on_change("node_output", {
                "node_id": node_id,
                "output": output,
            })

    def record_success(
        self,
        node_id: str,
        output: Any,
        tokens: Optional[Dict[str, int]] = None,
        duration: float = 0.0,
    ) -> NodeOutput:
        """Record a successful node execution.

        Args:
            node_id: The node ID
            output: The output data
            tokens: Token usage statistics
            duration: Execution duration in seconds

        Returns:
            The created NodeOutput
        """
        node_output = NodeOutput(
            node_id=node_id,
            output=output,
            tokens=tokens or {"prompt": 0, "completion": 0},
            duration=duration,
            status=NodeExecutionStatus.SUCCESS,
            completed_at=datetime.now(),
        )
        self.record_output(node_id, node_output)
        return node_output

    def record_error(
        self,
        node_id: str,
        error: str,
        duration: float = 0.0,
    ) -> NodeOutput:
        """Record a failed node execution.

        Args:
            node_id: The node ID
            error: Error message
            duration: Execution duration in seconds

        Returns:
            The created NodeOutput
        """
        node_output = NodeOutput(
            node_id=node_id,
            output=None,
            duration=duration,
            status=NodeExecutionStatus.ERROR,
            error=error,
            completed_at=datetime.now(),
        )
        self.record_output(node_id, node_output)
        return node_output

    def record_skipped(
        self,
        node_id: str,
        reason: str = "",
    ) -> NodeOutput:
        """Record a skipped node.

        Args:
            node_id: The node ID
            reason: Reason for skipping

        Returns:
            The created NodeOutput
        """
        node_output = NodeOutput(
            node_id=node_id,
            output=None,
            status=NodeExecutionStatus.SKIPPED,
            error=reason if reason else None,
            completed_at=datetime.now(),
        )
        self.record_output(node_id, node_output)
        return node_output

    def get_completed_nodes(self) -> List[str]:
        """Get list of completed node IDs."""
        return list(self._context.execution_history)

    def get_all_outputs(self) -> Dict[str, NodeOutput]:
        """Get all node outputs."""
        return dict(self._context.node_outputs)

    # -----------------------------------------------------------------------
    # Resolution helpers
    # -----------------------------------------------------------------------

    def resolve_path(self, path: str) -> Any:
        """Resolve a variable path to its value.

        Supports:
        - Simple variables: "name"
        - Input variables: "input.name"
        - Node outputs: "node_id.output"
        - Nested fields: "node_id.output.field"

        Args:
            path: The path to resolve

        Returns:
            The resolved value or None
        """
        # Check simple variables
        if path in self._context.variables:
            return self._context.variables[path]

        # Check input variables
        if path.startswith("input."):
            var_name = path[6:]
            return self._context.input_variables.get(var_name)

        # Check node outputs
        if "." in path:
            parts = path.split(".", 1)
            node_id = parts[0]
            field_path = parts[1]

            node_output = self._context.node_outputs.get(node_id)
            if node_output:
                if field_path == "output":
                    return node_output.output
                if field_path == "status":
                    return node_output.status.value
                if field_path == "duration":
                    return node_output.duration
                if field_path.startswith("output."):
                    # Nested field access
                    remaining = field_path[7:]
                    return self._get_nested(node_output.output, remaining)

        # Direct node output reference
        if path in self._context.node_outputs:
            return self._context.node_outputs[path].output

        return None

    def _get_nested(self, obj: Any, path: str) -> Any:
        """Get a nested value using dot notation."""
        parts = path.split(".")
        current = obj

        for part in parts:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    # -----------------------------------------------------------------------
    # Snapshot and history
    # -----------------------------------------------------------------------

    def create_snapshot(self, label: str = "") -> Dict[str, Any]:
        """Create a snapshot of the current context.

        Args:
            label: Optional label for the snapshot

        Returns:
            The snapshot data
        """
        snapshot = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "variables": copy.deepcopy(self._context.variables),
            "input_variables": copy.deepcopy(self._context.input_variables),
            "node_outputs": {
                k: v.to_dict() for k, v in self._context.node_outputs.items()
            },
            "execution_history": list(self._context.execution_history),
        }
        self._snapshots.append(snapshot)
        return snapshot

    def get_snapshots(self) -> List[Dict[str, Any]]:
        """Get all snapshots."""
        return list(self._snapshots)

    def get_change_log(self) -> List[Dict[str, Any]]:
        """Get the change log."""
        return list(self._change_log)

    def _log_change(self, change_type: str, data: Dict[str, Any]) -> None:
        """Log a context change."""
        self._change_log.append({
            "type": change_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        })

    # -----------------------------------------------------------------------
    # Context export
    # -----------------------------------------------------------------------

    def get_context(self) -> WorkflowContext:
        """Get a copy of the current context."""
        return WorkflowContext(
            variables=dict(self._context.variables),
            node_outputs=dict(self._context.node_outputs),
            execution_history=list(self._context.execution_history),
            input_variables=dict(self._context.input_variables),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Export context as a dictionary."""
        return self._context.to_dict()

    def to_json(self, indent: int = 2) -> str:
        """Export context as JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    # -----------------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Get context statistics.

        Returns:
            Dict with execution statistics
        """
        outputs = list(self._context.node_outputs.values())

        total_tokens = {"prompt": 0, "completion": 0}
        total_duration = 0.0
        success_count = 0
        error_count = 0
        skipped_count = 0

        for output in outputs:
            if output.tokens:
                total_tokens["prompt"] += output.tokens.get("prompt", 0)
                total_tokens["completion"] += output.tokens.get("completion", 0)
            total_duration += output.duration

            if output.status == NodeExecutionStatus.SUCCESS:
                success_count += 1
            elif output.status == NodeExecutionStatus.ERROR:
                error_count += 1
            elif output.status == NodeExecutionStatus.SKIPPED:
                skipped_count += 1

        return {
            "nodes_executed": len(outputs),
            "nodes_successful": success_count,
            "nodes_failed": error_count,
            "nodes_skipped": skipped_count,
            "total_tokens": total_tokens,
            "total_duration_seconds": total_duration,
            "variables_count": len(self._context.variables),
        }
