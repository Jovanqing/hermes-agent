"""
SQLite repository for the Workflow Management System.

Provides persistent storage for workflows and executions using SQLite
with WAL mode for concurrent access. Follows patterns from hermes_state.py.

Key features:
- WAL mode for concurrent readers + one writer
- JSON storage for complex nested structures
- Automatic schema migration
- Thread-safe connection management
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

from workflow.exceptions import (
    WorkflowExecutionNotFoundError,
    WorkflowNotFoundError,
)
from workflow.models import (
    ExecutionState,
    Workflow,
    WorkflowExecution,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)

# Schema version for migrations
SCHEMA_VERSION = 1


def _get_default_db_path() -> Path:
    """Get the default database path."""
    # Try to use hermes home if available
    try:
        from hermes_constants import get_hermes_home
        return get_hermes_home() / "workflows.db"
    except (ImportError, TypeError):
        # Fallback to ~/.hermes
        home = Path.home() / ".hermes"
        home.mkdir(parents=True, exist_ok=True)
        return home / "workflows.db"


# Default database path (computed at module load)
DEFAULT_DB_PATH = _get_default_db_path()

# WAL compatibility markers (same as hermes_state.py)
_WAL_INCOMPAT_MARKERS = (
    "locking protocol",
    "not authorized",
)


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------


SCHEMA_SQL = """
-- Workflows table: stores workflow definitions
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    nodes_json TEXT NOT NULL DEFAULT '[]',
    edges_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Index for listing workflows by status
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);

-- Index for searching by name
CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);

-- Workflow executions table: stores execution records
CREATE TABLE IF NOT EXISTS workflow_executions (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'idle',
    context_json TEXT NOT NULL DEFAULT '{}',
    current_node_ids_json TEXT NOT NULL DEFAULT '[]',
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);

-- Index for listing executions by workflow
CREATE INDEX IF NOT EXISTS idx_executions_workflow ON workflow_executions(workflow_id);

-- Index for listing executions by state
CREATE INDEX IF NOT EXISTS idx_executions_state ON workflow_executions(state);

-- Index for recent executions
CREATE INDEX IF NOT EXISTS idx_executions_created ON workflow_executions(created_at DESC);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""


# ---------------------------------------------------------------------------
# WorkflowRepository
# ---------------------------------------------------------------------------


class WorkflowRepository:
    """SQLite-based repository for workflow persistence.

    Provides CRUD operations for workflows and executions with
    thread-safe connection management and WAL mode support.

    Example:
        >>> repo = WorkflowRepository()
        >>> workflow = repo.create_workflow("My Workflow", description="...")
        >>> workflows = repo.list_workflows()
        >>> repo.delete_workflow(workflow.id)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the repository.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to ~/.hermes/workflows.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        self._wal_mode = True
        self._init_db()

    # -----------------------------------------------------------------------
    # Connection management
    # -----------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()
        return self._local.conn

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False,
        )

        # Configure connection
        conn.row_factory = sqlite3.Row

        # Try to enable WAL mode
        if self._wal_mode:
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError as e:
                if any(marker in str(e) for marker in _WAL_INCOMPAT_MARKERS):
                    logger.warning(
                        "WAL mode not supported on %s, falling back to DELETE mode",
                        self.db_path,
                    )
                    self._wal_mode = False
                    conn.execute("PRAGMA journal_mode=DELETE")
                else:
                    raise

        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys=ON")

        return conn

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database transactions."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # -----------------------------------------------------------------------
    # Database initialization
    # -----------------------------------------------------------------------

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._transaction() as conn:
            # Create tables
            conn.executescript(SCHEMA_SQL)

            # Check schema version
            cursor = conn.execute(
                "SELECT version FROM schema_version LIMIT 1"
            )
            row = cursor.fetchone()

            if row is None:
                # New database, set version
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            elif row["version"] < SCHEMA_VERSION:
                # Run migrations
                self._migrate_schema(conn, row["version"])

    def _migrate_schema(
        self,
        conn: sqlite3.Connection,
        from_version: int,
    ) -> None:
        """Run schema migrations.

        Args:
            conn: Database connection
            from_version: Current schema version
        """
        logger.info(
            "Migrating workflow schema from version %d to %d",
            from_version,
            SCHEMA_VERSION,
        )

        # Future migrations would go here
        # if from_version < 2:
        #     self._migrate_v1_to_v2(conn)

        # Update version
        conn.execute(
            "UPDATE schema_version SET version = ?",
            (SCHEMA_VERSION,),
        )

    # -----------------------------------------------------------------------
    # Workflow CRUD
    # -----------------------------------------------------------------------

    def create_workflow(
        self,
        name: str,
        description: str = "",
        nodes: Optional[list] = None,
        edges: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> Workflow:
        """Create a new workflow.

        Args:
            name: Workflow name
            description: Optional description
            nodes: Initial list of nodes
            edges: Initial list of edges
            metadata: Additional metadata

        Returns:
            The created Workflow object
        """
        now = datetime.now()
        workflow = Workflow(
            name=name,
            description=description,
            nodes=nodes or [],
            edges=edges or [],
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO workflows
                    (id, name, description, nodes_json, edges_json,
                     status, metadata_json, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow.id,
                    workflow.name,
                    workflow.description,
                    json.dumps([n.to_dict() for n in workflow.nodes]),
                    json.dumps([e.to_dict() for e in workflow.edges]),
                    workflow.status.value,
                    json.dumps(workflow.metadata),
                    workflow.version,
                    workflow.created_at.isoformat(),
                    workflow.updated_at.isoformat(),
                ),
            )

        logger.info("Created workflow '%s' (%s)", workflow.name, workflow.id)
        return workflow

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Get a workflow by ID.

        Args:
            workflow_id: The workflow ID

        Returns:
            The Workflow object

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM workflows WHERE id = ?",
            (workflow_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise WorkflowNotFoundError(workflow_id)

        return self._row_to_workflow(row)

    def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Workflow]:
        """List workflows with optional filtering.

        Args:
            status: Filter by status (None = all)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Workflow objects
        """
        conn = self._get_conn()

        if status:
            cursor = conn.execute(
                """
                SELECT * FROM workflows
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (status.value, limit, offset),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM workflows
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )

        return [self._row_to_workflow(row) for row in cursor.fetchall()]

    def update_workflow(self, workflow: Workflow) -> Workflow:
        """Update an existing workflow.

        Args:
            workflow: The workflow with updated data

        Returns:
            The updated Workflow object

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
        """
        # Verify exists
        self.get_workflow(workflow.id)

        workflow.updated_at = datetime.now()

        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE workflows SET
                    name = ?,
                    description = ?,
                    nodes_json = ?,
                    edges_json = ?,
                    status = ?,
                    metadata_json = ?,
                    version = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    workflow.name,
                    workflow.description,
                    json.dumps([n.to_dict() for n in workflow.nodes]),
                    json.dumps([e.to_dict() for e in workflow.edges]),
                    workflow.status.value,
                    json.dumps(workflow.metadata),
                    workflow.version,
                    workflow.updated_at.isoformat(),
                    workflow.id,
                ),
            )

        logger.info("Updated workflow '%s' (%s)", workflow.name, workflow.id)
        return workflow

    def delete_workflow(self, workflow_id: str) -> None:
        """Delete a workflow and its executions.

        Args:
            workflow_id: The workflow ID

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
        """
        # Verify exists
        self.get_workflow(workflow_id)

        with self._transaction() as conn:
            # Executions are deleted via CASCADE
            conn.execute(
                "DELETE FROM workflows WHERE id = ?",
                (workflow_id,),
            )

        logger.info("Deleted workflow %s", workflow_id)

    def search_workflows(self, query: str, limit: int = 20) -> list[Workflow]:
        """Search workflows by name or description.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching Workflow objects
        """
        conn = self._get_conn()
        search_pattern = f"%{query}%"

        cursor = conn.execute(
            """
            SELECT * FROM workflows
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (search_pattern, search_pattern, limit),
        )

        return [self._row_to_workflow(row) for row in cursor.fetchall()]

    # -----------------------------------------------------------------------
    # Execution CRUD
    # -----------------------------------------------------------------------

    def create_execution(
        self,
        workflow: Workflow,
        input_variables: Optional[dict] = None,
    ) -> WorkflowExecution:
        """Create a new execution for a workflow.

        Args:
            workflow: The workflow to execute
            input_variables: Variables to pass to the workflow

        Returns:
            The created WorkflowExecution object
        """
        from workflow.models import WorkflowContext

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            context=WorkflowContext(input_variables=input_variables or {}),
            workflow=workflow,
        )

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO workflow_executions
                    (id, workflow_id, state, context_json, current_node_ids_json,
                     error, started_at, completed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution.id,
                    execution.workflow_id,
                    execution.state.value,
                    json.dumps(execution.context.to_dict()),
                    json.dumps(list(execution.current_node_ids)),
                    execution.error,
                    execution.started_at.isoformat() if execution.started_at else None,
                    execution.completed_at.isoformat() if execution.completed_at else None,
                    execution.created_at.isoformat(),
                ),
            )

        logger.info(
            "Created execution %s for workflow %s",
            execution.id,
            workflow.id,
        )
        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution:
        """Get an execution by ID.

        Args:
            execution_id: The execution ID

        Returns:
            The WorkflowExecution object

        Raises:
            WorkflowExecutionNotFoundError: If execution doesn't exist
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM workflow_executions WHERE id = ?",
            (execution_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise WorkflowExecutionNotFoundError(execution_id)

        return self._row_to_execution(row)

    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        state: Optional[ExecutionState] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowExecution]:
        """List executions with optional filtering.

        Args:
            workflow_id: Filter by workflow ID
            state: Filter by state
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of WorkflowExecution objects
        """
        conn = self._get_conn()

        query = "SELECT * FROM workflow_executions WHERE 1=1"
        params: list[Any] = []

        if workflow_id:
            query += " AND workflow_id = ?"
            params.append(workflow_id)

        if state:
            query += " AND state = ?"
            params.append(state.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def update_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Update an execution record.

        Args:
            execution: The execution with updated data

        Returns:
            The updated WorkflowExecution object

        Raises:
            WorkflowExecutionNotFoundError: If execution doesn't exist
        """
        # Verify exists
        self.get_execution(execution.id)

        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE workflow_executions SET
                    state = ?,
                    context_json = ?,
                    current_node_ids_json = ?,
                    error = ?,
                    started_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    execution.state.value,
                    json.dumps(execution.context.to_dict()),
                    json.dumps(list(execution.current_node_ids)),
                    execution.error,
                    execution.started_at.isoformat() if execution.started_at else None,
                    execution.completed_at.isoformat() if execution.completed_at else None,
                    execution.id,
                ),
            )

        return execution

    def delete_execution(self, execution_id: str) -> None:
        """Delete an execution record.

        Args:
            execution_id: The execution ID

        Raises:
            WorkflowExecutionNotFoundError: If execution doesn't exist
        """
        # Verify exists
        self.get_execution(execution_id)

        with self._transaction() as conn:
            conn.execute(
                "DELETE FROM workflow_executions WHERE id = ?",
                (execution_id,),
            )

        logger.info("Deleted execution %s", execution_id)

    def get_active_executions(self) -> list[WorkflowExecution]:
        """Get all currently active (non-terminal) executions.

        Returns:
            List of active WorkflowExecution objects
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT * FROM workflow_executions
            WHERE state IN ('idle', 'running', 'paused', 'waiting_input')
            ORDER BY created_at DESC
            """,
        )
        return [self._row_to_execution(row) for row in cursor.fetchall()]

    # -----------------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------------

    def _row_to_workflow(self, row: sqlite3.Row) -> Workflow:
        """Convert a database row to a Workflow object."""
        from workflow.models import WorkflowEdge, WorkflowNode

        nodes_data = json.loads(row["nodes_json"])
        edges_data = json.loads(row["edges_json"])

        return Workflow(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            nodes=[WorkflowNode.from_dict(n) for n in nodes_data],
            edges=[WorkflowEdge.from_dict(e) for e in edges_data],
            status=WorkflowStatus(row["status"]),
            metadata=json.loads(row["metadata_json"]),
            version=row["version"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_execution(self, row: sqlite3.Row) -> WorkflowExecution:
        """Convert a database row to a WorkflowExecution object."""
        from workflow.models import WorkflowContext

        context_data = json.loads(row["context_json"])
        current_nodes = json.loads(row["current_node_ids_json"])

        started_at = row["started_at"]
        completed_at = row["completed_at"]

        return WorkflowExecution(
            id=row["id"],
            workflow_id=row["workflow_id"],
            state=ExecutionState(row["state"]),
            context=WorkflowContext.from_dict(context_data),
            current_node_ids=set(current_nodes),
            error=row["error"],
            started_at=datetime.fromisoformat(started_at) if started_at else None,
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_repo: Optional[WorkflowRepository] = None
_default_repo_lock = threading.Lock()


def get_default_repository() -> WorkflowRepository:
    """Get the default workflow repository singleton.

    Returns:
        The default WorkflowRepository instance
    """
    global _default_repo
    with _default_repo_lock:
        if _default_repo is None:
            _default_repo = WorkflowRepository()
        return _default_repo
