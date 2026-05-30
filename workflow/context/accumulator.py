"""
Context accumulator for workflow execution.

Builds and maintains the execution context as nodes complete:
- Tracks variables from input nodes
- Stores node outputs with metadata
- Provides context snapshots for debugging
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from workflow.models import (
    NodeOutput,
    WorkflowContext,
    NodeExecutionStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context snapshot
# ---------------------------------------------------------------------------


@dataclass
class ContextSnapshot:
    """A point-in-time snapshot of the workflow context.

    Useful for debugging and replaying executions.

    Attributes:
        id: Unique snapshot identifier
        label: Human-readable label
        timestamp: When the snapshot was taken
        variables: Context variables at snapshot time
        node_outputs: Node outputs at snapshot time
        execution_history: Completed nodes at snapshot time
        metadata: Additional snapshot metadata
    """

    id: str
    label: str
    timestamp: datetime = field(default_factory=datetime.now)
    variables: Dict[str, Any] = field(default_factory=dict)
    node_outputs: Dict[str, NodeOutput] = field(default_factory=dict)
    execution_history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "id": self.id,
            "label": self.label,
            "timestamp": self.timestamp.isoformat(),
            "variables": self._serialize_value(self.variables),
            "node_outputs": {
                k: v.to_dict() for k, v in self.node_outputs.items()
            },
            "execution_history": self.execution_history,
            "metadata": self.metadata,
        }

    def _serialize_value(self, value: Any) -> Any:
        """Recursively serialize a value."""
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return value


# ---------------------------------------------------------------------------
# Context accumulator
# ---------------------------------------------------------------------------


class ContextAccumulator:
    """Accumulates workflow context during execution.

    Provides:
    - Variable storage and retrieval
    - Node output tracking
    - Snapshot creation for debugging
    - Context diffing between snapshots

    Example:
        >>> accumulator = ContextAccumulator()
        >>> accumulator.set_variable("name", "World")
        >>> accumulator.record_node_output("node_1", NodeOutput(...))
        >>> snapshot = accumulator.create_snapshot("after_node_1")
    """

    def __init__(
        self,
        initial_context: Optional[WorkflowContext] = None,
    ):
        """Initialize the accumulator.

        Args:
            initial_context: Optional pre-existing context to start from
        """
        if initial_context:
            self._context = WorkflowContext(
                variables=dict(initial_context.variables),
                node_outputs=dict(initial_context.node_outputs),
                execution_history=list(initial_context.execution_history),
                input_variables=dict(initial_context.input_variables),
            )
        else:
            self._context = WorkflowContext()

        self._snapshots: List[ContextSnapshot] = []
        self._change_log: List[Dict[str, Any]] = []
        self._snapshot_counter = 0

    # -----------------------------------------------------------------------
    # Context access
    # -----------------------------------------------------------------------

    @property
    def context(self) -> WorkflowContext:
        """Get the current workflow context."""
        return self._context

    @property
    def variables(self) -> Dict[str, Any]:
        """Get all context variables."""
        return self._context.variables

    @property
    def node_outputs(self) -> Dict[str, NodeOutput]:
        """Get all node outputs."""
        return self._context.node_outputs

    @property
    def execution_history(self) -> List[str]:
        """Get the execution history."""
        return list(self._context.execution_history)

    # -----------------------------------------------------------------------
    # Variable management
    # -----------------------------------------------------------------------

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
            "old_value": self._truncate(old_value),
            "new_value": self._truncate(value),
            "source": source,
        })

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

    def clear_variables(self) -> None:
        """Clear all context variables."""
        self._context.variables.clear()
        self._log_change("clear_variables", {})

    # -----------------------------------------------------------------------
    # Input variable management
    # -----------------------------------------------------------------------

    def set_input_variable(self, name: str, value: Any) -> None:
        """Set an input variable.

        Args:
            name: Variable name
            value: Variable value
        """
        self._context.input_variables[name] = value

    def get_input_variable(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """Get an input variable.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            The variable value or default
        """
        return self._context.input_variables.get(name, default)

    def set_input_variables(self, variables: Dict[str, Any]) -> None:
        """Set multiple input variables.

        Args:
            variables: Dict of variable name -> value
        """
        self._context.input_variables.update(variables)

    # -----------------------------------------------------------------------
    # Node output management
    # -----------------------------------------------------------------------

    def record_node_output(
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
            "output_preview": self._truncate(output.output),
        })

    def get_node_output(self, node_id: str) -> Optional[NodeOutput]:
        """Get a node's output.

        Args:
            node_id: The node ID

        Returns:
            NodeOutput if found, None otherwise
        """
        return self._context.node_outputs.get(node_id)

    def get_completed_nodes(self) -> List[str]:
        """Get list of completed node IDs."""
        return list(self._context.execution_history)

    def is_node_completed(self, node_id: str) -> bool:
        """Check if a node has been completed.

        Args:
            node_id: The node ID

        Returns:
            True if completed
        """
        return node_id in self._context.execution_history

    # -----------------------------------------------------------------------
    # Value resolution
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
                if field_path == "tokens":
                    return node_output.tokens
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
    # Snapshots
    # -----------------------------------------------------------------------

    def create_snapshot(
        self,
        label: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextSnapshot:
        """Create a snapshot of the current context.

        Args:
            label: Human-readable label for the snapshot
            metadata: Additional metadata to include

        Returns:
            The created ContextSnapshot
        """
        self._snapshot_counter += 1
        snapshot_id = f"snapshot-{self._snapshot_counter}"

        snapshot = ContextSnapshot(
            id=snapshot_id,
            label=label,
            variables=copy.deepcopy(self._context.variables),
            node_outputs=copy.deepcopy(self._context.node_outputs),
            execution_history=list(self._context.execution_history),
            metadata=metadata or {},
        )

        self._snapshots.append(snapshot)
        logger.debug("Created context snapshot: %s", label)

        return snapshot

    def get_snapshots(self) -> List[ContextSnapshot]:
        """Get all snapshots."""
        return list(self._snapshots)

    def get_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Get a snapshot by ID.

        Args:
            snapshot_id: The snapshot ID

        Returns:
            ContextSnapshot if found, None otherwise
        """
        for snapshot in self._snapshots:
            if snapshot.id == snapshot_id:
                return snapshot
        return None

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore context from a snapshot.

        Args:
            snapshot_id: The snapshot ID

        Returns:
            True if restored successfully
        """
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            return False

        self._context.variables = copy.deepcopy(snapshot.variables)
        self._context.node_outputs = copy.deepcopy(snapshot.node_outputs)
        self._context.execution_history = list(snapshot.execution_history)

        self._log_change("restore_snapshot", {
            "snapshot_id": snapshot_id,
            "label": snapshot.label,
        })

        logger.info("Restored context from snapshot: %s", snapshot.label)
        return True

    def diff_snapshots(
        self,
        snapshot_a_id: str,
        snapshot_b_id: str,
    ) -> Dict[str, Any]:
        """Compare two snapshots and return the differences.

        Args:
            snapshot_a_id: First snapshot ID
            snapshot_b_id: Second snapshot ID

        Returns:
            Dict describing the differences
        """
        snapshot_a = self.get_snapshot(snapshot_a_id)
        snapshot_b = self.get_snapshot(snapshot_b_id)

        if not snapshot_a or not snapshot_b:
            return {"error": "One or both snapshots not found"}

        diff: Dict[str, Any] = {
            "variables": {
                "added": [],
                "removed": [],
                "changed": [],
            },
            "node_outputs": {
                "added": [],
                "removed": [],
            },
            "execution_history": {
                "new_nodes": [],
            },
        }

        # Compare variables
        keys_a = set(snapshot_a.variables.keys())
        keys_b = set(snapshot_b.variables.keys())

        diff["variables"]["added"] = list(keys_b - keys_a)
        diff["variables"]["removed"] = list(keys_a - keys_b)

        for key in keys_a & keys_b:
            if snapshot_a.variables[key] != snapshot_b.variables[key]:
                diff["variables"]["changed"].append(key)

        # Compare node outputs
        nodes_a = set(snapshot_a.node_outputs.keys())
        nodes_b = set(snapshot_b.node_outputs.keys())

        diff["node_outputs"]["added"] = list(nodes_b - nodes_a)
        diff["node_outputs"]["removed"] = list(nodes_a - nodes_b)

        # Compare execution history
        history_a = set(snapshot_a.execution_history)
        history_b = set(snapshot_b.execution_history)

        diff["execution_history"]["new_nodes"] = list(history_b - history_a)

        return diff

    # -----------------------------------------------------------------------
    # Change log
    # -----------------------------------------------------------------------

    def get_change_log(self) -> List[Dict[str, Any]]:
        """Get the change log."""
        return list(self._change_log)

    def clear_change_log(self) -> None:
        """Clear the change log."""
        self._change_log.clear()

    def _log_change(self, change_type: str, data: Dict[str, Any]) -> None:
        """Log a context change."""
        self._change_log.append({
            "type": change_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        })

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
            "snapshots_count": len(self._snapshots),
        }

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Export context as a dictionary."""
        return self._context.to_dict()

    def to_json(self, indent: int = 2) -> str:
        """Export context as JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _truncate(self, value: Any, max_length: int = 100) -> Any:
        """Truncate a value for logging."""
        if value is None:
            return None
        if isinstance(value, str) and len(value) > max_length:
            return value[:max_length] + "..."
        if isinstance(value, (dict, list)):
            s = json.dumps(value)
            if len(s) > max_length:
                return s[:max_length] + "..."
        return value
