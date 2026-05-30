"""
Workflow validation for the Workflow Management System.

Validates workflow definitions before execution:
- Checks for cycles in the graph (must be a DAG)
- Validates node configurations
- Validates edge references
- Ensures entry and exit nodes exist
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any, Optional

from workflow.exceptions import (
    CycleDetectedError,
    InvalidEdgeError,
    InvalidNodeError,
    MissingEntryNodeError,
    WorkflowValidationError,
)
from workflow.models import (
    AgentNodeData,
    BranchNodeData,
    InputNodeData,
    NodeType,
    OutputNodeData,
    TransformNodeData,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


class ValidationResult:
    """Result of workflow validation.

    Attributes:
        is_valid: Whether the workflow passed all validations
        errors: List of validation errors found
        warnings: List of non-fatal warnings
    """

    def __init__(self):
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(
        self,
        error_type: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Add a validation error."""
        self.errors.append({
            "type": error_type,
            "message": message,
            **kwargs,
        })

    def add_warning(
        self,
        warning_type: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Add a validation warning."""
        self.warnings.append({
            "type": warning_type,
            "message": message,
            **kwargs,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def __str__(self) -> str:
        if self.is_valid:
            return "Validation passed"
        error_msgs = [e["message"] for e in self.errors]
        return f"Validation failed: {'; '.join(error_msgs)}"


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------


def validate_workflow(
    workflow: Workflow,
    strict: bool = True,
) -> ValidationResult:
    """Validate a workflow definition.

    Args:
        workflow: The workflow to validate
        strict: If True, fail on warnings too

    Returns:
        ValidationResult with errors and warnings

    Raises:
        WorkflowValidationError: If validation fails and raise_on_error is True
    """
    result = ValidationResult()

    # Run all validations
    _validate_basic_structure(workflow, result)
    _validate_nodes(workflow, result)
    _validate_edges(workflow, result)
    _validate_graph_structure(workflow, result)
    _validate_node_connections(workflow, result)

    # Check for cycles last (most expensive)
    _validate_no_cycles(workflow, result)

    if not result.is_valid:
        logger.warning(
            "Workflow validation failed for '%s': %d errors",
            workflow.name or workflow.id,
            len(result.errors),
        )

    return result


def validate_workflow_or_raise(workflow: Workflow) -> None:
    """Validate a workflow and raise on failure.

    Args:
        workflow: The workflow to validate

    Raises:
        WorkflowValidationError: If validation fails
        CycleDetectedError: If the graph contains cycles
    """
    result = validate_workflow(workflow)

    if not result.is_valid:
        # Check for cycle error specifically
        for error in result.errors:
            if error["type"] == "cycle":
                raise CycleDetectedError(error.get("nodes", []))

        raise WorkflowValidationError(
            message="Workflow validation failed",
            errors=result.errors,
        )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_basic_structure(workflow: Workflow, result: ValidationResult) -> None:
    """Validate basic workflow structure."""
    # Must have a name
    if not workflow.name:
        result.add_warning(
            "missing_name",
            "Workflow has no name",
        )

    # Must have at least one node
    if not workflow.nodes:
        result.add_error(
            "empty_workflow",
            "Workflow has no nodes",
        )
        return

    # Check for duplicate node IDs
    node_ids = [n.id for n in workflow.nodes]
    duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
    if duplicates:
        result.add_error(
            "duplicate_node_ids",
            f"Duplicate node IDs found: {set(duplicates)}",
            node_ids=list(set(duplicates)),
        )

    # Check for duplicate edge IDs
    edge_ids = [e.id for e in workflow.edges]
    duplicates = [eid for eid in edge_ids if edge_ids.count(eid) > 1]
    if duplicates:
        result.add_error(
            "duplicate_edge_ids",
            f"Duplicate edge IDs found: {set(duplicates)}",
            edge_ids=list(set(duplicates)),
        )


def _validate_nodes(workflow: Workflow, result: ValidationResult) -> None:
    """Validate individual node configurations."""
    for node in workflow.nodes:
        _validate_single_node(node, result)


def _validate_single_node(node: WorkflowNode, result: ValidationResult) -> None:
    """Validate a single node's configuration."""
    # Check required fields
    if not node.id:
        result.add_error(
            "missing_node_id",
            "Node is missing an ID",
        )
        return

    # Validate based on node type
    try:
        typed_data = node.get_typed_data()
    except Exception as e:
        result.add_error(
            "invalid_node_data",
            f"Node '{node.id}' has invalid data: {e}",
            node_id=node.id,
        )
        return

    if node.type == NodeType.AGENT:
        _validate_agent_node(node, typed_data, result)
    elif node.type == NodeType.BRANCH:
        _validate_branch_node(node, typed_data, result)
    elif node.type == NodeType.INPUT:
        _validate_input_node(node, typed_data, result)
    elif node.type == NodeType.OUTPUT:
        _validate_output_node(node, typed_data, result)
    elif node.type == NodeType.TRANSFORM:
        _validate_transform_node(node, typed_data, result)

    # Validate common config
    if node.config.timeout <= 0:
        result.add_error(
            "invalid_timeout",
            f"Node '{node.id}' has invalid timeout: {node.config.timeout}",
            node_id=node.id,
        )


def _validate_agent_node(
    node: WorkflowNode,
    data: AgentNodeData | dict,
    result: ValidationResult,
) -> None:
    """Validate an agent node."""
    if isinstance(data, dict):
        # Raw dict, check keys
        if not data.get("prompt"):
            result.add_error(
                "missing_prompt",
                f"Agent node '{node.id}' has no prompt",
                node_id=node.id,
            )
        if not data.get("model"):
            result.add_error(
                "missing_model",
                f"Agent node '{node.id}' has no model specified",
                node_id=node.id,
            )
        temp = data.get("temperature", 0.7)
        if not (0.0 <= temp <= 2.0):
            result.add_error(
                "invalid_temperature",
                f"Agent node '{node.id}' has invalid temperature: {temp}",
                node_id=node.id,
            )
    elif isinstance(data, AgentNodeData):
        if not data.prompt:
            result.add_error(
                "missing_prompt",
                f"Agent node '{node.id}' has no prompt",
                node_id=node.id,
            )
        if not data.model:
            result.add_error(
                "missing_model",
                f"Agent node '{node.id}' has no model specified",
                node_id=node.id,
            )
        if not (0.0 <= data.temperature <= 2.0):
            result.add_error(
                "invalid_temperature",
                f"Agent node '{node.id}' has invalid temperature: {data.temperature}",
                node_id=node.id,
            )


def _validate_branch_node(
    node: WorkflowNode,
    data: BranchNodeData | dict,
    result: ValidationResult,
) -> None:
    """Validate a branch node."""
    if isinstance(data, dict):
        conditions = data.get("conditions", [])
    elif isinstance(data, BranchNodeData):
        conditions = data.conditions
    else:
        conditions = []

    if not conditions:
        result.add_warning(
            "empty_conditions",
            f"Branch node '{node.id}' has no conditions defined",
            node_id=node.id,
        )

    # Check for duplicate condition IDs
    condition_ids = [c.id if hasattr(c, "id") else c.get("id") for c in conditions]
    duplicates = [cid for cid in condition_ids if cid and condition_ids.count(cid) > 1]
    if duplicates:
        result.add_error(
            "duplicate_condition_ids",
            f"Branch node '{node.id}' has duplicate condition IDs: {set(duplicates)}",
            node_id=node.id,
        )

    # Validate each condition
    for i, cond in enumerate(conditions):
        cond_id = cond.id if hasattr(cond, "id") else cond.get("id", f"condition_{i}")
        evaluator_type = (
            cond.evaluator_type if hasattr(cond, "evaluator_type")
            else cond.get("evaluator_type")
        )

        if evaluator_type not in ("prompt", "regex", "json_path"):
            result.add_error(
                "invalid_evaluator_type",
                f"Condition '{cond_id}' in node '{node.id}' has invalid evaluator type: {evaluator_type}",
                node_id=node.id,
                condition_id=cond_id,
            )


def _validate_input_node(
    node: WorkflowNode,
    data: InputNodeData | dict,
    result: ValidationResult,
) -> None:
    """Validate an input node."""
    # Input nodes are generally valid with empty config
    # Just warn if no variables are defined
    if isinstance(data, dict):
        variables = data.get("variables", {})
        required = data.get("required", [])
    elif isinstance(data, InputNodeData):
        variables = data.variables
        required = data.required
    else:
        variables = {}
        required = []

    # Check that required variables have defaults or are documented
    for req_var in required:
        if req_var not in variables:
            result.add_warning(
                "required_without_default",
                f"Input node '{node.id}' requires '{req_var}' but has no default value",
                node_id=node.id,
                variable=req_var,
            )


def _validate_output_node(
    node: WorkflowNode,
    data: OutputNodeData | dict,
    result: ValidationResult,
) -> None:
    """Validate an output node."""
    if isinstance(data, dict):
        output_mapping = data.get("output_mapping", {})
    elif isinstance(data, OutputNodeData):
        output_mapping = data.output_mapping
    else:
        output_mapping = {}

    if not output_mapping:
        result.add_warning(
            "empty_output_mapping",
            f"Output node '{node.id}' has no output mapping",
            node_id=node.id,
        )


def _validate_transform_node(
    node: WorkflowNode,
    data: TransformNodeData | dict,
    result: ValidationResult,
) -> None:
    """Validate a transform node."""
    if isinstance(data, dict):
        transform_type = data.get("transform_type")
    elif isinstance(data, TransformNodeData):
        transform_type = data.transform_type
    else:
        transform_type = None

    if transform_type not in ("template", "json_path", "script"):
        result.add_error(
            "invalid_transform_type",
            f"Transform node '{node.id}' has invalid transform type: {transform_type}",
            node_id=node.id,
        )


def _validate_edges(workflow: Workflow, result: ValidationResult) -> None:
    """Validate all edges in the workflow."""
    node_ids = {n.id for n in workflow.nodes}

    for edge in workflow.edges:
        _validate_single_edge(edge, node_ids, result)


def _validate_single_edge(
    edge: WorkflowEdge,
    node_ids: set[str],
    result: ValidationResult,
) -> None:
    """Validate a single edge."""
    # Check required fields
    if not edge.id:
        result.add_error(
            "missing_edge_id",
            "Edge is missing an ID",
        )

    if not edge.source:
        result.add_error(
            "missing_source",
            f"Edge '{edge.id}' has no source node",
            edge_id=edge.id,
        )
    elif edge.source not in node_ids:
        result.add_error(
            "invalid_source",
            f"Edge '{edge.id}' references non-existent source node: {edge.source}",
            edge_id=edge.id,
            source=edge.source,
        )

    if not edge.target:
        result.add_error(
            "missing_target",
            f"Edge '{edge.id}' has no target node",
            edge_id=edge.id,
        )
    elif edge.target not in node_ids:
        result.add_error(
            "invalid_target",
            f"Edge '{edge.id}' references non-existent target node: {edge.target}",
            edge_id=edge.id,
            target=edge.target,
        )

    # Self-loops are usually a mistake
    if edge.source and edge.target and edge.source == edge.target:
        result.add_error(
            "self_loop",
            f"Edge '{edge.id}' creates a self-loop on node '{edge.source}'",
            edge_id=edge.id,
            node_id=edge.source,
        )


def _validate_graph_structure(workflow: Workflow, result: ValidationResult) -> None:
    """Validate the overall graph structure."""
    if not workflow.nodes:
        return

    # Check for entry nodes
    entry_nodes = workflow.get_entry_nodes()
    if not entry_nodes:
        result.add_error(
            "no_entry_nodes",
            "Workflow has no entry nodes (nodes without incoming edges)",
        )

    # Check for exit nodes
    exit_nodes = workflow.get_exit_nodes()
    if not exit_nodes:
        result.add_error(
            "no_exit_nodes",
            "Workflow has no exit nodes (nodes without outgoing edges)",
        )

    # Warn about isolated nodes (no edges at all)
    connected_nodes = set()
    for edge in workflow.edges:
        connected_nodes.add(edge.source)
        connected_nodes.add(edge.target)

    for node in workflow.nodes:
        if node.id not in connected_nodes and len(workflow.nodes) > 1:
            result.add_warning(
                "isolated_node",
                f"Node '{node.id}' is not connected to any other nodes",
                node_id=node.id,
            )


def _validate_node_connections(workflow: Workflow, result: ValidationResult) -> None:
    """Validate node-specific connection requirements."""
    for node in workflow.nodes:
        incoming = workflow.get_incoming_edges(node.id)
        outgoing = workflow.get_outgoing_edges(node.id)

        if node.type == NodeType.INPUT:
            # Input nodes should not have incoming edges
            if incoming:
                result.add_warning(
                    "input_with_incoming",
                    f"Input node '{node.id}' has incoming edges (unusual)",
                    node_id=node.id,
                )

        elif node.type == NodeType.OUTPUT:
            # Output nodes should not have outgoing edges
            if outgoing:
                result.add_warning(
                    "output_with_outgoing",
                    f"Output node '{node.id}' has outgoing edges (unusual)",
                    node_id=node.id,
                )

        elif node.type == NodeType.BRANCH:
            # Branch nodes should have multiple outgoing edges
            if len(outgoing) < 2:
                result.add_warning(
                    "branch_few_outputs",
                    f"Branch node '{node.id}' has fewer than 2 outgoing edges",
                        node_id=node.id,
                    )


def _validate_no_cycles(workflow: Workflow, result: ValidationResult) -> None:
    """Validate that the workflow graph has no cycles (is a DAG).

    Uses Kahn's algorithm for topological sorting to detect cycles.
    """
    if not workflow.nodes or not workflow.edges:
        return

    # Build adjacency list and in-degree count
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}

    for edge in workflow.edges:
        adj[edge.source].append(edge.target)
        in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    # Kahn's algorithm
    queue = deque([n for n, d in in_degree.items() if d == 0])
    sorted_count = 0
    sorted_nodes: list[str] = []

    while queue:
        node_id = queue.popleft()
        sorted_count += 1
        sorted_nodes.append(node_id)

        for neighbor in adj[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # If we didn't process all nodes, there's a cycle
    if sorted_count < len(workflow.nodes):
        # Find the nodes involved in the cycle
        cycle_nodes = [n for n, d in in_degree.items() if d > 0]
        result.add_error(
            "cycle",
            f"Workflow graph contains a cycle involving nodes: {cycle_nodes}",
            nodes=cycle_nodes,
        )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def find_cycles(workflow: Workflow) -> list[list[str]]:
    """Find all cycles in a workflow graph.

    Uses depth-first search to detect and return cycles.

    Returns:
        List of cycles, where each cycle is a list of node IDs
    """
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in workflow.edges:
        adj[edge.source].append(edge.target)

    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node_id: str) -> None:
        visited.add(node_id)
        rec_stack.add(node_id)
        path.append(node_id)

        for neighbor in adj[node_id]:
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node_id)

    for node in workflow.nodes:
        if node.id not in visited:
            dfs(node.id)

    return cycles


def get_topological_order(workflow: Workflow) -> Optional[list[str]]:
    """Get the topological ordering of workflow nodes.

    Returns:
        List of node IDs in topological order, or None if cycles exist
    """
    result = validate_workflow(workflow)

    # Check for cycle errors
    for error in result.errors:
        if error["type"] == "cycle":
            return None

    # Build adjacency list and in-degree count
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}

    for edge in workflow.edges:
        adj[edge.source].append(edge.target)
        in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    # Kahn's algorithm
    queue = deque([n for n, d in in_degree.items() if d == 0])
    sorted_nodes: list[str] = []

    while queue:
        node_id = queue.popleft()
        sorted_nodes.append(node_id)

        for neighbor in adj[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return sorted_nodes if len(sorted_nodes) == len(workflow.nodes) else None


def get_node_dependencies(workflow: Workflow, node_id: str) -> set[str]:
    """Get all nodes that a given node depends on (direct and transitive).

    Args:
        workflow: The workflow to analyze
        node_id: The node to find dependencies for

    Returns:
        Set of node IDs that must complete before this node can execute
    """
    # Build reverse adjacency (target -> sources)
    reverse_adj: dict[str, set[str]] = defaultdict(set)
    for edge in workflow.edges:
        reverse_adj[edge.target].add(edge.source)

    # BFS to find all transitive dependencies
    dependencies: set[str] = set()
    queue = deque(reverse_adj.get(node_id, set()))

    while queue:
        dep_id = queue.popleft()
        if dep_id not in dependencies:
            dependencies.add(dep_id)
            queue.extend(reverse_adj.get(dep_id, set()) - dependencies)

    return dependencies
