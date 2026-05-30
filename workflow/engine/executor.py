"""
Main workflow executor.

Orchestrates workflow execution by:
1. Validating the workflow
2. Initializing state machine and context
3. Scheduling and executing nodes
4. Handling errors and retries
5. Emitting events for monitoring
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Union

from workflow.engine.context import ContextManager
from workflow.engine.scheduler import NodeScheduler, SchedulingResult
from workflow.engine.state_machine import (
    ExecutionStateContainer,
    InvalidStateTransition,
    StateMachine,
)
from workflow.exceptions import (
    BreakpointReachedError,
    NodeExecutionError,
    WorkflowCancelledError,
    WorkflowExecutionError,
    WorkflowValidationError,
    wrap_exception,
)
from workflow.models import (
    ExecutionState,
    NodeType,
    NodeOutput,
    Workflow,
    WorkflowContext,
    WorkflowExecution,
    WorkflowNode,
)
from workflow.nodes.base import (
    BaseNodeExecutor,
    ExecutionContext,
    NodeExecutionResult,
    NodeExecutorRegistry,
    get_default_registry,
)
from workflow.validation import validate_workflow_or_raise

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Types of execution events."""

    # Workflow lifecycle
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"

    # Node lifecycle
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    NODE_SKIPPED = "node_skipped"

    # Streaming
    TOKEN = "token"

    # Control flow
    BREAKPOINT = "breakpoint"
    WAITING_INPUT = "waiting_input"
    INPUT_RECEIVED = "input_received"

    # State changes
    STATE_CHANGED = "state_changed"


@dataclass
class ExecutionEvent:
    """An event emitted during execution.

    Attributes:
        type: Event type
        execution_id: The execution ID
        timestamp: When the event occurred
        data: Event-specific data
    """

    type: EventType
    execution_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# ---------------------------------------------------------------------------
# Execution configuration
# ---------------------------------------------------------------------------


@dataclass
class ExecutionConfig:
    """Configuration for workflow execution.

    Attributes:
        validate_before_execution: Whether to validate the workflow
        stop_on_error: Whether to stop on first error
        max_parallel_nodes: Maximum nodes to execute in parallel
        default_timeout: Default node timeout in seconds
        create_snapshots: Whether to create context snapshots
        event_callbacks: List of event callback functions
    """

    validate_before_execution: bool = True
    stop_on_error: bool = True
    max_parallel_nodes: int = 10
    default_timeout: float = 300.0
    create_snapshots: bool = False
    event_callbacks: List[Callable[[ExecutionEvent], None]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Workflow executor
# ---------------------------------------------------------------------------


class WorkflowExecutor:
    """Main workflow execution engine.

    Orchestrates the execution of workflows by managing state,
    scheduling nodes, and coordinating execution.

    Example:
        >>> executor = WorkflowExecutor()
        >>> result = await executor.execute(workflow, input_variables={"name": "World"})
        >>> print(result.context.get_completed_nodes())
        ['input_1', 'agent_1', 'output_1']
    """

    def __init__(
        self,
        registry: Optional[NodeExecutorRegistry] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        """Initialize the executor.

        Args:
            registry: Node executor registry (uses default if None)
            config: Execution configuration
        """
        self.registry = registry or get_default_registry()
        self.config = config or ExecutionConfig()

        # Active executions
        self._executions: Dict[str, ExecutionStateContainer] = {}
        self._context_managers: Dict[str, ContextManager] = {}
        self._schedulers: Dict[str, NodeScheduler] = {}
        self._running_nodes: Dict[str, Set[str]] = {}  # execution_id -> node_ids
        self._skipped_nodes: Dict[str, Set[str]] = {}
        self._cancel_flags: Dict[str, bool] = {}

        # Event queue for async iteration
        self._event_queues: Dict[str, asyncio.Queue] = {}

    # -----------------------------------------------------------------------
    # Main execution methods
    # -----------------------------------------------------------------------

    async def execute(
        self,
        workflow: Workflow,
        input_variables: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ) -> WorkflowExecution:
        """Execute a workflow to completion.

        Args:
            workflow: The workflow to execute
            input_variables: Variables to pass to the workflow
            execution_id: Optional execution ID (generated if None)

        Returns:
            WorkflowExecution with final state and context

        Raises:
            WorkflowValidationError: If workflow validation fails
            WorkflowExecutionError: If execution fails
        """
        # Validate if configured
        if self.config.validate_before_execution:
            validate_workflow_or_raise(workflow)

        # Initialize execution
        exec_id = execution_id or str(uuid.uuid4())
        self._initialize_execution(workflow, exec_id, input_variables)

        try:
            # Run the execution loop
            await self._execution_loop(exec_id)

            # Get final execution state
            return self._build_execution_result(exec_id)

        except Exception as e:
            # Handle execution failure
            return self._handle_execution_error(exec_id, e)

        finally:
            # Cleanup
            self._cleanup_execution(exec_id)

    async def execute_stream(
        self,
        workflow: Workflow,
        input_variables: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """Execute a workflow with streaming events.

        Yields events as they occur during execution.

        Args:
            workflow: The workflow to execute
            input_variables: Variables to pass to the workflow
            execution_id: Optional execution ID

        Yields:
            ExecutionEvent for each significant event
        """
        # Validate if configured
        if self.config.validate_before_execution:
            validate_workflow_or_raise(workflow)

        # Initialize execution
        exec_id = execution_id or str(uuid.uuid4())
        self._initialize_execution(workflow, exec_id, input_variables)

        # Create event queue
        self._event_queues[exec_id] = asyncio.Queue()

        try:
            # Start execution as a task
            exec_task = asyncio.create_task(self._execution_loop(exec_id))

            # Yield events as they come
            while not exec_task.done() or not self._event_queues[exec_id].empty():
                try:
                    event = await asyncio.wait_for(
                        self._event_queues[exec_id].get(),
                        timeout=0.1,
                    )
                    yield event
                except asyncio.TimeoutError:
                    continue

            # Check for execution errors
            if exec_task.exception():
                raise exec_task.exception()

            # Yield any remaining events
            while not self._event_queues[exec_id].empty():
                yield await self._event_queues[exec_id].get()

        finally:
            self._cleanup_execution(exec_id)

    # -----------------------------------------------------------------------
    # Execution control
    # -----------------------------------------------------------------------

    async def pause(self, execution_id: str, reason: str = "User paused") -> None:
        """Pause a running execution.

        Args:
            execution_id: The execution ID
            reason: Reason for pausing
        """
        state = self._executions.get(execution_id)
        if state and state.state == ExecutionState.RUNNING:
            state.state_machine.pause(reason)
            await self._emit_event(execution_id, EventType.WORKFLOW_PAUSED, {
                "reason": reason,
            })

    async def resume(self, execution_id: str) -> None:
        """Resume a paused execution.

        Args:
            execution_id: The execution ID
        """
        state = self._executions.get(execution_id)
        if state and state.state_machine.is_paused():
            state.state_machine.resume()
            await self._emit_event(execution_id, EventType.WORKFLOW_RESUMED, {})

    async def cancel(self, execution_id: str, reason: str = "User cancelled") -> None:
        """Cancel a running execution.

        Args:
            execution_id: The execution ID
            reason: Reason for cancellation
        """
        self._cancel_flags[execution_id] = True

        state = self._executions.get(execution_id)
        if state and not state.is_terminal:
            state.state_machine.cancel(reason)
            await self._emit_event(execution_id, EventType.WORKFLOW_CANCELLED, {
                "reason": reason,
            })

    async def provide_input(
        self,
        execution_id: str,
        variables: Dict[str, Any],
    ) -> None:
        """Provide input to a waiting execution.

        Args:
            execution_id: The execution ID
            variables: Input variables to provide
        """
        state = self._executions.get(execution_id)
        context_manager = self._context_managers.get(execution_id)

        if state and state.state_machine.is_waiting_input() and context_manager:
            # Update input variables
            for name, value in variables.items():
                context_manager.set_input_variable(name, value)

            # Resume execution
            state.state_machine.resume()

            await self._emit_event(execution_id, EventType.INPUT_RECEIVED, {
                "variables": list(variables.keys()),
            })

    def get_execution_state(
        self,
        execution_id: str,
    ) -> Optional[ExecutionStateContainer]:
        """Get the current state of an execution.

        Args:
            execution_id: The execution ID

        Returns:
            ExecutionStateContainer or None if not found
        """
        return self._executions.get(execution_id)

    def get_context(self, execution_id: str) -> Optional[WorkflowContext]:
        """Get the context of an execution.

        Args:
            execution_id: The execution ID

        Returns:
            WorkflowContext or None if not found
        """
        manager = self._context_managers.get(execution_id)
        return manager.get_context() if manager else None

    # -----------------------------------------------------------------------
    # Internal methods
    # -----------------------------------------------------------------------

    def _initialize_execution(
        self,
        workflow: Workflow,
        execution_id: str,
        input_variables: Optional[Dict[str, Any]],
    ) -> None:
        """Initialize execution state."""
        # Create state machine
        state_machine = StateMachine(
            on_transition=lambda t: asyncio.create_task(
                self._emit_event(execution_id, EventType.STATE_CHANGED, {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "reason": t.reason,
                })
            )
        )

        state_container = ExecutionStateContainer(
            execution_id=execution_id,
            workflow_id=workflow.id,
            state_machine=state_machine,
        )

        # Create context manager
        context_manager = ContextManager(
            input_variables=input_variables,
            on_change=lambda t, d: asyncio.create_task(
                self._handle_context_change(execution_id, t, d)
            ),
        )

        # Create scheduler
        scheduler = NodeScheduler(workflow)

        # Store state
        self._executions[execution_id] = state_container
        self._context_managers[execution_id] = context_manager
        self._schedulers[execution_id] = scheduler
        self._running_nodes[execution_id] = set()
        self._skipped_nodes[execution_id] = set()
        self._cancel_flags[execution_id] = False

    async def _execution_loop(self, execution_id: str) -> None:
        """Main execution loop."""
        state = self._executions[execution_id]
        context_manager = self._context_managers[execution_id]
        scheduler = self._schedulers[execution_id]

        # Start execution
        state.start()
        await self._emit_event(execution_id, EventType.WORKFLOW_STARTED, {
            "workflow_id": state.workflow_id,
        })

        try:
            while not state.is_terminal:
                # Check for cancellation
                if self._cancel_flags.get(execution_id, False):
                    raise WorkflowCancelledError(
                        workflow_id=state.workflow_id,
                        execution_id=execution_id,
                    )

                # Wait if paused
                if state.state_machine.is_paused():
                    await asyncio.sleep(0.1)
                    continue

                # Wait if waiting for input
                if state.state_machine.is_waiting_input():
                    await asyncio.sleep(0.1)
                    continue

                # Get ready nodes
                result = scheduler.compute_ready_nodes(
                    context_manager.context,
                    self._running_nodes[execution_id],
                    self._skipped_nodes[execution_id],
                )

                # Check if complete
                if result.is_complete and not self._running_nodes[execution_id]:
                    state.complete()
                    await self._emit_event(execution_id, EventType.WORKFLOW_COMPLETED, {
                        "statistics": context_manager.get_statistics(),
                    })
                    break

                # Execute ready nodes
                if result.has_ready_nodes:
                    await self._execute_ready_nodes(
                        execution_id,
                        result.ready_nodes,
                    )
                elif not self._running_nodes[execution_id]:
                    # No ready nodes and nothing running - might be done or stuck
                    if not result.waiting_nodes:
                        state.complete()
                        await self._emit_event(execution_id, EventType.WORKFLOW_COMPLETED, {
                            "statistics": context_manager.get_statistics(),
                        })
                        break
                    else:
                        # Still waiting on something - small delay
                        await asyncio.sleep(0.1)

        except WorkflowCancelledError:
            state.state_machine.cancel("Cancelled")
            await self._emit_event(execution_id, EventType.WORKFLOW_CANCELLED, {})
            raise

        except Exception as e:
            logger.exception("Execution loop error: %s", e)
            state.fail(str(e))
            await self._emit_event(execution_id, EventType.WORKFLOW_FAILED, {
                "error": str(e),
            })
            raise

    async def _execute_ready_nodes(
        self,
        execution_id: str,
        nodes: List[WorkflowNode],
    ) -> None:
        """Execute nodes that are ready to run."""
        state = self._executions[execution_id]

        # Separate parallel and sequential nodes
        parallel_nodes = [n for n in nodes if n.config.parallel]
        sequential_nodes = [n for n in nodes if not n.config.parallel]

        # Limit parallel execution
        if len(parallel_nodes) > self.config.max_parallel_nodes:
            # Execute in batches
            batch = parallel_nodes[:self.config.max_parallel_nodes]
            remaining = parallel_nodes[self.config.max_parallel_nodes:]
            sequential_nodes = remaining + sequential_nodes
            parallel_nodes = batch

        # Execute parallel nodes concurrently
        if parallel_nodes:
            tasks = [
                self._execute_single_node(execution_id, node)
                for node in parallel_nodes
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Execute sequential nodes one at a time
        for node in sequential_nodes:
            if self._cancel_flags.get(execution_id, False):
                break
            await self._execute_single_node(execution_id, node)

    async def _execute_single_node(
        self,
        execution_id: str,
        node: WorkflowNode,
    ) -> NodeExecutionResult:
        """Execute a single node."""
        state = self._executions[execution_id]
        context_manager = self._context_managers[execution_id]

        # Check for breakpoint
        if node.config.breakpoint:
            state.state_machine.pause(f"Breakpoint at node {node.id}")
            await self._emit_event(execution_id, EventType.BREAKPOINT, {
                "node_id": node.id,
                "node_name": node.name,
            })
            # Wait for resume
            while state.state_machine.is_paused():
                await asyncio.sleep(0.1)

        # Mark as running
        self._running_nodes[execution_id].add(node.id)

        await self._emit_event(execution_id, EventType.NODE_STARTED, {
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.type.value,
        })

        # Get executor
        executor = self.registry.get_executor(node.type.value)
        if executor is None:
            result = NodeExecutionResult.error(
                node_id=node.id,
                error=f"No executor for node type: {node.type.value}",
            )
        else:
            # Create execution context
            exec_context = ExecutionContext(
                workflow_context=context_manager.context,
                node=node,
                execution_id=execution_id,
                on_token=lambda t: asyncio.create_task(
                    self._emit_event(execution_id, EventType.TOKEN, {
                        "node_id": node.id,
                        "token": t,
                    })
                ),
                cancel_requested=self._cancel_flags.get(execution_id, False),
            )

            # Execute with timeout
            try:
                result = await executor.execute_with_timeout(exec_context)
            except Exception as e:
                result = NodeExecutionResult.error(
                    node_id=node.id,
                    error=str(e),
                )

        # Mark as done
        self._running_nodes[execution_id].discard(node.id)

        # Record result
        if result.status.value == "success":
            context_manager.record_success(
                node_id=node.id,
                output=result.output,
                tokens=result.tokens,
                duration=result.duration,
            )
            await self._emit_event(execution_id, EventType.NODE_COMPLETED, {
                "node_id": node.id,
                "duration": result.duration,
            })
        elif result.status.value == "skipped":
            self._skipped_nodes[execution_id].add(node.id)
            context_manager.record_skipped(node.id, result.error or "")
            await self._emit_event(execution_id, EventType.NODE_SKIPPED, {
                "node_id": node.id,
                "reason": result.error,
            })
        else:
            context_manager.record_error(node.id, result.error or "Unknown error")
            await self._emit_event(execution_id, EventType.NODE_FAILED, {
                "node_id": node.id,
                "error": result.error,
            })

            # Stop on error if configured
            if self.config.stop_on_error:
                raise NodeExecutionError(
                    message=result.error or "Node execution failed",
                    workflow_id=state.workflow_id,
                    execution_id=execution_id,
                    node_id=node.id,
                )

        return result

    async def _emit_event(
        self,
        execution_id: str,
        event_type: EventType,
        data: Dict[str, Any],
    ) -> None:
        """Emit an execution event."""
        event = ExecutionEvent(
            type=event_type,
            execution_id=execution_id,
            data=data,
        )

        # Notify callbacks
        for callback in self.config.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning("Event callback failed: %s", e)

        # Add to queue if streaming
        if execution_id in self._event_queues:
            await self._event_queues[execution_id].put(event)

    async def _handle_context_change(
        self,
        execution_id: str,
        change_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Handle context changes."""
        # Could emit events or trigger other actions
        pass

    def _build_execution_result(
        self,
        execution_id: str,
    ) -> WorkflowExecution:
        """Build the final execution result."""
        state = self._executions[execution_id]
        context_manager = self._context_managers[execution_id]

        return WorkflowExecution(
            id=execution_id,
            workflow_id=state.workflow_id,
            state=state.state,
            context=context_manager.get_context(),
            started_at=state.started_at,
            completed_at=state.completed_at,
            error=state.error,
        )

    def _handle_execution_error(
        self,
        execution_id: str,
        error: Exception,
    ) -> WorkflowExecution:
        """Handle execution error and build result."""
        state = self._executions[execution_id]
        context_manager = self._context_managers[execution_id]

        # Update state if not already failed
        if not state.is_terminal:
            state.fail(str(error))

        return WorkflowExecution(
            id=execution_id,
            workflow_id=state.workflow_id,
            state=ExecutionState.FAILED,
            context=context_manager.get_context(),
            started_at=state.started_at,
            completed_at=datetime.now(),
            error=str(error),
        )

    def _cleanup_execution(self, execution_id: str) -> None:
        """Clean up execution state."""
        # Keep state for inspection, but clean up queues
        if execution_id in self._event_queues:
            del self._event_queues[execution_id]


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


async def execute_workflow(
    workflow: Workflow,
    input_variables: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> WorkflowExecution:
    """Execute a workflow to completion.

    Convenience function that creates an executor and runs the workflow.

    Args:
        workflow: The workflow to execute
        input_variables: Variables to pass to the workflow
        **kwargs: Additional arguments for ExecutionConfig

    Returns:
        WorkflowExecution with final state and context
    """
    config = ExecutionConfig(**kwargs)
    executor = WorkflowExecutor(config=config)
    return await executor.execute(workflow, input_variables)
