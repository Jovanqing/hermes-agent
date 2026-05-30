"""
Data models for the Workflow Management System.

Defines the core data structures used throughout the workflow system:
- Workflow: Container for nodes and edges
- WorkflowNode: Individual processing units (agent, branch, input, output)
- WorkflowEdge: Connections between nodes
- WorkflowContext: Shared state during execution
- WorkflowExecution: Runtime state for a workflow run
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class WorkflowStatus(str, Enum):
    """Lifecycle status of a workflow definition."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class NodeType(str, Enum):
    """Types of nodes that can appear in a workflow."""

    AGENT = "agent"
    BRANCH = "branch"
    INPUT = "input"
    OUTPUT = "output"
    TRANSFORM = "transform"


class ExecutionState(str, Enum):
    """Runtime states for a workflow execution."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeExecutionStatus(str, Enum):
    """Execution status for individual node outputs."""

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    PENDING = "pending"
    RUNNING = "running"


# ---------------------------------------------------------------------------
# Position & Geometry
# ---------------------------------------------------------------------------


@dataclass
class Position:
    """Canvas position for a workflow node."""

    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Position:
        return cls(x=data.get("x", 0.0), y=data.get("y", 0.0))


# ---------------------------------------------------------------------------
# Node Data Types
# ---------------------------------------------------------------------------


@dataclass
class AgentNodeData:
    """Configuration for an agent execution node.

    Attributes:
        prompt: The prompt template to send to the LLM.
                May contain {{variable}} placeholders resolved from context.
        model: Model identifier (e.g., 'claude-3-opus', 'gpt-4', 'hermes-3')
        temperature: Sampling temperature for the LLM (0.0 - 2.0)
        max_tokens: Maximum tokens to generate
        tools: List of tool names available to this agent
        input_mapping: Maps prompt variables to context sources
                       e.g., {"user_input": "input_node_1.output"}
    """

    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[str] = field(default_factory=list)
    input_mapping: dict[str, str] = field(default_factory=dict)
    system_prompt: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": self.tools,
            "input_mapping": self.input_mapping,
            "system_prompt": self.system_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentNodeData:
        return cls(
            prompt=data.get("prompt", ""),
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            tools=data.get("tools", []),
            input_mapping=data.get("input_mapping", {}),
            system_prompt=data.get("system_prompt"),
        )


@dataclass
class BranchCondition:
    """A single condition in a branch node.

    Attributes:
        id: Unique identifier for this condition
        output_port: Name of the output port if condition matches
        evaluator_type: How to evaluate the condition
        evaluator_config: Configuration specific to the evaluator type
    """

    id: str
    output_port: str
    evaluator_type: Literal["prompt", "regex", "json_path"]
    evaluator_config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "output_port": self.output_port,
            "evaluator_type": self.evaluator_type,
            "evaluator_config": self.evaluator_config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BranchCondition:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            output_port=data.get("output_port", "default"),
            evaluator_type=data.get("evaluator_type", "prompt"),
            evaluator_config=data.get("evaluator_config", {}),
        )


@dataclass
class BranchNodeData:
    """Configuration for a branch/conditional node.

    Branch nodes evaluate conditions and route execution to different
    output ports based on the result.

    Attributes:
        conditions: List of conditions to evaluate (first match wins)
        default_output: Output port if no condition matches
    """

    conditions: list[BranchCondition] = field(default_factory=list)
    default_output: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "conditions": [c.to_dict() for c in self.conditions],
            "default_output": self.default_output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BranchNodeData:
        conditions = [
            BranchCondition.from_dict(c) for c in data.get("conditions", [])
        ]
        return cls(
            conditions=conditions,
            default_output=data.get("default_output", "default"),
        )


@dataclass
class InputNodeData:
    """Configuration for an input node (workflow entry point).

    Input nodes define the initial variables available to the workflow.

    Attributes:
        variables: Dictionary of variable name -> default value
        required: List of variable names that must be provided at execution
    """

    variables: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": self.variables,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InputNodeData:
        return cls(
            variables=data.get("variables", {}),
            required=data.get("required", []),
        )


@dataclass
class OutputNodeData:
    """Configuration for an output node (workflow result).

    Output nodes define what data is returned when the workflow completes.

    Attributes:
        output_mapping: Maps output keys to context sources
        format: Optional output format ('json', 'text', 'markdown')
    """

    output_mapping: dict[str, str] = field(default_factory=dict)
    format: Literal["json", "text", "markdown"] = "json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_mapping": self.output_mapping,
            "format": self.format,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutputNodeData:
        return cls(
            output_mapping=data.get("output_mapping", {}),
            format=data.get("format", "json"),
        )


@dataclass
class TransformNodeData:
    """Configuration for a transform node.

    Transform nodes apply simple transformations to context data
    without invoking an LLM.

    Attributes:
        transform_type: Type of transformation ('template', 'json_path', 'script')
        transform_config: Configuration for the transformation
    """

    transform_type: Literal["template", "json_path", "script"]
    transform_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transform_type": self.transform_type,
            "transform_config": self.transform_config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransformNodeData:
        return cls(
            transform_type=data.get("transform_type", "template"),
            transform_config=data.get("transform_config", {}),
        )


# Union type for all node data types
NodeData = Union[AgentNodeData, BranchNodeData, InputNodeData, OutputNodeData, TransformNodeData]


# ---------------------------------------------------------------------------
# Node Configuration
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    """Configuration for node retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts
        delay_seconds: Base delay between retries
        exponential_backoff: If True, delay doubles with each retry
        retry_on_errors: List of error types to retry (empty = retry all)
    """

    max_retries: int = 0
    delay_seconds: float = 1.0
    exponential_backoff: bool = True
    retry_on_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "delay_seconds": self.delay_seconds,
            "exponential_backoff": self.exponential_backoff,
            "retry_on_errors": self.retry_on_errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetryPolicy:
        return cls(
            max_retries=data.get("max_retries", 0),
            delay_seconds=data.get("delay_seconds", 1.0),
            exponential_backoff=data.get("exponential_backoff", True),
            retry_on_errors=data.get("retry_on_errors", []),
        )


@dataclass
class NodeConfig:
    """Configuration options for a workflow node.

    Attributes:
        retry_policy: How to handle failures
        timeout: Maximum execution time in seconds
        parallel: If True, can execute in parallel with sibling nodes
        breakpoint: If True, pause execution before this node
    """

    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout: float = 300.0  # 5 minutes default
    parallel: bool = False
    breakpoint: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "retry_policy": self.retry_policy.to_dict(),
            "timeout": self.timeout,
            "parallel": self.parallel,
            "breakpoint": self.breakpoint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeConfig:
        retry_data = data.get("retry_policy", {})
        if isinstance(retry_data, dict):
            retry_policy = RetryPolicy.from_dict(retry_data)
        else:
            retry_policy = RetryPolicy()

        return cls(
            retry_policy=retry_policy,
            timeout=data.get("timeout", 300.0),
            parallel=data.get("parallel", False),
            breakpoint=data.get("breakpoint", False),
        )


# ---------------------------------------------------------------------------
# Workflow Node
# ---------------------------------------------------------------------------


@dataclass
class WorkflowNode:
    """A node in a workflow graph.

    Attributes:
        id: Unique identifier for this node
        type: The type of node (agent, branch, input, output, transform)
        position: Canvas position for UI rendering
        data: Type-specific configuration data
        config: Execution configuration (retry, timeout, etc.)
        name: Human-readable name for the node
        description: Optional description of what this node does
    """

    id: str
    type: NodeType
    position: Position
    data: Union[NodeData, dict[str, Any]]
    config: NodeConfig = field(default_factory=NodeConfig)
    name: str = ""
    description: str = ""

    def get_typed_data(self) -> NodeData:
        """Convert raw dict data to the appropriate typed dataclass."""
        if isinstance(self.data, dict):
            if self.type == NodeType.AGENT:
                return AgentNodeData.from_dict(self.data)
            elif self.type == NodeType.BRANCH:
                return BranchNodeData.from_dict(self.data)
            elif self.type == NodeType.INPUT:
                return InputNodeData.from_dict(self.data)
            elif self.type == NodeType.OUTPUT:
                return OutputNodeData.from_dict(self.data)
            elif self.type == NodeType.TRANSFORM:
                return TransformNodeData.from_dict(self.data)
        return self.data

    def to_dict(self) -> dict[str, Any]:
        data = self.data
        if hasattr(data, "to_dict"):
            data = data.to_dict()

        return {
            "id": self.id,
            "type": self.type.value,
            "position": self.position.to_dict(),
            "data": data,
            "config": self.config.to_dict(),
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowNode:
        node_type = NodeType(data.get("type", "agent"))

        # Parse data based on type
        raw_data = data.get("data", {})
        if node_type == NodeType.AGENT:
            typed_data = AgentNodeData.from_dict(raw_data) if isinstance(raw_data, dict) else raw_data
        elif node_type == NodeType.BRANCH:
            typed_data = BranchNodeData.from_dict(raw_data) if isinstance(raw_data, dict) else raw_data
        elif node_type == NodeType.INPUT:
            typed_data = InputNodeData.from_dict(raw_data) if isinstance(raw_data, dict) else raw_data
        elif node_type == NodeType.OUTPUT:
            typed_data = OutputNodeData.from_dict(raw_data) if isinstance(raw_data, dict) else raw_data
        elif node_type == NodeType.TRANSFORM:
            typed_data = TransformNodeData.from_dict(raw_data) if isinstance(raw_data, dict) else raw_data
        else:
            typed_data = raw_data

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=node_type,
            position=Position.from_dict(data.get("position", {})),
            data=typed_data,
            config=NodeConfig.from_dict(data.get("config", {})),
            name=data.get("name", ""),
            description=data.get("description", ""),
        )


# ---------------------------------------------------------------------------
# Workflow Edge
# ---------------------------------------------------------------------------


@dataclass
class EdgeCondition:
    """Optional condition on an edge that must be satisfied for traversal.

    Attributes:
        variable: Context variable to check
        operator: Comparison operator
        value: Value to compare against
    """

    variable: str
    operator: Literal["eq", "ne", "gt", "lt", "gte", "lte", "contains", "exists"]
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "operator": self.operator,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EdgeCondition:
        return cls(
            variable=data.get("variable", ""),
            operator=data.get("operator", "exists"),
            value=data.get("value"),
        )


@dataclass
class WorkflowEdge:
    """A connection between two nodes in a workflow.

    Attributes:
        id: Unique identifier for this edge
        source: Source node ID
        source_port: Output port on source node (for branch nodes)
        target: Target node ID
        target_port: Input port on target node
        condition: Optional condition that must be satisfied
        label: Optional label for UI display
    """

    id: str
    source: str
    target: str
    source_port: str = "default"
    target_port: str = "input"
    condition: Optional[EdgeCondition] = None
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_port": self.source_port,
            "target": self.target,
            "target_port": self.target_port,
            "condition": self.condition.to_dict() if self.condition else None,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowEdge:
        condition_data = data.get("condition")
        condition = (
            EdgeCondition.from_dict(condition_data)
            if condition_data
            else None
        )

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source=data.get("source", ""),
            target=data.get("target", ""),
            source_port=data.get("source_port", "default"),
            target_port=data.get("target_port", "input"),
            condition=condition,
            label=data.get("label", ""),
        )


# ---------------------------------------------------------------------------
# Node Output & Context
# ---------------------------------------------------------------------------


@dataclass
class NodeOutput:
    """Result of executing a single workflow node.

    Attributes:
        node_id: ID of the node that produced this output
        output: The output data (text, JSON, etc.)
        tokens: Token usage statistics
        duration: Execution time in seconds
        status: Execution status
        error: Error message if status is ERROR
        started_at: When execution started
        completed_at: When execution completed
    """

    node_id: str
    output: Any
    tokens: dict[str, int] = field(default_factory=lambda: {"prompt": 0, "completion": 0})
    duration: float = 0.0
    status: NodeExecutionStatus = NodeExecutionStatus.PENDING
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "output": self.output,
            "tokens": self.tokens,
            "duration": self.duration,
            "status": self.status.value,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeOutput:
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")

        return cls(
            node_id=data.get("node_id", ""),
            output=data.get("output"),
            tokens=data.get("tokens", {"prompt": 0, "completion": 0}),
            duration=data.get("duration", 0.0),
            status=NodeExecutionStatus(data.get("status", "pending")),
            error=data.get("error"),
            started_at=datetime.fromisoformat(started_at) if started_at else None,
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
        )


@dataclass
class WorkflowContext:
    """Shared state accumulated during workflow execution.

    The context grows as nodes complete, storing their outputs and
    any variables defined during execution.

    Attributes:
        variables: User-defined and computed variables
        node_outputs: Map of node ID -> output for completed nodes
        execution_history: Ordered list of executed node IDs
        input_variables: Variables provided at workflow start
    """

    variables: dict[str, Any] = field(default_factory=dict)
    node_outputs: dict[str, NodeOutput] = field(default_factory=dict)
    execution_history: list[str] = field(default_factory=list)
    input_variables: dict[str, Any] = field(default_factory=dict)

    def get_node_output(self, node_id: str) -> Optional[NodeOutput]:
        """Get the output of a specific node."""
        return self.node_outputs.get(node_id)

    def set_variable(self, name: str, value: Any) -> None:
        """Set a context variable."""
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.variables.get(name, default)

    def record_node_execution(self, node_id: str, output: NodeOutput) -> None:
        """Record a completed node execution."""
        self.node_outputs[node_id] = output
        if node_id not in self.execution_history:
            self.execution_history.append(node_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": self.variables,
            "node_outputs": {k: v.to_dict() for k, v in self.node_outputs.items()},
            "execution_history": self.execution_history,
            "input_variables": self.input_variables,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowContext:
        node_outputs = {
            k: NodeOutput.from_dict(v)
            for k, v in data.get("node_outputs", {}).items()
        }
        return cls(
            variables=data.get("variables", {}),
            node_outputs=node_outputs,
            execution_history=data.get("execution_history", []),
            input_variables=data.get("input_variables", {}),
        )


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


def _generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


@dataclass
class Workflow:
    """A complete workflow definition.

    A workflow is a directed acyclic graph (DAG) of nodes connected by edges.
    It can be executed to produce results.

    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Optional description
        nodes: List of nodes in the workflow
        edges: List of edges connecting nodes
        status: Lifecycle status
        created_at: When the workflow was created
        updated_at: When the workflow was last modified
        version: Schema version for migrations
        metadata: Additional metadata (tags, author, etc.)
    """

    id: str = field(default_factory=_generate_id)
    name: str = ""
    description: str = ""
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_edge(self, edge_id: str) -> Optional[WorkflowEdge]:
        """Get an edge by ID."""
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None

    def get_incoming_edges(self, node_id: str) -> list[WorkflowEdge]:
        """Get all edges targeting a node."""
        return [e for e in self.edges if e.target == node_id]

    def get_outgoing_edges(self, node_id: str) -> list[WorkflowEdge]:
        """Get all edges originating from a node."""
        return [e for e in self.edges if e.source == node_id]

    def get_entry_nodes(self) -> list[WorkflowNode]:
        """Get nodes with no incoming edges (entry points)."""
        targets = {e.target for e in self.edges}
        return [n for n in self.nodes if n.id not in targets]

    def get_exit_nodes(self) -> list[WorkflowNode]:
        """Get nodes with no outgoing edges (exit points)."""
        sources = {e.source for e in self.edges}
        return [n for n in self.nodes if n.id not in sources]

    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the workflow."""
        self.nodes.append(node)
        self.updated_at = datetime.now()

    def remove_node(self, node_id: str) -> None:
        """Remove a node and its connected edges."""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.edges = [
            e for e in self.edges
            if e.source != node_id and e.target != node_id
        ]
        self.updated_at = datetime.now()

    def add_edge(self, edge: WorkflowEdge) -> None:
        """Add an edge to the workflow."""
        self.edges.append(edge)
        self.updated_at = datetime.now()

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the workflow."""
        self.edges = [e for e in self.edges if e.id != edge_id]
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Workflow:
        nodes = [WorkflowNode.from_dict(n) for n in data.get("nodes", [])]
        edges = [WorkflowEdge.from_dict(e) for e in data.get("edges", [])]

        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        return cls(
            id=data.get("id", _generate_id()),
            name=data.get("name", ""),
            description=data.get("description", ""),
            nodes=nodes,
            edges=edges,
            status=WorkflowStatus(data.get("status", "draft")),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
            updated_at=datetime.fromisoformat(updated_at) if updated_at else datetime.now(),
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Workflow Execution
# ---------------------------------------------------------------------------


@dataclass
class WorkflowExecution:
    """Runtime state for a workflow execution.

    Tracks the progress and state of a single workflow run.

    Attributes:
        id: Unique execution identifier
        workflow_id: ID of the workflow being executed
        state: Current execution state
        context: Accumulated execution context
        current_node_ids: IDs of currently executing nodes (for parallel)
        started_at: When execution started
        completed_at: When execution finished (success or failure)
        error: Error message if execution failed
        created_at: When the execution record was created
    """

    id: str = field(default_factory=_generate_id)
    workflow_id: str = ""
    state: ExecutionState = ExecutionState.IDLE
    context: WorkflowContext = field(default_factory=WorkflowContext)
    current_node_ids: set[str] = field(default_factory=set)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Reference to the workflow definition (not persisted)
    workflow: Optional[Workflow] = field(default=None, repr=False)

    def is_terminal(self) -> bool:
        """Check if execution is in a terminal state."""
        return self.state in (
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        )

    def is_active(self) -> bool:
        """Check if execution is currently running or paused."""
        return self.state in (
            ExecutionState.RUNNING,
            ExecutionState.PAUSED,
            ExecutionState.WAITING_INPUT,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "state": self.state.value,
            "context": self.context.to_dict(),
            "current_node_ids": list(self.current_node_ids),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowExecution:
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")
        created_at = data.get("created_at")

        return cls(
            id=data.get("id", _generate_id()),
            workflow_id=data.get("workflow_id", ""),
            state=ExecutionState(data.get("state", "idle")),
            context=WorkflowContext.from_dict(data.get("context", {})),
            current_node_ids=set(data.get("current_node_ids", [])),
            started_at=datetime.fromisoformat(started_at) if started_at else None,
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            error=data.get("error"),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
        )
