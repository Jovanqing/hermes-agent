"""
Base classes for workflow node executors.

Defines the interface and common functionality for all node executors.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

from workflow.models import (
    NodeExecutionStatus,
    NodeOutput,
    WorkflowContext,
    WorkflowNode,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Execution context
# ---------------------------------------------------------------------------


@dataclass
class ExecutionContext:
    """Context passed to node executors during execution.

    Provides access to workflow state, input variables, and callbacks
    for streaming output.

    Attributes:
        workflow_context: The shared workflow context with variables and outputs
        node: The node being executed
        execution_id: Unique ID for this execution
        on_token: Callback for streaming tokens
        on_event: Callback for execution events
        cancel_requested: Flag to check for cancellation
    """

    workflow_context: WorkflowContext
    node: WorkflowNode
    execution_id: str
    on_token: Optional[Callable[[str], None]] = None
    on_event: Optional[Callable[[str, Any], None]] = None
    cancel_requested: bool = False

    def emit_token(self, token: str) -> None:
        """Emit a streaming token."""
        if self.on_token:
            self.on_token(token)

    def emit_event(self, event_type: str, data: Any = None) -> None:
        """Emit an execution event."""
        if self.on_event:
            self.on_event(event_type, data)

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self.cancel_requested


# ---------------------------------------------------------------------------
# Execution result
# ---------------------------------------------------------------------------


@dataclass
class NodeExecutionResult:
    """Result of executing a single node.

    Attributes:
        node_id: ID of the executed node
        output: The output data
        tokens: Token usage statistics
        duration: Execution time in seconds
        status: Execution status
        error: Error message if failed
        metadata: Additional result metadata
    """

    node_id: str
    output: Any
    tokens: Dict[str, int] = field(default_factory=lambda: {"prompt": 0, "completion": 0})
    duration: float = 0.0
    status: NodeExecutionStatus = NodeExecutionStatus.SUCCESS
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_node_output(self) -> NodeOutput:
        """Convert to a NodeOutput for storage in context."""
        return NodeOutput(
            node_id=self.node_id,
            output=self.output,
            tokens=self.tokens,
            duration=self.duration,
            status=self.status,
            error=self.error,
        )

    @classmethod
    def success(
        cls,
        node_id: str,
        output: Any,
        tokens: Optional[Dict[str, int]] = None,
        duration: float = 0.0,
        **metadata: Any,
    ) -> NodeExecutionResult:
        """Create a successful result."""
        return cls(
            node_id=node_id,
            output=output,
            tokens=tokens or {"prompt": 0, "completion": 0},
            duration=duration,
            status=NodeExecutionStatus.SUCCESS,
            metadata=metadata,
        )

    @classmethod
    def error(
        cls,
        node_id: str,
        error: str,
        duration: float = 0.0,
    ) -> NodeExecutionResult:
        """Create an error result."""
        return cls(
            node_id=node_id,
            output=None,
            duration=duration,
            status=NodeExecutionStatus.ERROR,
            error=error,
        )

    @classmethod
    def skipped(cls, node_id: str, reason: str = "") -> NodeExecutionResult:
        """Create a skipped result."""
        return cls(
            node_id=node_id,
            output=None,
            status=NodeExecutionStatus.SKIPPED,
            error=reason if reason else None,
        )


# ---------------------------------------------------------------------------
# Base node executor
# ---------------------------------------------------------------------------


class BaseNodeExecutor(ABC):
    """Abstract base class for node executors.

    Subclasses must implement execute() and may optionally implement
    execute_stream() for streaming support.

    Attributes:
        node_type: The type of node this executor handles
    """

    node_type: str = "base"

    def __init__(self, **kwargs: Any):
        """Initialize the executor with optional configuration."""
        self.config = kwargs

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        """Execute the node and return the result.

        Args:
            context: Execution context with workflow state and callbacks

        Returns:
            NodeExecutionResult with output and metadata

        Raises:
            Exception: If execution fails
        """
        pass

    async def execute_stream(
        self,
        context: ExecutionContext,
    ) -> AsyncIterator[Union[str, NodeExecutionResult]]:
        """Execute the node with streaming output.

        Yields tokens as they are generated, then yields the final
        NodeExecutionResult.

        Default implementation calls execute() and yields the result.
        Subclasses should override for true streaming support.

        Args:
            context: Execution context with workflow state and callbacks

        Yields:
            str: Individual tokens as they are generated
            NodeExecutionResult: Final result at the end
        """
        result = await self.execute(context)
        yield result

    async def execute_with_retry(
        self,
        context: ExecutionContext,
    ) -> NodeExecutionResult:
        """Execute with retry logic based on node configuration.

        Uses the retry policy from the node's config to handle failures.

        Args:
            context: Execution context

        Returns:
            NodeExecutionResult (may be from a retry)
        """
        from workflow.exceptions import NodeExecutionError

        retry_policy = context.node.config.retry_policy
        max_retries = retry_policy.max_retries
        delay = retry_policy.delay_seconds
        exponential = retry_policy.exponential_backoff

        last_error: Optional[Exception] = None
        attempt = 0

        while attempt <= max_retries:
            try:
                # Check for cancellation
                if context.is_cancelled():
                    return NodeExecutionResult.error(
                        node_id=context.node.id,
                        error="Execution cancelled",
                    )

                # Execute
                result = await self.execute(context)

                # If successful, return
                if result.status == NodeExecutionStatus.SUCCESS:
                    return result

                # If skipped, don't retry
                if result.status == NodeExecutionStatus.SKIPPED:
                    return result

                # Otherwise, it's an error - prepare to retry
                last_error = Exception(result.error or "Unknown error")

            except Exception as e:
                last_error = e
                logger.warning(
                    "Node %s execution failed (attempt %d/%d): %s",
                    context.node.id,
                    attempt + 1,
                    max_retries + 1,
                    str(e),
                )

            # Check if we should retry
            if attempt < max_retries:
                # Check retry_on_errors filter
                if retry_policy.retry_on_errors:
                    error_type = type(last_error).__name__ if last_error else ""
                    if error_type not in retry_policy.retry_on_errors:
                        break

                # Wait before retry
                wait_time = delay * (2 ** attempt if exponential else 1)
                logger.info(
                    "Retrying node %s in %.1f seconds...",
                    context.node.id,
                    wait_time,
                )
                context.emit_event("retry", {
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "delay": wait_time,
                })

                # Sleep with cancellation check
                import asyncio
                for _ in range(int(wait_time * 10)):
                    if context.is_cancelled():
                        return NodeExecutionResult.error(
                            node_id=context.node.id,
                            error="Execution cancelled during retry",
                        )
                    await asyncio.sleep(0.1)

            attempt += 1

        # All retries exhausted
        error_msg = str(last_error) if last_error else "Unknown error"
        return NodeExecutionResult.error(
            node_id=context.node.id,
            error=f"Failed after {attempt} attempts: {error_msg}",
            duration=0.0,
        )

    async def execute_with_timeout(
        self,
        context: ExecutionContext,
    ) -> NodeExecutionResult:
        """Execute with timeout based on node configuration.

        Args:
            context: Execution context

        Returns:
            NodeExecutionResult (may be timeout error)
        """
        import asyncio

        timeout = context.node.config.timeout

        try:
            result = await asyncio.wait_for(
                self.execute_with_retry(context),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.error(
                "Node %s timed out after %.1f seconds",
                context.node.id,
                timeout,
            )
            return NodeExecutionResult.error(
                node_id=context.node.id,
                error=f"Execution timed out after {timeout}s",
            )

    def validate_node(self, node: WorkflowNode) -> List[str]:
        """Validate that the node is compatible with this executor.

        Args:
            node: The node to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if node.type.value != self.node_type:
            errors.append(
                f"Node type '{node.type.value}' does not match "
                f"executor type '{self.node_type}'"
            )

        return errors


# ---------------------------------------------------------------------------
# Node executor registry
# ---------------------------------------------------------------------------


class NodeExecutorRegistry:
    """Registry for node executors.

    Maps node types to their executor classes.
    """

    def __init__(self):
        self._executors: Dict[str, BaseNodeExecutor] = {}

    def register(
        self,
        node_type: str,
        executor: BaseNodeExecutor,
    ) -> None:
        """Register an executor for a node type.

        Args:
            node_type: The node type to handle
            executor: The executor instance
        """
        self._executors[node_type] = executor
        logger.debug("Registered executor for node type: %s", node_type)

    def get_executor(self, node_type: str) -> Optional[BaseNodeExecutor]:
        """Get the executor for a node type.

        Args:
            node_type: The node type

        Returns:
            The executor instance, or None if not registered
        """
        return self._executors.get(node_type)

    def execute_node(
        self,
        context: ExecutionContext,
    ) -> NodeExecutionResult:
        """Get the appropriate executor for a node.

        Args:
            context: Execution context containing the node

        Returns:
            The executor for the node's type

        Raises:
            ValueError: If no executor is registered for the node type
        """
        executor = self.get_executor(context.node.type.value)
        if executor is None:
            raise ValueError(
                f"No executor registered for node type: {context.node.type.value}"
            )
        return executor


# Global registry instance
_default_registry: Optional[NodeExecutorRegistry] = None


def get_default_registry() -> NodeExecutorRegistry:
    """Get the default node executor registry.

    Returns:
        The global NodeExecutorRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = NodeExecutorRegistry()

        # Register default executors
        from workflow.nodes.agent_node import AgentNodeExecutor
        from workflow.nodes.simple_nodes import register_simple_executors

        _default_registry.register("agent", AgentNodeExecutor())
        register_simple_executors(_default_registry)

    return _default_registry
