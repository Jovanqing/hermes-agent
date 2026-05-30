"""
State machine for workflow execution.

Manages execution state transitions:
    idle -> running -> completed
                   -> failed
                   -> paused -> running
                   -> waiting_input -> running
                   -> cancelled
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from workflow.models import ExecutionState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


# Valid state transitions
VALID_TRANSITIONS: Dict[ExecutionState, Set[ExecutionState]] = {
    ExecutionState.IDLE: {
        ExecutionState.RUNNING,
        ExecutionState.CANCELLED,
    },
    ExecutionState.RUNNING: {
        ExecutionState.PAUSED,
        ExecutionState.WAITING_INPUT,
        ExecutionState.COMPLETED,
        ExecutionState.FAILED,
        ExecutionState.CANCELLED,
    },
    ExecutionState.PAUSED: {
        ExecutionState.RUNNING,
        ExecutionState.CANCELLED,
    },
    ExecutionState.WAITING_INPUT: {
        ExecutionState.RUNNING,
        ExecutionState.CANCELLED,
    },
    ExecutionState.COMPLETED: set(),  # Terminal state
    ExecutionState.FAILED: set(),     # Terminal state
    ExecutionState.CANCELLED: set(),  # Terminal state
}

# Terminal states
TERMINAL_STATES = {
    ExecutionState.COMPLETED,
    ExecutionState.FAILED,
    ExecutionState.CANCELLED,
}

# Active states (execution is in progress)
ACTIVE_STATES = {
    ExecutionState.RUNNING,
    ExecutionState.PAUSED,
    ExecutionState.WAITING_INPUT,
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(
        self,
        from_state: ExecutionState,
        to_state: ExecutionState,
        reason: str = "",
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason

        message = f"Invalid transition: {from_state.value} -> {to_state.value}"
        if reason:
            message += f" ({reason})"

        super().__init__(message)


# ---------------------------------------------------------------------------
# State transition record
# ---------------------------------------------------------------------------


@dataclass
class StateTransition:
    """Record of a state transition.

    Attributes:
        from_state: Previous state
        to_state: New state
        timestamp: When the transition occurred
        reason: Optional reason for the transition
        metadata: Additional transition data
    """

    from_state: ExecutionState
    to_state: ExecutionState
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class StateMachine:
    """State machine for workflow execution.

    Manages state transitions and maintains transition history.

    Example:
        >>> sm = StateMachine()
        >>> sm.transition(ExecutionState.RUNNING)
        >>> sm.is_active()
        True
        >>> sm.transition(ExecutionState.PAUSED, reason="Breakpoint")
        >>> sm.state
        <ExecutionState.PAUSED>
    """

    def __init__(
        self,
        initial_state: ExecutionState = ExecutionState.IDLE,
        on_transition: Optional[Callable[[StateTransition], None]] = None,
    ):
        """Initialize the state machine.

        Args:
            initial_state: Starting state
            on_transition: Optional callback for state transitions
        """
        self._state = initial_state
        self._history: List[StateTransition] = []
        self._on_transition = on_transition
        self._state_entered_at = datetime.now()

    @property
    def state(self) -> ExecutionState:
        """Get the current state."""
        return self._state

    @property
    def history(self) -> List[StateTransition]:
        """Get the transition history."""
        return list(self._history)

    @property
    def state_entered_at(self) -> datetime:
        """Get when the current state was entered."""
        return self._state_entered_at

    def can_transition(self, to_state: ExecutionState) -> bool:
        """Check if a transition is valid.

        Args:
            to_state: Target state

        Returns:
            True if the transition is valid
        """
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        return to_state in valid_targets

    def transition(
        self,
        to_state: ExecutionState,
        reason: str = "",
        **metadata: Any,
    ) -> StateTransition:
        """Transition to a new state.

        Args:
            to_state: Target state
            reason: Optional reason for the transition
            **metadata: Additional transition data

        Returns:
            The StateTransition record

        Raises:
            InvalidStateTransition: If the transition is not valid
        """
        if not self.can_transition(to_state):
            raise InvalidStateTransition(
                from_state=self._state,
                to_state=to_state,
                reason=reason,
            )

        # Create transition record
        transition = StateTransition(
            from_state=self._state,
            to_state=to_state,
            timestamp=datetime.now(),
            reason=reason,
            metadata=metadata,
        )

        # Update state
        old_state = self._state
        self._state = to_state
        self._state_entered_at = transition.timestamp
        self._history.append(transition)

        logger.debug(
            "State transition: %s -> %s (reason: %s)",
            old_state.value,
            to_state.value,
            reason or "none",
        )

        # Notify callback
        if self._on_transition:
            try:
                self._on_transition(transition)
            except Exception as e:
                logger.warning("State transition callback failed: %s", e)

        return transition

    def is_terminal(self) -> bool:
        """Check if the current state is terminal."""
        return self._state in TERMINAL_STATES

    def is_active(self) -> bool:
        """Check if execution is currently active."""
        return self._state in ACTIVE_STATES

    def is_running(self) -> bool:
        """Check if execution is actively running (not paused)."""
        return self._state == ExecutionState.RUNNING

    def is_paused(self) -> bool:
        """Check if execution is paused."""
        return self._state == ExecutionState.PAUSED

    def is_waiting_input(self) -> bool:
        """Check if execution is waiting for input."""
        return self._state == ExecutionState.WAITING_INPUT

    # Convenience transition methods

    def start(self, reason: str = "Starting execution") -> StateTransition:
        """Start execution (idle -> running)."""
        return self.transition(ExecutionState.RUNNING, reason)

    def pause(self, reason: str = "Paused") -> StateTransition:
        """Pause execution (running -> paused)."""
        return self.transition(ExecutionState.PAUSED, reason)

    def resume(self, reason: str = "Resumed") -> StateTransition:
        """Resume execution (paused/waiting -> running)."""
        return self.transition(ExecutionState.RUNNING, reason)

    def complete(self, reason: str = "Completed") -> StateTransition:
        """Complete execution (running -> completed)."""
        return self.transition(ExecutionState.COMPLETED, reason)

    def fail(self, error: str) -> StateTransition:
        """Fail execution (running -> failed)."""
        return self.transition(ExecutionState.FAILED, reason=error, error=error)

    def cancel(self, reason: str = "Cancelled") -> StateTransition:
        """Cancel execution."""
        return self.transition(ExecutionState.CANCELLED, reason)

    def wait_for_input(
        self,
        reason: str = "Waiting for input",
        **metadata: Any,
    ) -> StateTransition:
        """Wait for external input (running -> waiting_input)."""
        return self.transition(ExecutionState.WAITING_INPUT, reason, **metadata)

    # State duration tracking

    def time_in_current_state(self) -> float:
        """Get seconds spent in the current state."""
        return (datetime.now() - self._state_entered_at).total_seconds()

    def total_time_in_state(self, state: ExecutionState) -> float:
        """Get total seconds spent in a specific state.

        Args:
            state: The state to calculate time for

        Returns:
            Total seconds in that state
        """
        total = 0.0

        for i, transition in enumerate(self._history):
            if transition.from_state == state:
                # Calculate duration of this stay
                if i + 1 < len(self._history):
                    end_time = self._history[i + 1].timestamp
                else:
                    end_time = datetime.now() if self._state == state else transition.timestamp

                duration = (end_time - transition.timestamp).total_seconds()
                total += duration

        # Handle initial state
        if self._history and self._history[0].from_state == state:
            pass  # Already counted
        elif not self._history and state == ExecutionState.IDLE:
            total += self.time_in_current_state()

        return total


# ---------------------------------------------------------------------------
# Execution state container
# ---------------------------------------------------------------------------


@dataclass
class ExecutionStateContainer:
    """Container for execution state and metadata.

    Combines the state machine with additional execution data.
    """

    execution_id: str
    workflow_id: str
    state_machine: StateMachine
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def state(self) -> ExecutionState:
        return self.state_machine.state

    @property
    def is_terminal(self) -> bool:
        return self.state_machine.is_terminal()

    @property
    def duration(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def start(self) -> None:
        """Mark execution as started."""
        self.started_at = datetime.now()
        self.state_machine.start()

    def complete(self) -> None:
        """Mark execution as completed."""
        self.completed_at = datetime.now()
        self.state_machine.complete()

    def fail(self, error: str) -> None:
        """Mark execution as failed."""
        self.completed_at = datetime.now()
        self.error = error
        self.state_machine.fail(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "duration": self.duration,
            "history": [
                {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "reason": t.reason,
                }
                for t in self.state_machine.history
            ],
        }
