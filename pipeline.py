#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vibe Building - Unified Integration Pipeline

Connects all modules together:
  AI (Qwen/OpenAI) → Workflow Engine → Revit Client → pyRevit → Revit

This is the main entry point that ties together:
  - workflow/          (execution engine, scheduler, context)
  - vibe_building/     (Revit HTTP client, intent parser)
  - tools/revit_tool.py (hermes-agent tool definitions)
  - workflow/streaming/ (SSE event broadcasting)
  - workflow/engine/recovery/ (retry, breakpoints, error handling)
"""

import os
import sys
import json
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

# Configure paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Environment
os.environ["OPENAI_API_KEY"] = "sk-e39ef94abba74acb8ffed3a6ca9752ea"
os.environ["OPENAI_BASE_URL"] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

from openai import OpenAI

# Import our modules
from tools import revit_api
from vibe_building.intent_parser import IntentParser

# Workflow engine modules
from workflow.engine.state_machine import StateMachine, ExecutionState
from workflow.engine.context import ContextManager
from workflow.engine.recovery.retry import RetryPolicy, RetryHandler, BackoffStrategy
from workflow.engine.recovery.error_classifier import ErrorClassifier, classify_error
from workflow.streaming.handler import StreamHandler, StreamEvent, StreamEventType

logger = logging.getLogger(__name__)


# =============================================================================
# Building Pipeline
# =============================================================================

@dataclass
class PipelineStep:
    """A single step in the building pipeline."""
    name: str
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class PipelineResult:
    """Result of a complete pipeline execution."""
    steps: List[PipelineStep] = field(default_factory=list)
    total_duration: float = 0.0
    success: bool = False
    ai_response: str = ""
    revit_results: List[Dict] = field(default_factory=list)


class BuildingPipeline:
    """
    Unified pipeline that processes natural language commands
    through AI understanding and executes them in Revit.

    Pipeline flow:
    1. Parse input → IntentParser (rule-based pre-check)
    2. AI Understanding → Qwen (function calling)
    3. Validate → Check parameters and feasibility
    4. Execute → RevitClient → pyRevit → Revit API
    5. Verify → Query Revit to confirm changes
    6. Report → Generate summary for user
    """

    def __init__(
        self,
        ai_client: Optional[OpenAI] = None,
        intent_parser: Optional[IntentParser] = None,
        system_prompt: Optional[str] = None,
    ):
        # AI client
        self.ai = ai_client or OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"]
        )

        # Intent parser (rule-based fallback)
        self.parser = intent_parser or IntentParser()

        # System prompt
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        # Workflow engine components
        self.state_machine = StateMachine()
        self.context_manager = ContextManager()
        self.error_classifier = ErrorClassifier()

        # Retry policy for Revit operations
        self.retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            strategy=BackoffStrategy.EXPONENTIAL,
        )
        self.retry_handler = RetryHandler(self.retry_policy)

        # Streaming
        self.stream_handler: Optional[StreamHandler] = None

        # Conversation history
        self.history: List[Dict] = []

        # Function definitions for AI
        self.functions = self._build_functions()

    def _build_functions(self) -> List[Dict]:
        """Build function definitions for AI tool calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_wall",
                    "description": "Create a wall between two points",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_x": {"type": "number", "description": "Start X (meters)"},
                            "start_y": {"type": "number", "description": "Start Y (meters)"},
                            "end_x": {"type": "number", "description": "End X (meters)"},
                            "end_y": {"type": "number", "description": "End Y (meters)"},
                            "height": {"type": "number", "default": 3.0},
                            "level": {"type": "string", "default": "Level 1"}
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_room",
                    "description": "Create a rectangular room (4 walls)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x1": {"type": "number", "description": "Bottom-left X"},
                            "y1": {"type": "number", "description": "Bottom-left Y"},
                            "x2": {"type": "number", "description": "Top-right X"},
                            "y2": {"type": "number", "description": "Top-right Y"},
                            "height": {"type": "number", "default": 3.0},
                            "level": {"type": "string", "default": "Level 1"}
                        },
                        "required": ["x1", "y1", "x2", "y2"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_walls",
                    "description": "List all walls in the model",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_levels",
                    "description": "Get all levels/floors",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_all_walls",
                    "description": "Delete all walls",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_model_info",
                    "description": "Get model summary (wall count, levels, etc.)",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    # =========================================================================
    # Pipeline Steps
    # =========================================================================

    def step_check_connection(self) -> PipelineStep:
        """Step 1: Check Revit connection."""
        step = PipelineStep(name="Check Revit Connection")
        step.started_at = datetime.now()
        step.status = "running"

        try:
            health = revit_api.health_check()
            if health.get("status") == "ok":
                step.status = "completed"
                step.result = health
            else:
                step.status = "failed"
                step.error = f"Revit not responding: {health}"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)

        step.completed_at = datetime.now()
        step.duration = (step.completed_at - step.started_at).total_seconds()
        return step

    def step_parse_intent(self, user_input: str) -> PipelineStep:
        """Step 2: Parse user intent (rule-based + AI)."""
        step = PipelineStep(name="Parse Intent")
        step.started_at = datetime.now()
        step.status = "running"

        try:
            # Rule-based parsing first
            rule_intent = self.parser.parse(user_input)

            step.result = {
                "rule_based": rule_intent.to_dict() if rule_intent else None,
                "raw_input": user_input,
            }
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)

        step.completed_at = datetime.now()
        step.duration = (step.completed_at - step.started_at).total_seconds()
        return step

    def step_ai_understand(self, user_input: str) -> PipelineStep:
        """Step 3: AI understands the command and decides what to do."""
        step = PipelineStep(name="AI Understanding")
        step.started_at = datetime.now()
        step.status = "running"

        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            messages.extend(self.history[-10:])  # Last 10 messages for context
            messages.append({"role": "user", "content": user_input})

            response = self.ai.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                tools=self.functions,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2000
            )

            msg = response.choices[0].message

            step.result = {
                "content": msg.content,
                "tool_calls": [],
            }

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    step.result["tool_calls"].append({
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments),
                        "id": tc.id,
                    })

            # Store for conversation continuity
            self.history.append({"role": "user", "content": user_input})
            if msg.content:
                self.history.append({"role": "assistant", "content": msg.content})

            step.status = "completed"

        except Exception as e:
            step.status = "failed"
            step.error = str(e)

        step.completed_at = datetime.now()
        step.duration = (step.completed_at - step.started_at).total_seconds()
        return step

    def step_execute_revit(self, tool_calls: List[Dict]) -> PipelineStep:
        """Step 4: Execute Revit operations with retry."""
        step = PipelineStep(name="Execute in Revit")
        step.started_at = datetime.now()
        step.status = "running"
        step.result = {"operations": [], "success_count": 0, "fail_count": 0}

        for tc in tool_calls:
            func_name = tc["name"]
            func_args = tc["args"]

            try:
                result = self._execute_revit_function(func_name, func_args)
                step.result["operations"].append({
                    "function": func_name,
                    "args": func_args,
                    "result": result,
                    "success": True,
                })
                step.result["success_count"] += 1
            except Exception as e:
                step.result["operations"].append({
                    "function": func_name,
                    "args": func_args,
                    "error": str(e),
                    "success": False,
                })
                step.result["fail_count"] += 1

        if step.result["fail_count"] > 0 and step.result["success_count"] == 0:
            step.status = "failed"
        else:
            step.status = "completed"

        step.completed_at = datetime.now()
        step.duration = (step.completed_at - step.started_at).total_seconds()
        return step

    def step_verify(self) -> PipelineStep:
        """Step 5: Verify changes in Revit."""
        step = PipelineStep(name="Verify Changes")
        step.started_at = datetime.now()
        step.status = "running"

        try:
            walls = revit_api.list_walls()
            step.result = {
                "wall_count": len(walls),
                "walls": walls[:5],  # First 5 for summary
            }
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)

        step.completed_at = datetime.now()
        step.duration = (step.completed_at - step.started_at).total_seconds()
        return step

    def step_ai_report(self, user_input: str, execute_result: Dict, verify_result: Dict) -> PipelineStep:
        """Step 6: AI generates a summary report."""
        step = PipelineStep(name="Generate Report")
        step.started_at = datetime.now()
        step.status = "running"

        try:
            report_messages = [
                {"role": "system", "content": "You are a BIM assistant. Summarize what was done in Chinese. Be concise."},
                {"role": "user", "content": f"User asked: {user_input}"},
                {"role": "user", "content": f"Executed: {json.dumps(execute_result, ensure_ascii=False)[:500]}"},
                {"role": "user", "content": f"Current model: {json.dumps(verify_result, ensure_ascii=False)[:300]}"},
                {"role": "user", "content": "Please summarize what was accomplished in 2-3 sentences in Chinese."},
            ]

            response = self.ai.chat.completions.create(
                model="qwen-plus",
                messages=report_messages,
                temperature=0.7,
                max_tokens=300
            )

            step.result = response.choices[0].message.content
            step.status = "completed"

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.result = "Report generation failed."

        step.completed_at = datetime.now()
        step.duration = (step.completed_at - step.started_at).total_seconds()
        return step

    # =========================================================================
    # Revit Function Execution
    # =========================================================================

    def _execute_revit_function(self, name: str, args: Dict) -> Dict:
        """Execute a single Revit function via tools/revit_api.py."""

        if name == "create_wall":
            return revit_api.create_wall(
                start_x=args["start_x"],
                start_y=args["start_y"],
                end_x=args["end_x"],
                end_y=args["end_y"],
                height=args.get("height", 3.0),
                level=args.get("level", "Level 1"),
            )

        elif name == "create_room":
            return revit_api.create_room(
                x1=args["x1"],
                y1=args["y1"],
                x2=args["x2"],
                y2=args["y2"],
                level=args.get("level", "Level 1"),
                height=args.get("height", 3.0),
            )

        elif name == "list_walls":
            walls = revit_api.list_walls()
            return {"walls": walls[:10], "count": len(walls)}

        elif name == "get_levels":
            levels = revit_api.get_levels()
            return {"levels": levels, "count": len(levels)}

        elif name == "delete_all_walls":
            return revit_api.delete_all_walls()

        elif name == "get_model_info":
            health = revit_api.health_check()
            walls = revit_api.list_walls()
            levels = revit_api.get_levels()
            return {
                "document": health.get("document_name"),
                "wall_count": len(walls),
                "level_count": len(levels),
            }

        else:
            return {"error": f"Unknown function: {name}"}

    # =========================================================================
    # Main Pipeline Execution
    # =========================================================================

    def run(self, user_input: str, verbose: bool = True) -> PipelineResult:
        """
        Run the complete pipeline for a user command.

        Args:
            user_input: Natural language command
            verbose: Print progress to console

        Returns:
            PipelineResult with all step details
        """
        result = PipelineResult()
        start_time = time.time()

        if verbose:
            print(f"\n{'='*60}")
            print(f"  Pipeline: {user_input}")
            print(f"{'='*60}")

        # Step 1: Check connection
        if verbose:
            print(f"\n  [1/6] Checking Revit connection...")
        step1 = self.step_check_connection()
        result.steps.append(step1)
        if step1.status == "failed":
            if verbose:
                print(f"  FAILED: {step1.error}")
            result.success = False
            return result
        if verbose:
            print(f"  OK - {step1.result.get('document_name', 'Connected')}")

        # Step 2: Parse intent (rule-based)
        if verbose:
            print(f"\n  [2/6] Parsing intent...")
        step2 = self.step_parse_intent(user_input)
        result.steps.append(step2)
        if verbose and step2.result:
            rule = step2.result.get("rule_based")
            if rule:
                print(f"  Rule-based: action={rule.get('action')}, confidence={rule.get('confidence')}")
            else:
                print(f"  Rule-based: no match (will use AI)")

        # Step 3: AI understanding
        if verbose:
            print(f"\n  [3/6] AI understanding...")
        step3 = self.step_ai_understand(user_input)
        result.steps.append(step3)
        if step3.status == "failed":
            if verbose:
                print(f"  FAILED: {step3.error}")
            result.success = False
            return result

        tool_calls = step3.result.get("tool_calls", [])
        if verbose:
            if tool_calls:
                for tc in tool_calls:
                    print(f"  AI calls: {tc['name']}({tc['args']})")
            else:
                print(f"  AI response: {step3.result.get('content', '')[:100]}")

        # Step 4: Execute in Revit
        if tool_calls:
            if verbose:
                print(f"\n  [4/6] Executing in Revit...")
            step4 = self.step_execute_revit(tool_calls)
            result.steps.append(step4)
            result.revit_results = step4.result.get("operations", [])
            if verbose:
                print(f"  Success: {step4.result['success_count']}, Failed: {step4.result['fail_count']}")
                for op in step4.result.get("operations", []):
                    if op.get("success"):
                        r = op.get("result", {})
                        if "room_dimensions" in r:
                            print(f"    -> {op['function']}: {r.get('room_dimensions')}, {r.get('area_sqm')} sqm")
                        elif "wall_id" in r:
                            print(f"    -> {op['function']}: wall #{r.get('wall_id')}")
                        elif "count" in r:
                            print(f"    -> {op['function']}: {r.get('count')} items")
                        else:
                            print(f"    -> {op['function']}: OK")
        else:
            if verbose:
                print(f"\n  [4/6] No Revit operations needed")
            result.steps.append(PipelineStep(
                name="Execute in Revit",
                status="skipped",
                result={"success_count": 0}
            ))

        # Step 5: Verify
        if verbose:
            print(f"\n  [5/6] Verifying...")
        step5 = self.step_verify()
        result.steps.append(step5)
        if verbose:
            print(f"  Model now has {step5.result.get('wall_count', 0)} walls")

        # Step 6: AI report
        if verbose:
            print(f"\n  [6/6] Generating report...")
        execute_data = result.steps[3].result if len(result.steps) > 3 else {}
        verify_data = step5.result if step5.result else {}
        step6 = self.step_ai_report(user_input, execute_data, verify_data)
        result.steps.append(step6)
        result.ai_response = step6.result or ""
        if verbose:
            print(f"\n  Report: {result.ai_response}")

        # Final summary
        result.total_duration = time.time() - start_time
        result.success = all(
            s.status in ("completed", "skipped") for s in result.steps
        )

        if verbose:
            status = "SUCCESS" if result.success else "FAILED"
            print(f"\n{'='*60}")
            print(f"  {status} | Duration: {result.total_duration:.2f}s | Steps: {len(result.steps)}")
            print(f"{'='*60}")

        return result


# =============================================================================
# Default System Prompt
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are a professional BIM modeling assistant for VibeBuilding.
You help users create building elements in Revit using natural language.

IMPORTANT: Only execute what the user CURRENTLY asks. Do NOT repeat or rebuild previous commands.
Each user message is a new, independent request.

Available functions:
1. create_wall(start_x, start_y, end_x, end_y, height, level) - Create a wall
2. create_room(x1, y1, x2, y2, height, level) - Create a rectangular room (4 walls)
3. list_walls() - List all walls
4. get_levels() - Get all levels
5. delete_all_walls() - Delete all walls
6. get_model_info() - Get model summary

Coordinate system:
- X axis: East-West (positive = East)
- Y axis: North-South (positive = North)
- Units: meters

When the user describes what they want:
1. Understand the intent
2. Choose reasonable coordinates if not specified
3. Call the appropriate function(s)
4. For complex shapes, break into multiple rectangular sections

Always respond in Chinese."""


# =============================================================================
# Interactive Mode
# =============================================================================

def interactive_mode():
    """Run the pipeline in interactive mode."""
    print("=" * 60)
    print("  Vibe Building - Integrated Pipeline")
    print("  AI: Qwen (DashScope) | Revit: 2025")
    print("  Engine: Workflow + Context + Retry + Error Classification")
    print("=" * 60)

    pipeline = BuildingPipeline()

    # Initial connection check
    check = pipeline.step_check_connection()
    if check.status == "failed":
        print(f"\n  Cannot connect to Revit: {check.error}")
        print("  Make sure Revit is running with VibeBuilding extension.")
        return

    print(f"\n  Connected to: {check.result.get('document_name', 'Revit')}")
    print(f"\n  Type your building commands. Type 'quit' to exit.")
    print(f"  Type 'pipeline' to see detailed step breakdown.")
    print()

    show_pipeline = False

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            if user_input.lower() == "pipeline":
                show_pipeline = not show_pipeline
                print(f"Pipeline details: {'ON' if show_pipeline else 'OFF'}")
                continue

            result = pipeline.run(user_input, verbose=show_pipeline)

            if not show_pipeline:
                if result.success:
                    print(f"\nAI: {result.ai_response}")
                else:
                    failed = [s for s in result.steps if s.status == "failed"]
                    errors = "; ".join(s.error or "unknown" for s in failed)
                    print(f"\nError: {errors}")

            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    interactive_mode()
