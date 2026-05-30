"""
Node scheduler for workflow execution.

Determines which nodes are ready to execute based on:
- Dependency resolution (incoming edges)
- Node completion status
- Parallel execution configuration
- Branch conditions
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from workflow.models import (
    NodeType,
    Workflow,
    WorkflowContext,
    WorkflowEdge,
    WorkflowNode,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scheduling result
# ---------------------------------------------------------------------------


@dataclass
class SchedulingResult:
    """Result of scheduling computation.

    Attributes:
        ready_nodes: Nodes that can be executed now
        waiting_nodes: Nodes waiting for dependencies
        blocked_nodes: Nodes blocked by conditions
        completed_nodes: Nodes that have finished
        is_complete: Whether the workflow is complete
    """

    ready_nodes: List[WorkflowNode] = field(default_factory=list)
    waiting_nodes: List[WorkflowNode] = field(default_factory=list)
    blocked_nodes: List[WorkflowNode] = field(default_factory=list)
    completed_nodes: List[str] = field(default_factory=list)
    is_complete: bool = False

    @property
    def has_ready_nodes(self) -> bool:
        return len(self.ready_nodes) > 0

    def get_parallel_groups(self) -> List[List[WorkflowNode]]:
        """Split ready nodes into parallel and sequential groups.

        Returns:
            List of groups, where:
            - First group contains all parallel-enabled nodes
            - Remaining groups contain one sequential node each
        """
        parallel = [n for n in self.ready_nodes if n.config.parallel]
        sequential = [n for n in self.ready_nodes if not n.config.parallel]

        groups = []
        if parallel:
            groups.append(parallel)
        for node in sequential:
            groups.append([node])

        return groups


# ---------------------------------------------------------------------------
# Node scheduler
# ---------------------------------------------------------------------------


class NodeScheduler:
    """Scheduler for workflow node execution.

    Computes which nodes are ready to execute based on the current
    workflow state and context.

    Example:
        >>> scheduler = NodeScheduler(workflow)
        >>> result = scheduler.compute_ready_nodes(context, running_nodes)
        >>> for node in result.ready_nodes:
        ...     await execute_node(node)
    """

    def __init__(self, workflow: Workflow):
        """Initialize the scheduler.

        Args:
            workflow: The workflow to schedule
        """
        self.workflow = workflow

        # Pre-compute dependency graph
        self._incoming_edges: Dict[str, List[WorkflowEdge]] = defaultdict(list)
        self._outgoing_edges: Dict[str, List[WorkflowEdge]] = defaultdict(list)
        self._node_map: Dict[str, WorkflowNode] = {}

        for node in workflow.nodes:
            self._node_map[node.id] = node

        for edge in workflow.edges:
            self._incoming_edges[edge.target].append(edge)
            self._outgoing_edges[edge.source].append(edge)

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID."""
        return self._node_map.get(node_id)

    def get_dependencies(self, node_id: str) -> Set[str]:
        """Get direct dependencies for a node.

        Args:
            node_id: The node ID

        Returns:
            Set of node IDs that must complete before this node
        """
        edges = self._incoming_edges.get(node_id, [])
        return {e.source for e in edges}

    def get_dependents(self, node_id: str) -> Set[str]:
        """Get nodes that depend on this node.

        Args:
            node_id: The node ID

        Returns:
            Set of node IDs that depend on this node
        """
        edges = self._outgoing_edges.get(node_id, [])
        return {e.target for e in edges}

    def get_entry_nodes(self) -> List[WorkflowNode]:
        """Get nodes with no incoming edges (entry points)."""
        return [
            node for node in self.workflow.nodes
            if not self._incoming_edges.get(node.id)
        ]

    def get_exit_nodes(self) -> List[WorkflowNode]:
        """Get nodes with no outgoing edges (exit points)."""
        return [
            node for node in self.workflow.nodes
            if not self._outgoing_edges.get(node.id)
        ]

    def compute_ready_nodes(
        self,
        context: WorkflowContext,
        running_nodes: Set[str],
        skipped_nodes: Optional[Set[str]] = None,
    ) -> SchedulingResult:
        """Compute which nodes are ready to execute.

        A node is ready when:
        1. It has not been executed yet
        2. It is not currently running
        3. All its dependencies are satisfied (completed or skipped)
        4. Edge conditions (if any) are satisfied

        Args:
            context: Current workflow context
            running_nodes: Set of currently executing node IDs
            skipped_nodes: Set of nodes that were skipped

        Returns:
            SchedulingResult with ready, waiting, and blocked nodes
        """
        skipped_nodes = skipped_nodes or set()
        completed_nodes = set(context.execution_history)
        all_node_ids = {n.id for n in self.workflow.nodes}

        ready = []
        waiting = []
        blocked = []

        for node in self.workflow.nodes:
            # Skip already processed nodes
            if node.id in completed_nodes:
                continue
            if node.id in skipped_nodes:
                continue
            if node.id in running_nodes:
                continue

            # Check dependencies
            deps = self.get_dependencies(node.id)
            unsatisfied_deps = deps - completed_nodes - skipped_nodes

            if unsatisfied_deps:
                waiting.append(node)
                continue

            # Check edge conditions
            can_execute, reason = self._check_edge_conditions(
                node, context, completed_nodes, skipped_nodes
            )

            if can_execute:
                ready.append(node)
            else:
                blocked.append(node)
                logger.debug(
                    "Node %s blocked: %s",
                    node.id,
                    reason,
                )

        # Check if workflow is complete
        is_complete = (
            len(completed_nodes) + len(skipped_nodes) == len(all_node_ids)
            or (not ready and not waiting and not running_nodes)
        )

        return SchedulingResult(
            ready_nodes=ready,
            waiting_nodes=waiting,
            blocked_nodes=blocked,
            completed_nodes=list(completed_nodes),
            is_complete=is_complete,
        )

    def _check_edge_conditions(
        self,
        node: WorkflowNode,
        context: WorkflowContext,
        completed_nodes: Set[str],
        skipped_nodes: Set[str],
    ) -> Tuple[bool, str]:
        """Check if edge conditions allow node execution.

        Args:
            node: The node to check
            context: Current workflow context
            completed_nodes: Set of completed node IDs
            skipped_nodes: Set of skipped node IDs

        Returns:
            Tuple of (can_execute, reason)
        """
        incoming_edges = self._incoming_edges.get(node.id, [])

        # Entry nodes have no conditions
        if not incoming_edges:
            return True, ""

        # Check each incoming edge
        for edge in incoming_edges:
            # Source must be completed (not skipped)
            if edge.source in skipped_nodes:
                return False, f"Source node {edge.source} was skipped"

            if edge.source not in completed_nodes:
                return False, f"Source node {edge.source} not completed"

            # Check edge condition if present
            if edge.condition:
                if not self._evaluate_condition(edge.condition, context):
                    return False, f"Edge condition not met: {edge.id}"

        return True, ""

    def _evaluate_condition(
        self,
        condition: Any,  # EdgeCondition
        context: WorkflowContext,
    ) -> bool:
        """Evaluate an edge condition.

        Args:
            condition: The edge condition
            context: Current workflow context

        Returns:
            True if condition is satisfied
        """
        variable = condition.variable
        operator = condition.operator
        expected_value = condition.value

        # Get the actual value
        actual_value = self._resolve_variable(variable, context)

        # Evaluate based on operator
        if operator == "exists":
            return actual_value is not None

        if operator == "eq":
            return actual_value == expected_value

        if operator == "ne":
            return actual_value != expected_value

        if operator == "gt":
            return actual_value is not None and actual_value > expected_value

        if operator == "lt":
            return actual_value is not None and actual_value < expected_value

        if operator == "gte":
            return actual_value is not None and actual_value >= expected_value

        if operator == "lte":
            return actual_value is not None and actual_value <= expected_value

        if operator == "contains":
            if actual_value is None:
                return False
            if isinstance(actual_value, str):
                return expected_value in actual_value
            if isinstance(actual_value, (list, dict)):
                return expected_value in actual_value
            return False

        logger.warning("Unknown condition operator: %s", operator)
        return False

    def _resolve_variable(
        self,
        variable: str,
        context: WorkflowContext,
    ) -> Any:
        """Resolve a variable path to its value.

        Args:
            variable: Variable path (e.g., "name", "node_1.output")
            context: Current workflow context

        Returns:
            The resolved value or None
        """
        # Check context variables
        if variable in context.variables:
            return context.variables[variable]

        # Check input variables
        if variable.startswith("input."):
            var_name = variable[6:]
            return context.input_variables.get(var_name)

        # Check node outputs
        if "." in variable:
            parts = variable.split(".", 1)
            node_id = parts[0]
            field_path = parts[1]

            node_output = context.node_outputs.get(node_id)
            if node_output:
                if field_path == "output":
                    return node_output.output
                if field_path == "status":
                    return node_output.status.value

        return None

    def get_execution_order(self) -> Optional[List[str]]:
        """Get a valid execution order for all nodes.

        Returns:
            List of node IDs in topological order, or None if cycles exist
        """
        from workflow.validation import get_topological_order
        return get_topological_order(self.workflow)

    def get_parallel_level(self, node_id: str) -> int:
        """Get the parallel execution level for a node.

        Nodes at the same level can potentially execute in parallel.

        Args:
            node_id: The node ID

        Returns:
            The parallel level (0 = entry nodes)
        """
        deps = self.get_dependencies(node_id)
        if not deps:
            return 0

        max_dep_level = max(
            self.get_parallel_level(dep) for dep in deps
        )
        return max_dep_level + 1

    def estimate_critical_path(self) -> Tuple[List[str], int]:
        """Estimate the critical path through the workflow.

        The critical path is the longest path from entry to exit.

        Returns:
            Tuple of (node_ids in path, path length)
        """
        # Simple implementation using BFS
        entry_nodes = self.get_entry_nodes()
        if not entry_nodes:
            return [], 0

        # Calculate longest path to each node
        longest_path: Dict[str, Tuple[int, List[str]]] = {}

        def compute_longest(node_id: str) -> Tuple[int, List[str]]:
            if node_id in longest_path:
                return longest_path[node_id]

            deps = self.get_dependencies(node_id)
            if not deps:
                result = (1, [node_id])
            else:
                best_length = 0
                best_path: List[str] = []
                for dep in deps:
                    dep_length, dep_path = compute_longest(dep)
                    if dep_length > best_length:
                        best_length = dep_length
                        best_path = dep_path
                result = (best_length + 1, best_path + [node_id])

            longest_path[node_id] = result
            return result

        # Compute for all exit nodes
        exit_nodes = self.get_exit_nodes()
        max_length = 0
        max_path: List[str] = []

        for node in exit_nodes:
            length, path = compute_longest(node.id)
            if length > max_length:
                max_length = length
                max_path = path

        return max_path, max_length


# ---------------------------------------------------------------------------
# Dependency graph utilities
# ---------------------------------------------------------------------------


def build_dependency_graph(workflow: Workflow) -> Dict[str, Set[str]]:
    """Build a dependency graph for a workflow.

    Args:
        workflow: The workflow

    Returns:
        Dict mapping node ID to set of dependency node IDs
    """
    graph: Dict[str, Set[str]] = {n.id: set() for n in workflow.nodes}

    for edge in workflow.edges:
        graph[edge.target].add(edge.source)

    return graph


def find_parallel_groups(workflow: Workflow) -> List[Set[str]]:
    """Find groups of nodes that can execute in parallel.

    Args:
        workflow: The workflow

    Returns:
        List of node ID sets, where each set can execute in parallel
    """
    scheduler = NodeScheduler(workflow)
    graph = build_dependency_graph(workflow)

    # Group by parallel level
    levels: Dict[int, Set[str]] = defaultdict(set)
    for node in workflow.nodes:
        level = scheduler.get_parallel_level(node.id)
        levels[level].add(node.id)

    return [nodes for level, nodes in sorted(levels.items())]
