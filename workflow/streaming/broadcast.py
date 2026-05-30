"""
Event broadcaster for workflow execution streaming.

Manages SSE connections and broadcasts events to connected clients.
Integrates with the hermes-agent gateway API server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set

from workflow.streaming.handler import (
    StreamEvent,
    StreamEventType,
    StreamHandler,
    format_sse_comment,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Broadcast subscription
# ---------------------------------------------------------------------------


@dataclass
class BroadcastSubscription:
    """A subscription to execution events.

    Attributes:
        execution_id: The execution being subscribed to
        client_id: Unique identifier for this subscription
        connected_at: When the subscription was created
        last_event_at: When the last event was received
    """

    execution_id: str
    client_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    last_event_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Event broadcaster
# ---------------------------------------------------------------------------


class EventBroadcaster:
    """Broadcasts workflow execution events to connected clients.

    Manages:
    - Active execution handlers
    - Client subscriptions
    - SSE response streams

    Example:
        >>> broadcaster = EventBroadcaster()
        >>> handler = broadcaster.create_handler(execution_id)
        >>> # In your aiohttp handler:
        >>> async def sse_handler(request):
        ...     response = web.StreamResponse(...)
        ...     async for event in broadcaster.subscribe(execution_id):
        ...         await response.write(event.to_sse().encode())
    """

    def __init__(
        self,
        max_handlers: int = 100,
        handler_ttl_seconds: int = 3600,
    ):
        """Initialize the broadcaster.

        Args:
            max_handlers: Maximum concurrent execution handlers
            handler_ttl_seconds: How long to keep handlers after completion
        """
        self.max_handlers = max_handlers
        self.handler_ttl_seconds = handler_ttl_seconds

        self._handlers: Dict[str, StreamHandler] = {}
        self._handler_created_at: Dict[str, datetime] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # execution_id -> client_ids
        self._subscription_details: Dict[str, BroadcastSubscription] = {}

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    def start_cleanup_loop(self, interval_seconds: int = 60) -> None:
        """Start the background cleanup loop.

        Args:
            interval_seconds: How often to run cleanup
        """
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(
                self._cleanup_loop(interval_seconds)
            )

    def stop_cleanup_loop(self) -> None:
        """Stop the background cleanup loop."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def _cleanup_loop(self, interval_seconds: int) -> None:
        """Background loop to clean up expired handlers."""
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                self._cleanup_expired_handlers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Cleanup loop error: %s", e)

    def _cleanup_expired_handlers(self) -> None:
        """Remove handlers that have been completed for too long."""
        now = datetime.now()
        to_remove = []

        for execution_id, handler in self._handlers.items():
            if handler.is_closed:
                created_at = self._handler_created_at.get(execution_id, now)
                age = (now - created_at).total_seconds()
                if age > self.handler_ttl_seconds:
                    to_remove.append(execution_id)

        for execution_id in to_remove:
            self._remove_handler(execution_id)
            logger.debug("Cleaned up handler for execution %s", execution_id)

    def _remove_handler(self, execution_id: str) -> None:
        """Remove a handler and its subscriptions."""
        if execution_id in self._handlers:
            self._handlers[execution_id].close()
            del self._handlers[execution_id]

        if execution_id in self._handler_created_at:
            del self._handler_created_at[execution_id]

        if execution_id in self._subscriptions:
            # Clean up subscription details
            for client_id in self._subscriptions[execution_id]:
                sub_key = f"{execution_id}:{client_id}"
                if sub_key in self._subscription_details:
                    del self._subscription_details[sub_key]
            del self._subscriptions[execution_id]

    # -----------------------------------------------------------------------
    # Handler management
    # -----------------------------------------------------------------------

    def create_handler(self, execution_id: str) -> StreamHandler:
        """Create a new stream handler for an execution.

        Args:
            execution_id: The execution ID

        Returns:
            StreamHandler for the execution

        Raises:
            ValueError: If max handlers exceeded
        """
        if len(self._handlers) >= self.max_handlers:
            # Try to clean up first
            self._cleanup_expired_handlers()
            if len(self._handlers) >= self.max_handlers:
                raise ValueError(
                    f"Maximum concurrent handlers ({self.max_handlers}) exceeded"
                )

        if execution_id in self._handlers:
            return self._handlers[execution_id]

        handler = StreamHandler(execution_id)
        self._handlers[execution_id] = handler
        self._handler_created_at[execution_id] = datetime.now()
        self._subscriptions[execution_id] = set()

        logger.debug("Created stream handler for execution %s", execution_id)
        return handler

    def get_handler(self, execution_id: str) -> Optional[StreamHandler]:
        """Get an existing handler.

        Args:
            execution_id: The execution ID

        Returns:
            StreamHandler or None if not found
        """
        return self._handlers.get(execution_id)

    def emit(
        self,
        execution_id: str,
        event: StreamEvent,
    ) -> None:
        """Emit an event for an execution.

        Args:
            execution_id: The execution ID
            event: The event to emit
        """
        handler = self._handlers.get(execution_id)
        if handler:
            handler.emit(event)

    def close_handler(self, execution_id: str) -> None:
        """Close a handler (marks it for cleanup).

        Args:
            execution_id: The execution ID
        """
        handler = self._handlers.get(execution_id)
        if handler:
            handler.close()
            # Update created_at so TTL is measured from close time
            self._handler_created_at[execution_id] = datetime.now()

    # -----------------------------------------------------------------------
    # Subscription management
    # -----------------------------------------------------------------------

    @asynccontextmanager
    async def subscribe(
        self,
        execution_id: str,
        client_id: str,
        include_history: bool = True,
    ) -> AsyncIterator[AsyncIterator[StreamEvent]]:
        """Subscribe to execution events.

        Args:
            execution_id: The execution to subscribe to
            client_id: Unique client identifier
            include_history: Whether to include past events

        Yields:
            AsyncIterator of StreamEvents
        """
        handler = self._handlers.get(execution_id)
        if not handler:
            raise ValueError(f"No handler for execution {execution_id}")

        # Register subscription
        sub_key = f"{execution_id}:{client_id}"
        self._subscriptions[execution_id].add(client_id)
        self._subscription_details[sub_key] = BroadcastSubscription(
            execution_id=execution_id,
            client_id=client_id,
        )

        logger.debug(
            "Client %s subscribed to execution %s",
            client_id,
            execution_id,
        )

        try:
            async for event in handler.subscribe(include_history=include_history):
                # Update last event time
                if sub_key in self._subscription_details:
                    self._subscription_details[sub_key].last_event_at = datetime.now()
                yield event

        finally:
            # Unregister subscription
            self._subscriptions[execution_id].discard(client_id)
            if sub_key in self._subscription_details:
                del self._subscription_details[sub_key]

            logger.debug(
                "Client %s unsubscribed from execution %s",
                client_id,
                execution_id,
            )

    def get_subscriber_count(self, execution_id: str) -> int:
        """Get the number of active subscribers for an execution.

        Args:
            execution_id: The execution ID

        Returns:
            Number of active subscribers
        """
        return len(self._subscriptions.get(execution_id, set()))

    def get_active_executions(self) -> List[str]:
        """Get list of executions with active handlers.

        Returns:
            List of execution IDs
        """
        return list(self._handlers.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get broadcaster statistics.

        Returns:
            Dict with statistics
        """
        total_subscribers = sum(
            len(subs) for subs in self._subscriptions.values()
        )
        active_handlers = sum(
            1 for h in self._handlers.values() if not h.is_closed
        )

        return {
            "total_handlers": len(self._handlers),
            "active_handlers": active_handlers,
            "closed_handlers": len(self._handlers) - active_handlers,
            "total_subscribers": total_subscribers,
            "max_handlers": self.max_handlers,
        }


# ---------------------------------------------------------------------------
# aiohttp SSE handler helper
# ---------------------------------------------------------------------------


try:
    from aiohttp import web

    async def create_sse_response(
        request: web.Request,
        broadcaster: EventBroadcaster,
        execution_id: str,
        client_id: Optional[str] = None,
        include_history: bool = True,
    ) -> web.StreamResponse:
        """Create an SSE response for workflow streaming.

        Args:
            request: The aiohttp request
            broadcaster: The event broadcaster
            execution_id: The execution to stream
            client_id: Optional client ID (generated if None)
            include_history: Whether to include past events

        Returns:
            aiohttp StreamResponse
        """
        import uuid

        if client_id is None:
            client_id = str(uuid.uuid4())

        # Create streaming response
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",
            },
        )
        await response.prepare(request)

        # Send initial comment
        await response.write(
            format_sse_comment(f"Connected to execution {execution_id}").encode()
        )

        try:
            async with broadcaster.subscribe(
                execution_id,
                client_id,
                include_history=include_history,
            ) as events:
                async for event in events:
                    # Check if client disconnected
                    if request.transport is None:
                        break

                    await response.write(event.to_sse().encode())

        except ValueError as e:
            # Execution not found
            error_event = StreamEvent.error(
                execution_id=execution_id,
                error=str(e),
                error_type="not_found",
            )
            await response.write(error_event.to_sse().encode())

        except asyncio.CancelledError:
            pass

        finally:
            await response.write_eof()

        return response

except ImportError:
    # aiohttp not available
    pass


# ---------------------------------------------------------------------------
# Global broadcaster instance
# ---------------------------------------------------------------------------

_default_broadcaster: Optional[EventBroadcaster] = None


def get_default_broadcaster() -> EventBroadcaster:
    """Get the default global broadcaster instance.

    Returns:
        The default EventBroadcaster
    """
    global _default_broadcaster
    if _default_broadcaster is None:
        _default_broadcaster = EventBroadcaster()
        _default_broadcaster.start_cleanup_loop()
    return _default_broadcaster
