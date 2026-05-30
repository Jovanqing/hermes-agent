"""
Execution history tracking for workflows.

Records and retrieves past workflow executions:
- ExecutionRecord: Complete record of a single execution
- ExecutionHistory: Store and query execution records
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_default_db_path() -> Path:
    """Get the default database path."""
    try:
        from hermes_constants import get_hermes_home
        return get_hermes_home() / "execution_history.db"
    except (ImportError, TypeError):
        home = Path.home() / ".hermes"
        home.mkdir(parents=True, exist_ok=True)
        return home / "execution_history.db"


DEFAULT_DB_PATH = _get_default_db_path()


# ---------------------------------------------------------------------------
# Execution record
# ---------------------------------------------------------------------------


@dataclass
class ExecutionRecord:
    """A complete record of a workflow execution.

    Attributes:
        id: Unique execution ID
        workflow_id: The workflow that was executed
        workflow_name: Name of the workflow at execution time
        status: Final execution status
        started_at: When execution started
        completed_at: When execution finished
        duration: Total duration in seconds
        context_snapshot: Snapshot of the final context
        node_results: Results for each node
        error: Error message if failed
        input_variables: Variables provided at start
        metadata: Additional metadata
    """

    id: str
    workflow_id: str
    workflow_name: str = ""
    status: str = "unknown"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error: Optional[str] = None
    input_variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == "failed"

    @property
    def nodes_executed(self) -> int:
        """Get number of nodes executed."""
        return len(self.node_results)

    @property
    def nodes_successful(self) -> int:
        """Get number of successful nodes."""
        return sum(1 for r in self.node_results.values() if r.get("status") == "success")

    @property
    def nodes_failed(self) -> int:
        """Get number of failed nodes."""
        return sum(1 for r in self.node_results.values() if r.get("status") == "error")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "context_snapshot": self.context_snapshot,
            "node_results": self.node_results,
            "error": self.error,
            "input_variables": self.input_variables,
            "metadata": self.metadata,
            "nodes_executed": self.nodes_executed,
            "nodes_successful": self.nodes_successful,
            "nodes_failed": self.nodes_failed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionRecord:
        """Create from dictionary."""
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")

        return cls(
            id=data.get("id", ""),
            workflow_id=data.get("workflow_id", ""),
            workflow_name=data.get("workflow_name", ""),
            status=data.get("status", "unknown"),
            started_at=datetime.fromisoformat(started_at) if started_at else None,
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            duration=data.get("duration", 0.0),
            context_snapshot=data.get("context_snapshot", {}),
            node_results=data.get("node_results", {}),
            error=data.get("error"),
            input_variables=data.get("input_variables", {}),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS execution_history (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'unknown',
    started_at TEXT,
    completed_at TEXT,
    duration REAL NOT NULL DEFAULT 0.0,
    context_snapshot_json TEXT NOT NULL DEFAULT '{}',
    node_results_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    input_variables_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_execution_history_workflow
    ON execution_history(workflow_id);

CREATE INDEX IF NOT EXISTS idx_execution_history_status
    ON execution_history(status);

CREATE INDEX IF NOT EXISTS idx_execution_history_started
    ON execution_history(started_at DESC);
"""


# ---------------------------------------------------------------------------
# Execution history
# ---------------------------------------------------------------------------


class ExecutionHistory:
    """Stores and retrieves workflow execution records.

    Uses SQLite for persistent storage.

    Example:
        >>> history = ExecutionHistory()
        >>> history.record(execution_record)
        >>> recent = history.get_recent(limit=10)
        >>> by_workflow = history.get_by_workflow("workflow_123")
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the execution history store.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = self._get_conn()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    # -----------------------------------------------------------------------
    # Recording
    # -----------------------------------------------------------------------

    def record(self, execution: ExecutionRecord) -> None:
        """Record an execution.

        Args:
            execution: The execution record to store
        """
        conn = self._get_conn()

        conn.execute(
            """
            INSERT OR REPLACE INTO execution_history
                (id, workflow_id, workflow_name, status, started_at, completed_at,
                 duration, context_snapshot_json, node_results_json, error,
                 input_variables_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution.id,
                execution.workflow_id,
                execution.workflow_name,
                execution.status,
                execution.started_at.isoformat() if execution.started_at else None,
                execution.completed_at.isoformat() if execution.completed_at else None,
                execution.duration,
                json.dumps(execution.context_snapshot),
                json.dumps(execution.node_results),
                execution.error,
                json.dumps(execution.input_variables),
                json.dumps(execution.metadata),
            ),
        )
        conn.commit()

        logger.debug("Recorded execution %s", execution.id)

    def update(self, execution: ExecutionRecord) -> None:
        """Update an existing execution record.

        Args:
            execution: The execution record with updated data
        """
        # Same as record (uses INSERT OR REPLACE)
        self.record(execution)

    # -----------------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------------

    def get(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get an execution by ID.

        Args:
            execution_id: The execution ID

        Returns:
            ExecutionRecord or None if not found
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM execution_history WHERE id = ?",
            (execution_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_record(row)

    def get_recent(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ExecutionRecord]:
        """Get recent executions.

        Args:
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of ExecutionRecords
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT * FROM execution_history
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_by_workflow(
        self,
        workflow_id: str,
        limit: int = 20,
    ) -> List[ExecutionRecord]:
        """Get executions for a specific workflow.

        Args:
            workflow_id: The workflow ID
            limit: Maximum number of records

        Returns:
            List of ExecutionRecords
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT * FROM execution_history
            WHERE workflow_id = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_by_status(
        self,
        status: str,
        limit: int = 20,
    ) -> List[ExecutionRecord]:
        """Get executions by status.

        Args:
            status: The status to filter by
            limit: Maximum number of records

        Returns:
            List of ExecutionRecords
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT * FROM execution_history
            WHERE status = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (status, limit),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_failed(self, limit: int = 20) -> List[ExecutionRecord]:
        """Get failed executions."""
        return self.get_by_status("failed", limit)

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> List[ExecutionRecord]:
        """Search executions by workflow name or error message.

        Args:
            query: Search query
            limit: Maximum number of records

        Returns:
            List of matching ExecutionRecords
        """
        conn = self._get_conn()
        pattern = f"%{query}%"

        cursor = conn.execute(
            """
            SELECT * FROM execution_history
            WHERE workflow_name LIKE ? OR error LIKE ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (pattern, pattern, limit),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    # -----------------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------------

    def get_statistics(
        self,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get execution statistics.

        Args:
            workflow_id: Optional workflow to filter by

        Returns:
            Dictionary of statistics
        """
        conn = self._get_conn()

        if workflow_id:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(duration) as avg_duration,
                    MAX(duration) as max_duration,
                    MIN(duration) as min_duration
                FROM execution_history
                WHERE workflow_id = ?
                """,
                (workflow_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(duration) as avg_duration,
                    MAX(duration) as max_duration,
                    MIN(duration) as min_duration
                FROM execution_history
                """
            )

        row = cursor.fetchone()

        return {
            "total_executions": row["total"] or 0,
            "successful": row["successful"] or 0,
            "failed": row["failed"] or 0,
            "success_rate": (row["successful"] or 0) / max(row["total"] or 1, 1) * 100,
            "avg_duration": row["avg_duration"] or 0,
            "max_duration": row["max_duration"] or 0,
            "min_duration": row["min_duration"] or 0,
        }

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------

    def delete(self, execution_id: str) -> bool:
        """Delete an execution record.

        Args:
            execution_id: The execution ID

        Returns:
            True if deleted
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM execution_history WHERE id = ?",
            (execution_id,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def cleanup(
        self,
        older_than_days: int = 30,
        keep_recent: int = 100,
    ) -> int:
        """Clean up old execution records.

        Args:
            older_than_days: Delete records older than this
            keep_recent: Always keep this many recent records

        Returns:
            Number of records deleted
        """
        conn = self._get_conn()

        # Find records to delete (old AND not in recent N)
        cursor = conn.execute(
            """
            DELETE FROM execution_history
            WHERE id NOT IN (
                SELECT id FROM execution_history
                ORDER BY started_at DESC
                LIMIT ?
            )
            AND started_at < datetime('now', ?)
            """,
            (keep_recent, f"-{older_than_days} days"),
        )
        conn.commit()

        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Cleaned up %d old execution records", deleted)

        return deleted

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _row_to_record(self, row: sqlite3.Row) -> ExecutionRecord:
        """Convert a database row to an ExecutionRecord."""
        started_at = row["started_at"]
        completed_at = row["completed_at"]

        return ExecutionRecord(
            id=row["id"],
            workflow_id=row["workflow_id"],
            workflow_name=row["workflow_name"],
            status=row["status"],
            started_at=datetime.fromisoformat(started_at) if started_at else None,
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            duration=row["duration"],
            context_snapshot=json.loads(row["context_snapshot_json"]),
            node_results=json.loads(row["node_results_json"]),
            error=row["error"],
            input_variables=json.loads(row["input_variables_json"]),
            metadata=json.loads(row["metadata_json"]),
        )


# ---------------------------------------------------------------------------
# Default instance
# ---------------------------------------------------------------------------

_default_history: Optional[ExecutionHistory] = None


def get_default_history() -> ExecutionHistory:
    """Get the default execution history instance."""
    global _default_history
    if _default_history is None:
        _default_history = ExecutionHistory()
    return _default_history
