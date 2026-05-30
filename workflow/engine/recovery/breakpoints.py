"""
Breakpoint management for workflow execution.

Provides pause/resume functionality at specific nodes:
- Breakpoint: A pause point in the workflow
- BreakpointManager: Manages breakpoints across executions
- Support for conditional breakpoints
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Breakpoint state
# ---------------------------------------------------------------------------


class BreakpointState(str, Enum):
    """State of a breakpoint."""

    ACTIVE = "active"       # Will pause when hit
    DISABLED = "disabled"   # Won't pause, but still tracked
    HIT = "hit"             # Currently paused at this breakpoint
    PASSED = "passed"       # Was hit and resumed


# ---------------------------------------------------------------------------
# Breakpoint
# ---------------------------------------------------------------------------


@dataclass
class Breakpoint:
    """A breakpoint in a workflow.

    Attributes:
        id: Unique identifier
        node_id: The node to pause at
        workflow_id: The workflow this breakpoint belongs to
        state: Current state of the breakpoint
        condition: Optional condition expression (breakpoint only fires if true)
        hit_count: Number of times this breakpoint has been hit
        max_hits: Optional limit on hit count (0 = unlimited)
        label: Human-readable label
        created_at: When the breakpoint was created
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    workflow_id: str = ""
    state: BreakpointState = BreakpointState.ACTIVE
    condition: Optional[str] = None
    hit_count: int = 0
    max_hits: int = 0  # 0 = unlimited
    label: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def should_fire(self) -> bool:
        """Check if this breakpoint should fire when hit.

        Returns:
            True if the breakpoint should pause execution
        """
        if self.state != BreakpointState.ACTIVE:
            return False

        if self.max_hits > 0 and self.hit_count >= self.max_hits:
            return False

        return True

    def record_hit(self) -> None:
        """Record that this breakpoint was hit."""
        self.hit_count += 1
        self.state = BreakpointState.HIT

    def resume(self) -> None:
        """Resume execution after hitting this breakpoint."""
        self.state = BreakpointState.ACTIVE

    def disable(self) -> None:
        """Disable this breakpoint."""
        self.state = BreakpointState.DISABLED

    def enable(self) -> None:
        """Enable this breakpoint."""
        if self.state == BreakpointState.DISABLED:
            self.state = BreakpointState.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "node_id": self.node_id,
            "workflow_id": self.workflow_id,
            "state": self.state.value,
            "condition": self.condition,
            "hit_count": self.hit_count,
            "max_hits": self.max_hits,
            "label": self.label,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Breakpoint:
        """Create from dictionary."""
        created_at = data.get("created_at")
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            node_id=data.get("node_id", ""),
            workflow_id=data.get("workflow_id", ""),
            state=BreakpointState(data.get("state", "active")),
            condition=data.get("condition"),
            hit_count=data.get("hit_count", 0),
            max_hits=data.get("max_hits", 0),
            label=data.get("label", ""),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Breakpoint manager
# ---------------------------------------------------------------------------


class BreakpointManager:
    """Manages breakpoints for workflow executions.

    Provides:
    - Adding/removing breakpoints
    - Checking if execution should pause
    - Resuming paused executions
    - Persisting breakpoint state

    Example:
        >>> manager = BreakpointManager()
        >>> bp = manager.add_breakpoint("workflow_1", "node_5")
        >>> # During execution:
        >>> if manager.should_pause("workflow_1", "node_5"):
        ...     await manager.wait_for_resume(execution_id)
    """

    def __init__(self):
        self._breakpoints: Dict[str, Breakpoint] = {}  # breakpoint_id -> Breakpoint
        self._by_workflow: Dict[str, Set[str]] = {}    # workflow_id -> breakpoint_ids
        self._by_node: Dict[str, Set[str]] = {}        # node_id -> breakpoint_ids

        # Execution pause state
        self._paused_executions: Dict[str, str] = {}   # execution_id -> breakpoint_id
        self._resume_events: Dict[str, asyncio.Event] = {}

    # -----------------------------------------------------------------------
    # Breakpoint management
    # -----------------------------------------------------------------------

    def add_breakpoint(
        self,
        workflow_id: str,
        node_id: str,
        label: str = "",
        condition: Optional[str] = None,
        max_hits: int = 0,
    ) -> Breakpoint:
        """Add a breakpoint to a workflow node.

        Args:
            workflow_id: The workflow ID
            node_id: The node to pause at
            label: Optional human-readable label
            condition: Optional condition expression
            max_hits: Maximum times to fire (0 = unlimited)

        Returns:
            The created Breakpoint
        """
        breakpoint = Breakpoint(
            node_id=node_id,
            workflow_id=workflow_id,
            label=label or f"Breakpoint at {node_id}",
            condition=condition,
            max_hits=max_hits,
        )

        self._breakpoints[breakpoint.id] = breakpoint

        # Index by workflow
        if workflow_id not in self._by_workflow:
            self._by_workflow[workflow_id] = set()
        self._by_workflow[workflow_id].add(breakpoint.id)

        # Index by node
        node_key = f"{workflow_id}:{node_id}"
        if node_key not in self._by_node:
            self._by_node[node_key] = set()
        self._by_node[node_key].add(breakpoint.id)

        logger.info(
            "Added breakpoint %s at %s:%s",
            breakpoint.id,
            workflow_id,
            node_id,
        )

        return breakpoint

    def remove_breakpoint(self, breakpoint_id: str) -> bool:
        """Remove a breakpoint.

        Args:
            breakpoint_id: The breakpoint ID

        Returns:
            True if removed, False if not found
        """
        breakpoint = self._breakpoints.pop(breakpoint_id, None)
        if not breakpoint:
            return False

        # Remove from indices
        if breakpoint.workflow_id in self._by_workflow:
            self._by_workflow[breakpoint.workflow_id].discard(breakpoint_id)

        node_key = f"{breakpoint.workflow_id}:{breakpoint.node_id}"
        if node_key in self._by_node:
            self._by_node[node_key].discard(breakpoint_id)

        logger.info("Removed breakpoint %s", breakpoint_id)
        return True

    def get_breakpoint(self, breakpoint_id: str) -> Optional[Breakpoint]:
        """Get a breakpoint by ID."""
        return self._breakpoints.get(breakpoint_id)

    def get_breakpoints_for_workflow(self, workflow_id: str) -> List[Breakpoint]:
        """Get all breakpoints for a workflow."""
        bp_ids = self._by_workflow.get(workflow_id, set())
        return [self._breakpoints[bp_id] for bp_id in bp_ids if bp_id in self._breakpoints]

    def get_breakpoints_for_node(
        self,
        workflow_id: str,
        node_id: str,
    ) -> List[Breakpoint]:
        """Get all breakpoints for a specific node."""
        node_key = f"{workflow_id}:{node_id}"
        bp_ids = self._by_node.get(node_key, set())
        return [self._breakpoints[bp_id] for bp_id in bp_ids if bp_id in self._breakpoints]

    def enable_breakpoint(self, breakpoint_id: str) -> bool:
        """Enable a breakpoint."""
        bp = self._breakpoints.get(breakpoint_id)
        if bp:
            bp.enable()
            return True
        return False

    def disable_breakpoint(self, breakpoint_id: str) -> bool:
        """Disable a breakpoint."""
        bp = self._breakpoints.get(breakpoint_id)
        if bp:
            bp.disable()
            return True
        return False

    def toggle_breakpoint(
        self,
        workflow_id: str,
        node_id: str,
    ) -> Optional[Breakpoint]:
        """Toggle a breakpoint on a node.

        If a breakpoint exists, remove it. Otherwise, add one.

        Returns:
            The new breakpoint if added, None if removed
        """
        existing = self.get_breakpoints_for_node(workflow_id, node_id)
        if existing:
            self.remove_breakpoint(existing[0].id)
            return None
        else:
            return self.add_breakpoint(workflow_id, node_id)

    # -----------------------------------------------------------------------
    # Execution control
    # -----------------------------------------------------------------------

    def should_pause(
        self,
        workflow_id: str,
        node_id: str,
        context: Optional[Any] = None,
    ) -> Optional[Breakpoint]:
        """Check if execution should pause at a node.

        Args:
            workflow_id: The workflow ID
            node_id: The current node ID
            context: Optional execution context for condition evaluation

        Returns:
            The breakpoint to pause at, or None if should not pause
        """
        breakpoints = self.get_breakpoints_for_node(workflow_id, node_id)

        for bp in breakpoints:
            if not bp.should_fire():
                continue

            # Evaluate condition if present
            if bp.condition and context:
                try:
                    # TODO: Implement condition evaluation
                    # For now, always fire if condition is set
                    pass
                except Exception as e:
                    logger.warning("Breakpoint condition evaluation failed: %s", e)
                    continue

            return bp

        return None

    def pause_execution(
        self,
        execution_id: str,
        breakpoint: Breakpoint,
    ) -> None:
        """Mark an execution as paused at a breakpoint.

        Args:
            execution_id: The execution ID
            breakpoint: The breakpoint that was hit
        """
        breakpoint.record_hit()
        self._paused_executions[execution_id] = breakpoint.id
        self._resume_events[execution_id] = asyncio.Event()

        logger.info(
            "Execution %s paused at breakpoint %s",
            execution_id,
            breakpoint.id,
        )

    def is_paused(self, execution_id: str) -> bool:
        """Check if an execution is paused."""
        return execution_id in self._paused_executions

    def get_pause_breakpoint(self, execution_id: str) -> Optional[Breakpoint]:
        """Get the breakpoint an execution is paused at."""
        bp_id = self._paused_executions.get(execution_id)
        if bp_id:
            return self._breakpoints.get(bp_id)
        return None

    async def wait_for_resume(
        self,
        execution_id: str,
        timeout: Optional[float] = None,
    ) -> bool:
        """Wait for an execution to be resumed.

        Args:
            execution_id: The execution ID
            timeout: Optional timeout in seconds

        Returns:
            True if resumed, False if timed out
        """
        event = self._resume_events.get(execution_id)
        if not event:
            return True  # Not paused

        try:
            if timeout:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()
            return True
        except asyncio.TimeoutError:
            return False

    def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution.

        Args:
            execution_id: The execution ID

        Returns:
            True if resumed, False if not paused
        """
        if execution_id not in self._paused_executions:
            return False

        bp_id = self._paused_executions.pop(execution_id)
        bp = self._breakpoints.get(bp_id)
        if bp:
            bp.resume()

        event = self._resume_events.pop(execution_id, None)
        if event:
            event.set()

        logger.info("Execution %s resumed", execution_id)
        return True

    def resume_all(self) -> int:
        """Resume all paused executions.

        Returns:
            Number of executions resumed
        """
        count = 0
        for exec_id in list(self._paused_executions.keys()):
            if self.resume_execution(exec_id):
                count += 1
        return count

    # -----------------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Get breakpoint manager statistics."""
        active = sum(1 for bp in self._breakpoints.values() if bp.state == BreakpointState.ACTIVE)
        disabled = sum(1 for bp in self._breakpoints.values() if bp.state == BreakpointState.DISABLED)
        total_hits = sum(bp.hit_count for bp in self._breakpoints.values())

        return {
            "total_breakpoints": len(self._breakpoints),
            "active_breakpoints": active,
            "disabled_breakpoints": disabled,
            "paused_executions": len(self._paused_executions),
            "total_hits": total_hits,
        }

    def clear_all(self) -> None:
        """Clear all breakpoints and resume all paused executions."""
        self.resume_all()
        self._breakpoints.clear()
        self._by_workflow.clear()
        self._by_node.clear()
