"""
Custom exceptions for the Workflow Management System.

Provides a hierarchy of exceptions for different error conditions:
- WorkflowError: Base exception for all workflow errors
- WorkflowNotFoundError: Workflow does not exist
- WorkflowValidationError: Invalid workflow definition
- WorkflowExecutionError: Error during workflow execution
- NodeExecutionError: Error executing a specific node
- CycleDetectedError: Workflow graph contains cycles
"""

from __future__ import annotations

from typing import Any, Optional


class WorkflowError(Exception):
    """Base exception for all workflow-related errors.

    Attributes:
        message: Human-readable error description
        details: Optional additional error context
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a serializable dictionary."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow with the specified ID does not exist."""

    def __init__(self, workflow_id: str):
        super().__init__(
            message=f"Workflow not found: {workflow_id}",
            details={"workflow_id": workflow_id},
        )
        self.workflow_id = workflow_id


class WorkflowExecutionNotFoundError(WorkflowError):
    """Raised when a workflow execution with the specified ID does not exist."""

    def __init__(self, execution_id: str):
        super().__init__(
            message=f"Workflow execution not found: {execution_id}",
            details={"execution_id": execution_id},
        )
        self.execution_id = execution_id


class WorkflowValidationError(WorkflowError):
    """Raised when a workflow definition is invalid.

    This can occur when:
    - The workflow graph contains cycles
    - Required nodes are missing
    - Node configurations are invalid
    - Edges reference non-existent nodes
    """

    def __init__(
        self,
        message: str,
        errors: Optional[list[dict[str, Any]]] = None,
    ):
        super().__init__(
            message=message,
            details={"validation_errors": errors or []},
        )
        self.errors = errors or []


class CycleDetectedError(WorkflowValidationError):
    """Raised when the workflow graph contains a cycle.

    Workflow graphs must be directed acyclic graphs (DAGs).
    Cycles would cause infinite execution loops.

    Attributes:
        cycle: List of node IDs forming the cycle
    """

    def __init__(self, cycle: list[str]):
        cycle_str = " -> ".join(cycle)
        super().__init__(
            message=f"Cycle detected in workflow graph: {cycle_str}",
            errors=[{
                "type": "cycle",
                "nodes": cycle,
            }],
        )
        self.cycle = cycle


class InvalidNodeError(WorkflowValidationError):
    """Raised when a node has invalid configuration."""

    def __init__(
        self,
        node_id: str,
        reason: str,
    ):
        super().__init__(
            message=f"Invalid node '{node_id}': {reason}",
            errors=[{
                "type": "invalid_node",
                "node_id": node_id,
                "reason": reason,
            }],
        )
        self.node_id = node_id
        self.reason = reason


class InvalidEdgeError(WorkflowValidationError):
    """Raised when an edge references non-existent nodes."""

    def __init__(
        self,
        edge_id: str,
        reason: str,
    ):
        super().__init__(
            message=f"Invalid edge '{edge_id}': {reason}",
            errors=[{
                "type": "invalid_edge",
                "edge_id": edge_id,
                "reason": reason,
            }],
        )
        self.edge_id = edge_id
        self.reason = reason


class MissingEntryNodeError(WorkflowValidationError):
    """Raised when a workflow has no entry nodes (nodes without incoming edges)."""

    def __init__(self):
        super().__init__(
            message="Workflow must have at least one entry node (node without incoming edges)",
            errors=[{"type": "missing_entry_node"}],
        )


class WorkflowExecutionError(WorkflowError):
    """Raised when an error occurs during workflow execution.

    Attributes:
        workflow_id: ID of the workflow being executed
        execution_id: ID of the execution that failed
    """

    def __init__(
        self,
        message: str,
        workflow_id: str,
        execution_id: str,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            details={
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "cause": str(cause) if cause else None,
            },
        )
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.cause = cause


class NodeExecutionError(WorkflowExecutionError):
    """Raised when a specific node fails during execution.

    Attributes:
        node_id: ID of the node that failed
        retry_count: Number of retries attempted
    """

    def __init__(
        self,
        message: str,
        workflow_id: str,
        execution_id: str,
        node_id: str,
        retry_count: int = 0,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"Node '{node_id}' failed: {message}",
            workflow_id=workflow_id,
            execution_id=execution_id,
            cause=cause,
        )
        self.details["node_id"] = node_id
        self.details["retry_count"] = retry_count
        self.node_id = node_id
        self.retry_count = retry_count


class NodeTimeoutError(NodeExecutionError):
    """Raised when a node exceeds its configured timeout."""

    def __init__(
        self,
        workflow_id: str,
        execution_id: str,
        node_id: str,
        timeout_seconds: float,
    ):
        super().__init__(
            message=f"Node timed out after {timeout_seconds}s",
            workflow_id=workflow_id,
            execution_id=execution_id,
            node_id=node_id,
        )
        self.details["timeout_seconds"] = timeout_seconds
        self.timeout_seconds = timeout_seconds


class ContextResolutionError(WorkflowExecutionError):
    """Raised when context variable resolution fails.

    This can occur when:
    - A referenced node output doesn't exist
    - A variable is not defined in the context
    - The input mapping is invalid
    """

    def __init__(
        self,
        message: str,
        workflow_id: str,
        execution_id: str,
        node_id: str,
        variable: str,
    ):
        super().__init__(
            message=f"Failed to resolve context for node '{node_id}': {message}",
            workflow_id=workflow_id,
            execution_id=execution_id,
        )
        self.details["node_id"] = node_id
        self.details["variable"] = variable
        self.node_id = node_id
        self.variable = variable


class ExecutionStateError(WorkflowExecutionError):
    """Raised when an invalid state transition is attempted.

    For example, trying to resume an execution that is not paused.
    """

    def __init__(
        self,
        message: str,
        execution_id: str,
        current_state: str,
    ):
        super().__init__(
            message=message,
            workflow_id="",
            execution_id=execution_id,
        )
        self.details["current_state"] = current_state
        self.current_state = current_state


class BreakpointReachedError(WorkflowError):
    """Raised (or signaled) when execution hits a breakpoint.

    This is not truly an error but a control flow signal indicating
    that execution should pause for human inspection.

    Attributes:
        execution_id: ID of the paused execution
        node_id: ID of the node with the breakpoint
    """

    def __init__(
        self,
        execution_id: str,
        node_id: str,
    ):
        super().__init__(
            message=f"Breakpoint reached at node '{node_id}'",
            details={
                "execution_id": execution_id,
                "node_id": node_id,
            },
        )
        self.execution_id = execution_id
        self.node_id = node_id


class ConditionEvaluationError(WorkflowExecutionError):
    """Raised when a branch condition fails to evaluate.

    Attributes:
        node_id: ID of the branch node
        condition_id: ID of the failing condition
    """

    def __init__(
        self,
        message: str,
        workflow_id: str,
        execution_id: str,
        node_id: str,
        condition_id: str,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"Condition evaluation failed for node '{node_id}': {message}",
            workflow_id=workflow_id,
            execution_id=execution_id,
            cause=cause,
        )
        self.details["node_id"] = node_id
        self.details["condition_id"] = condition_id
        self.node_id = node_id
        self.condition_id = condition_id


class WorkflowCancelledError(WorkflowExecutionError):
    """Raised when a workflow execution is cancelled."""

    def __init__(
        self,
        workflow_id: str,
        execution_id: str,
        reason: str = "User cancelled",
    ):
        super().__init__(
            message=f"Workflow execution cancelled: {reason}",
            workflow_id=workflow_id,
            execution_id=execution_id,
        )
        self.details["reason"] = reason
        self.reason = reason


# ---------------------------------------------------------------------------
# Error utilities
# ---------------------------------------------------------------------------


def wrap_exception(
    exc: Exception,
    workflow_id: str = "",
    execution_id: str = "",
    node_id: str = "",
) -> WorkflowError:
    """Wrap an arbitrary exception in a WorkflowError.

    Useful for converting unexpected exceptions into workflow-specific
    errors that can be properly handled and displayed.
    """
    if isinstance(exc, WorkflowError):
        return exc

    message = str(exc) or exc.__class__.__name__

    if node_id and execution_id:
        return NodeExecutionError(
            message=message,
            workflow_id=workflow_id,
            execution_id=execution_id,
            node_id=node_id,
            cause=exc,
        )
    elif execution_id:
        return WorkflowExecutionError(
            message=message,
            workflow_id=workflow_id,
            execution_id=execution_id,
            cause=exc,
        )
    else:
        return WorkflowError(message=message, details={"cause": str(exc)})
