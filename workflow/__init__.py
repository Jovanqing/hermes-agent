"""
Workflow Management System for Hermes Agent.

Provides visual workflow creation and execution on an interactive canvas.
Each node represents a discrete AI agent execution, with edges defining
data flow and control between agents.

Key components:
- models.py: Data models for workflows, nodes, edges, and executions
- repository.py: SQLite-based persistence
- validation.py: Workflow graph validation
- exceptions.py: Custom exceptions
"""

from workflow.models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowContext,
    NodeOutput,
    WorkflowStatus,
    NodeType,
    ExecutionState,
    WorkflowExecution,
    Position,
    AgentNodeData,
    BranchNodeData,
    BranchCondition,
    NodeConfig,
)

from workflow.exceptions import (
    WorkflowError,
    WorkflowNotFoundError,
    WorkflowValidationError,
    WorkflowExecutionError,
    NodeExecutionError,
    CycleDetectedError,
)

from workflow.validation import validate_workflow

__all__ = [
    # Models
    "Workflow",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowContext",
    "NodeOutput",
    "WorkflowStatus",
    "NodeType",
    "ExecutionState",
    "WorkflowExecution",
    "Position",
    "AgentNodeData",
    "BranchNodeData",
    "BranchCondition",
    "NodeConfig",
    # Exceptions
    "WorkflowError",
    "WorkflowNotFoundError",
    "WorkflowValidationError",
    "WorkflowExecutionError",
    "NodeExecutionError",
    "CycleDetectedError",
    # Functions
    "validate_workflow",
]
