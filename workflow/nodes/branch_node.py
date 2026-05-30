"""
Branch node executor for workflow system.

Evaluates conditions and routes execution to different output ports:
- Prompt-based evaluators: Use LLM to evaluate conditions
- Regex evaluators: Match patterns against values
- JSON path evaluators: Extract and compare JSON values
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from workflow.context.accumulator import ContextAccumulator
from workflow.models import (
    BranchCondition,
    BranchNodeData,
    NodeExecutionStatus,
    NodeType,
    WorkflowNode,
)
from workflow.nodes.base import (
    BaseNodeExecutor,
    ExecutionContext,
    NodeExecutionResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------


@dataclass
class EvaluationResult:
    """Result of evaluating a single condition.

    Attributes:
        matched: Whether the condition matched
        output_port: The output port to route to (if matched)
        condition_id: ID of the evaluated condition
        details: Additional evaluation details
        duration: Time taken to evaluate
    """

    matched: bool
    output_port: str
    condition_id: str
    details: Dict[str, Any] = None
    duration: float = 0.0

    def __post_init__(self):
        if self.details is None:
            self.details = {}


# ---------------------------------------------------------------------------
# Base evaluator
# ---------------------------------------------------------------------------


class ConditionEvaluator(ABC):
    """Base class for condition evaluators."""

    @abstractmethod
    async def evaluate(
        self,
        condition: BranchCondition,
        context: ContextAccumulator,
    ) -> EvaluationResult:
        """Evaluate a condition against the context.

        Args:
            condition: The condition to evaluate
            context: The workflow context

        Returns:
            EvaluationResult indicating whether the condition matched
        """
        pass


# ---------------------------------------------------------------------------
# Prompt evaluator
# ---------------------------------------------------------------------------


class PromptConditionEvaluator(ConditionEvaluator):
    """Evaluates conditions using an LLM prompt.

    Config format:
        {
            "prompt": "Does the following text indicate success? {{input}}",
            "input_path": "agent_1.output",
            "true_patterns": ["yes", "true", "success"],
            "model": "gpt-3.5-turbo",  # Optional, fast model for evaluation
        }
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        self.llm_provider = llm_provider

    async def evaluate(
        self,
        condition: BranchCondition,
        context: ContextAccumulator,
    ) -> EvaluationResult:
        start_time = time.time()
        config = condition.evaluator_config

        # Get input value
        input_path = config.get("input_path", "")
        input_value = context.resolve_path(input_path) if input_path else ""

        # Build prompt
        prompt_template = config.get("prompt", "Is this true? {{input}}")
        prompt = prompt_template.replace("{{input}}", str(input_value))

        # Get true patterns
        true_patterns = config.get("true_patterns", ["yes", "true", "1"])

        try:
            if self.llm_provider:
                # Use LLM to evaluate
                model = config.get("model", "gpt-3.5-turbo")
                response = await self.llm_provider.generate(
                    prompt=prompt,
                    model=model,
                    max_tokens=10,
                    temperature=0.0,
                )
                result_text = response.content.strip().lower()
            else:
                # Mock evaluation for testing
                result_text = str(input_value).lower()

            # Check if result matches any true pattern
            matched = any(
                pattern.lower() in result_text
                for pattern in true_patterns
            )

            duration = time.time() - start_time

            return EvaluationResult(
                matched=matched,
                output_port=condition.output_port,
                condition_id=condition.id,
                details={
                    "prompt": prompt,
                    "response": result_text if self.llm_provider else "(mock)",
                    "patterns_checked": true_patterns,
                },
                duration=duration,
            )

        except Exception as e:
            logger.exception("Prompt evaluation failed: %s", e)
            return EvaluationResult(
                matched=False,
                output_port=condition.output_port,
                condition_id=condition.id,
                details={"error": str(e)},
                duration=time.time() - start_time,
            )


# ---------------------------------------------------------------------------
# Regex evaluator
# ---------------------------------------------------------------------------


class RegexConditionEvaluator(ConditionEvaluator):
    """Evaluates conditions using regular expressions.

    Config format:
        {
            "pattern": "success|completed|done",
            "input_path": "agent_1.output",
            "flags": "i",  # Optional: i=ignorecase, m=multiline, s=dotall
            "full_match": false,  # If true, require full string match
        }
    """

    async def evaluate(
        self,
        condition: BranchCondition,
        context: ContextAccumulator,
    ) -> EvaluationResult:
        start_time = time.time()
        config = condition.evaluator_config

        # Get input value
        input_path = config.get("input_path", "")
        input_value = context.resolve_path(input_path) if input_path else ""

        if input_value is None:
            input_value = ""
        elif not isinstance(input_value, str):
            input_value = json.dumps(input_value)

        # Get pattern
        pattern = config.get("pattern", "")
        if not pattern:
            return EvaluationResult(
                matched=False,
                output_port=condition.output_port,
                condition_id=condition.id,
                details={"error": "No pattern specified"},
                duration=time.time() - start_time,
            )

        # Build flags
        flags_str = config.get("flags", "")
        flags = 0
        if "i" in flags_str:
            flags |= re.IGNORECASE
        if "m" in flags_str:
            flags |= re.MULTILINE
        if "s" in flags_str:
            flags |= re.DOTALL

        full_match = config.get("full_match", False)

        try:
            compiled = re.compile(pattern, flags)

            if full_match:
                match = compiled.fullmatch(input_value)
            else:
                match = compiled.search(input_value)

            matched = match is not None

            return EvaluationResult(
                matched=matched,
                output_port=condition.output_port,
                condition_id=condition.id,
                details={
                    "pattern": pattern,
                    "input_preview": input_value[:100] if len(input_value) > 100 else input_value,
                    "match": match.group(0) if match else None,
                    "full_match": full_match,
                },
                duration=time.time() - start_time,
            )

        except re.error as e:
            logger.warning("Invalid regex pattern '%s': %s", pattern, e)
            return EvaluationResult(
                matched=False,
                output_port=condition.output_port,
                condition_id=condition.id,
                details={"error": f"Invalid regex: {e}"},
                duration=time.time() - start_time,
            )


# ---------------------------------------------------------------------------
# JSON path evaluator
# ---------------------------------------------------------------------------


class JsonPathConditionEvaluator(ConditionEvaluator):
    """Evaluates conditions by extracting and comparing JSON values.

    Config format:
        {
            "path": "agent_1.output.status",
            "operator": "eq",  # eq, ne, gt, lt, gte, lte, contains, exists
            "value": "success",
            "input_path": "",  # Optional: base object to query (defaults to context)
        }
    """

    async def evaluate(
        self,
        condition: BranchCondition,
        context: ContextAccumulator,
    ) -> EvaluationResult:
        start_time = time.time()
        config = condition.evaluator_config

        # Get base object
        input_path = config.get("input_path", "")
        if input_path:
            base = context.resolve_path(input_path)
        else:
            base = None  # Will use context directly

        # Get path to evaluate
        path = config.get("path", "")
        if not path:
            return EvaluationResult(
                matched=False,
                output_port=condition.output_port,
                condition_id=condition.id,
                details={"error": "No path specified"},
                duration=time.time() - start_time,
            )

        # Resolve the value
        if base is not None:
            actual_value = self._get_nested(base, path)
        else:
            actual_value = context.resolve_path(path)

        # Get comparison config
        operator = config.get("operator", "exists")
        expected_value = config.get("value")

        # Evaluate
        matched, details = self._compare(actual_value, operator, expected_value)

        return EvaluationResult(
            matched=matched,
            output_port=condition.output_port,
            condition_id=condition.id,
            details={
                "path": path,
                "actual_value": self._truncate(actual_value),
                "operator": operator,
                "expected_value": self._truncate(expected_value),
                **details,
            },
            duration=time.time() - start_time,
        )

    def _get_nested(self, obj: Any, path: str) -> Any:
        """Get a nested value using dot notation."""
        parts = path.split(".")
        current = obj

        for part in parts:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    def _compare(
        self,
        actual: Any,
        operator: str,
        expected: Any,
    ) -> tuple:
        """Compare values based on operator.

        Returns:
            Tuple of (matched, details_dict)
        """
        if operator == "exists":
            return actual is not None, {}

        if operator == "eq":
            return actual == expected, {}

        if operator == "ne":
            return actual != expected, {}

        if actual is None:
            return False, {"reason": "actual value is None"}

        if operator == "gt":
            try:
                return float(actual) > float(expected), {}
            except (TypeError, ValueError):
                return False, {"reason": "cannot compare non-numeric values"}

        if operator == "lt":
            try:
                return float(actual) < float(expected), {}
            except (TypeError, ValueError):
                return False, {"reason": "cannot compare non-numeric values"}

        if operator == "gte":
            try:
                return float(actual) >= float(expected), {}
            except (TypeError, ValueError):
                return False, {"reason": "cannot compare non-numeric values"}

        if operator == "lte":
            try:
                return float(actual) <= float(expected), {}
            except (TypeError, ValueError):
                return False, {"reason": "cannot compare non-numeric values"}

        if operator == "contains":
            if isinstance(actual, str):
                return expected in actual, {}
            if isinstance(actual, (list, dict)):
                return expected in actual, {}
            return False, {"reason": "value does not support contains"}

        return False, {"reason": f"unknown operator: {operator}"}

    def _truncate(self, value: Any, max_length: int = 100) -> Any:
        """Truncate a value for logging."""
        if value is None:
            return None
        if isinstance(value, str) and len(value) > max_length:
            return value[:max_length] + "..."
        return value


# ---------------------------------------------------------------------------
# Evaluator registry
# ---------------------------------------------------------------------------


EVALUATORS: Dict[str, type] = {
    "prompt": PromptConditionEvaluator,
    "regex": RegexConditionEvaluator,
    "json_path": JsonPathConditionEvaluator,
}


def get_evaluator(evaluator_type: str, **kwargs) -> ConditionEvaluator:
    """Get an evaluator by type.

    Args:
        evaluator_type: The type of evaluator
        **kwargs: Additional arguments for the evaluator (only used by some)

    Returns:
        ConditionEvaluator instance
    """
    evaluator_class = EVALUATORS.get(evaluator_type)
    if evaluator_class is None:
        raise ValueError(f"Unknown evaluator type: {evaluator_type}")

    # Only pass kwargs to evaluators that accept them
    if evaluator_type == "prompt":
        return evaluator_class(llm_provider=kwargs.get("llm_provider"))
    else:
        return evaluator_class()


# ---------------------------------------------------------------------------
# Branch node executor
# ---------------------------------------------------------------------------


class BranchNodeExecutor(BaseNodeExecutor):
    """Executor for branch nodes.

    Evaluates conditions in order and routes execution to the first
    matching condition's output port, or the default port if none match.
    """

    node_type = "branch"

    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        **kwargs: Any,
    ):
        """Initialize the branch executor.

        Args:
            llm_provider: Optional LLM provider for prompt-based evaluation
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.llm_provider = llm_provider

    async def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        """Execute a branch node.

        Evaluates conditions and determines which output port to use.
        """
        start_time = time.time()
        node = context.node

        try:
            # Get typed data
            typed_data = node.get_typed_data()
            if not isinstance(typed_data, BranchNodeData):
                return NodeExecutionResult.error(
                    node_id=node.id,
                    error="Node data is not BranchNodeData",
                )

            conditions = typed_data.conditions
            default_output = typed_data.default_output or "default"

            # Create context accumulator from workflow context
            acc = ContextAccumulator(initial_context=context.workflow_context)

            # Evaluate conditions in order
            evaluation_results: List[EvaluationResult] = []
            selected_port: Optional[str] = None

            for condition in conditions:
                evaluator = get_evaluator(
                    condition.evaluator_type,
                    llm_provider=self.llm_provider if condition.evaluator_type == "prompt" else None,
                )

                result = await evaluator.evaluate(condition, acc)
                evaluation_results.append(result)

                if result.matched and selected_port is None:
                    selected_port = result.output_port
                    context.emit_event("condition_matched", {
                        "condition_id": condition.id,
                        "output_port": result.output_port,
                    })

                context.emit_event("condition_evaluated", {
                    "condition_id": condition.id,
                    "matched": result.matched,
                    "duration": result.duration,
                })

            # Use default if no condition matched
            if selected_port is None:
                selected_port = default_output
                context.emit_event("using_default", {
                    "output_port": default_output,
                })

            duration = time.time() - start_time

            context.emit_event("branch_evaluated", {
                "selected_port": selected_port,
                "conditions_evaluated": len(evaluation_results),
            })

            return NodeExecutionResult.success(
                node_id=node.id,
                output={
                    "selected_port": selected_port,
                    "evaluations": [
                        {
                            "condition_id": r.condition_id,
                            "matched": r.matched,
                            "output_port": r.output_port,
                            "details": r.details,
                        }
                        for r in evaluation_results
                    ],
                },
                duration=duration,
                selected_port=selected_port,
                conditions_evaluated=len(evaluation_results),
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.exception("Branch node %s execution failed", node.id)
            return NodeExecutionResult.error(
                node_id=node.id,
                error=str(e),
                duration=duration,
            )

    def validate_node(self, node: WorkflowNode) -> List[str]:
        """Validate a branch node configuration."""
        errors = super().validate_node(node)

        typed_data = node.get_typed_data()
        if not isinstance(typed_data, BranchNodeData):
            errors.append("Node data must be BranchNodeData")
            return errors

        if not typed_data.conditions:
            errors.append("Branch node must have at least one condition")

        for i, condition in enumerate(typed_data.conditions):
            if condition.evaluator_type not in EVALUATORS:
                errors.append(
                    f"Condition {i}: unknown evaluator type '{condition.evaluator_type}'"
                )

        return errors


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_branch_executor(registry, llm_provider: Optional[Any] = None) -> None:
    """Register the branch executor with a registry.

    Args:
        registry: NodeExecutorRegistry to register with
        llm_provider: Optional LLM provider for prompt evaluation
    """
    registry.register("branch", BranchNodeExecutor(llm_provider=llm_provider))
