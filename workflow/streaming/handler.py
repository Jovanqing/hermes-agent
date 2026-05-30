"""
Stream handler for workflow execution events.

Formats execution events for SSE streaming:
- Token events: Individual LLM tokens
- Node lifecycle events: started, completed, failed
- Workflow lifecycle events: started, completed, failed, paused
- State change events
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class StreamEventType(str, Enum):
    """Types of stream events."""

    # Workflow lifecycle
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    WORKFLOW_CANCELLED = "workflow.cancelled"

    # Node lifecycle
    NODE_STARTED = "node.started"
    NODE_COMPLETED = "node.completed"
    NODE_FAILED = "node.failed"
    NODE_SKIPPED = "node.skipped"

    # Token streaming
    TOKEN = "token"
    TOKEN_COMPLETE = "token.complete"

    # State changes
    STATE_CHANGED = "state.changed"

    # Breakpoints
    BREAKPOINT_HIT = "breakpoint.hit"

    # Errors
    ERROR = "error"

    # Keepalive
    KEEPALIVE = "keepalive"


# ---------------------------------------------------------------------------
# Stream event
# ---------------------------------------------------------------------------


@dataclass
class StreamEvent:
    """A single stream event.

    Attributes:
        type: Event type
        execution_id: The execution this event belongs to
        data: Event-specific data
        timestamp: When the event occurred
        sequence: Event sequence number for ordering
    """

    type: StreamEventType
    execution_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a serializable dictionary."""
        return {
            "type": self.type.value,
            "execution_id": self.execution_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    def to_sse(self) -> str:
        """Format as Server-Sent Event.

        SSE format:
            event: <event-type>
            data: <json-data>

        """
        return f"event: {self.type.value}\ndata: {self.to_json()}\n\n"

    @classmethod
    def workflow_started(
        cls,
        execution_id: str,
        workflow_id: str,
        workflow_name: str,
    ) -> StreamEvent:
        """Create a workflow.started event."""
        return cls(
            type=StreamEventType.WORKFLOW_STARTED,
            execution_id=execution_id,
            data={
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
            },
        )

    @classmethod
    def workflow_completed(
        cls,
        execution_id: str,
        statistics: Dict[str, Any],
        duration: float,
    ) -> StreamEvent:
        """Create a workflow.completed event."""
        return cls(
            type=StreamEventType.WORKFLOW_COMPLETED,
            execution_id=execution_id,
            data={
                "statistics": statistics,
                "duration": duration,
            },
        )

    @classmethod
    def workflow_failed(
        cls,
        execution_id: str,
        error: str,
        failed_node_id: Optional[str] = None,
    ) -> StreamEvent:
        """Create a workflow.failed event."""
        return cls(
            type=StreamEventType.WORKFLOW_FAILED,
            execution_id=execution_id,
            data={
                "error": error,
                "failed_node_id": failed_node_id,
            },
        )

    @classmethod
    def workflow_paused(
        cls,
        execution_id: str,
        reason: str,
    ) -> StreamEvent:
        """Create a workflow.paused event."""
        return cls(
            type=StreamEventType.WORKFLOW_PAUSED,
            execution_id=execution_id,
            data={"reason": reason},
        )

    @classmethod
    def workflow_resumed(cls, execution_id: str) -> StreamEvent:
        """Create a workflow.resumed event."""
        return cls(
            type=StreamEventType.WORKFLOW_RESUMED,
            execution_id=execution_id,
            data={},
        )

    @classmethod
    def workflow_cancelled(
        cls,
        execution_id: str,
        reason: str,
    ) -> StreamEvent:
        """Create a workflow.cancelled event."""
        return cls(
            type=StreamEventType.WORKFLOW_CANCELLED,
            execution_id=execution_id,
            data={"reason": reason},
        )

    @classmethod
    def node_started(
        cls,
        execution_id: str,
        node_id: str,
        node_name: str,
        node_type: str,
    ) -> StreamEvent:
        """Create a node.started event."""
        return cls(
            type=StreamEventType.NODE_STARTED,
            execution_id=execution_id,
            data={
                "node_id": node_id,
                "node_name": node_name,
                "node_type": node_type,
            },
        )

    @classmethod
    def node_completed(
        cls,
        execution_id: str,
        node_id: str,
        output: Any,
        duration: float,
        tokens: Optional[Dict[str, int]] = None,
    ) -> StreamEvent:
        """Create a node.completed event."""
        # Truncate large outputs for streaming
        output_preview = output
        if isinstance(output, str) and len(output) > 500:
            output_preview = output[:500] + "..."
        elif isinstance(output, dict):
            output_str = json.dumps(output)
            if len(output_str) > 500:
                output_preview = output_str[:500] + "..."

        return cls(
            type=StreamEventType.NODE_COMPLETED,
            execution_id=execution_id,
            data={
                "node_id": node_id,
                "output": output_preview,
                "duration": duration,
                "tokens": tokens,
            },
        )

    @classmethod
    def node_failed(
        cls,
        execution_id: str,
        node_id: str,
        error: str,
        retry_count: int = 0,
    ) -> StreamEvent:
        """Create a node.failed event."""
        return cls(
            type=StreamEventType.NODE_FAILED,
            execution_id=execution_id,
            data={
                "node_id": node_id,
                "error": error,
                "retry_count": retry_count,
            },
        )

    @classmethod
    def node_skipped(
        cls,
        execution_id: str,
        node_id: str,
        reason: str,
    ) -> StreamEvent:
        """Create a node.skipped event."""
        return cls(
            type=StreamEventType.NODE_SKIPPED,
            execution_id=execution_id,
            data={
                "node_id": node_id,
                "reason": reason,
            },
        )

    @classmethod
    def token(
        cls,
        execution_id: str,
        node_id: str,
        token: str,
        index: int,
    ) -> StreamEvent:
        """Create a token event."""
        return cls(
            type=StreamEventType.TOKEN,
            execution_id=execution_id,
            data={
                "node_id": node_id,
                "token": token,
                "index": index,
            },
        )

    @classmethod
    def token_complete(
        cls,
        execution_id: str,
        node_id: str,
        full_output: str,
        tokens: Dict[str, int],
    ) -> StreamEvent:
        """Create a token.complete event (end of streaming for a node)."""
        return cls(
            type=StreamEventType.TOKEN_COMPLETE,
            execution_id=execution_id,
            data={
                "node_id": node_id,
                "full_output": full_output,
                "tokens": tokens,
            },
        )

    @classmethod
    def state_changed(
        cls,
        execution_id: str,
        from_state: str,
        to_state: str,
        reason: str = "",
    ) -> StreamEvent:
        """Create a state.changed event."""
        return cls(
            type=StreamEventType.STATE_CHANGED,
            execution_id=execution_id,
            data={
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason,
            },
        )

    @classmethod
    def breakpoint_hit(
        cls,
        execution_id: str,
        node_id: str,
        node_name: str,
    ) -> StreamEvent:
        """Create a breakpoint.hit event."""
        return cls(
            type=StreamEventType.BREAKPOINT_HIT,
            execution_id=execution_id,
            data={
                "node_id": node_id,
                "node_name": node_name,
            },
        )

    @classmethod
    def error(
        cls,
        execution_id: str,
        error: str,
        error_type: str = "unknown",
    ) -> StreamEvent:
        """Create an error event."""
        return cls(
            type=StreamEventType.ERROR,
            execution_id=execution_id,
            data={
                "error": error,
                "error_type": error_type,
            },
        )

    @classmethod
    def keepalive(cls, execution_id: str) -> StreamEvent:
        """Create a keepalive event."""
        return cls(
            type=StreamEventType.KEEPALIVE,
            execution_id=execution_id,
            data={},
        )


# ---------------------------------------------------------------------------
# Stream handler
# ---------------------------------------------------------------------------


class StreamHandler:
    """Handles stream events for a workflow execution.

    Collects events and provides them to subscribers.
    Maintains event history for late-joining subscribers.

    Example:
        >>> handler = StreamHandler(execution_id)
        >>> handler.emit(StreamEvent.node_started(...))
        >>> async for event in handler.subscribe():
        ...     print(event.to_sse())
    """

    def __init__(
        self,
        execution_id: str,
        max_history: int = 1000,
    ):
        """Initialize the stream handler.

        Args:
            execution_id: The execution this handler is for
            max_history: Maximum events to keep in history
        """
        self.execution_id = execution_id
        self.max_history = max_history

        self._history: List[StreamEvent] = []
        self._subscribers: List[asyncio.Queue] = []
        self._sequence = 0
        self._closed = False

    @property
    def is_closed(self) -> bool:
        """Check if the handler is closed."""
        return self._closed

    def emit(self, event: StreamEvent) -> None:
        """Emit an event to all subscribers.

        Args:
            event: The event to emit
        """
        if self._closed:
            return

        # Assign sequence number
        event.sequence = self._sequence
        self._sequence += 1

        # Add to history
        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        # Notify subscribers
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Subscriber queue full for execution %s",
                    self.execution_id,
                )

    async def subscribe(
        self,
        include_history: bool = True,
    ) -> AsyncIterator[StreamEvent]:
        """Subscribe to events.

        Args:
            include_history: Whether to include historical events

        Yields:
            StreamEvent objects as they occur
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.append(queue)

        try:
            # Yield history first
            if include_history:
                for event in self._history:
                    yield event

            # Yield new events
            while not self._closed:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield StreamEvent.keepalive(self.execution_id)

        finally:
            self._subscribers.remove(queue)

    def close(self) -> None:
        """Close the handler and notify subscribers."""
        self._closed = True

        # Signal subscribers by putting a sentinel
        for queue in self._subscribers:
            try:
                queue.put_nowait(None)  # type: ignore
            except asyncio.QueueFull:
                pass

    def get_history(self) -> List[StreamEvent]:
        """Get the event history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear the event history."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def format_sse_comment(comment: str) -> str:
    """Format a comment for SSE.

    Comments start with ':' and are ignored by EventSource.
    Useful for keepalive or debugging.
    """
    lines = comment.split("\n")
    return "\n".join(f": {line}" for line in lines) + "\n\n"


def parse_sse_event(data: str) -> Dict[str, Any]:
    """Parse an SSE event string.

    Args:
        data: The raw SSE event data

    Returns:
        Dict with 'event' and 'data' keys
    """
    event_type = "message"
    event_data = ""

    for line in data.strip().split("\n"):
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            event_data = line[5:].strip()

    try:
        parsed_data = json.loads(event_data) if event_data else {}
    except json.JSONDecodeError:
        parsed_data = {"raw": event_data}

    return {
        "event": event_type,
        "data": parsed_data,
    }


# Import asyncio at module level for type hints
import asyncio
