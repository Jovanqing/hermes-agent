#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test the integrated pipeline with a demo command."""

import os
import sys

os.environ["OPENAI_API_KEY"] = "sk-e39ef94abba74acb8ffed3a6ca9752ea"
os.environ["OPENAI_BASE_URL"] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from pipeline import BuildingPipeline

print("=" * 60)
print("  Vibe Building - Integrated Pipeline Test")
print("=" * 60)
print()
print("Modules integrated:")
print("  - AI: Qwen (DashScope) - natural language understanding")
print("  - Workflow Engine: StateMachine + ContextManager")
print("  - Recovery: RetryPolicy + ErrorClassifier")
print("  - Streaming: StreamHandler + StreamEvent")
print("  - Intent Parser: rule-based fallback")
print("  - Revit API: tools/revit_api.py -> pyRevit -> Revit 2025")
print()

pipeline = BuildingPipeline()

# Demo 1: Delete all and create a room
print("=" * 60)
print("  Test 1: Delete all walls and create a bedroom")
print("=" * 60)
result1 = pipeline.run("Delete all walls first, then create a 6x5 meter bedroom at position (0,0)", verbose=True)

print()
print()

# Demo 2: Add another room (new pipeline to avoid history replay)
pipeline2 = BuildingPipeline()
print("=" * 60)
print("  Test 2: Add a kitchen next to the bedroom")
print("=" * 60)
result2 = pipeline2.run("Create a 4x3 meter kitchen next to the bedroom, starting at position (6,0)", verbose=True)

print()
print()

# Demo 3: Query (new pipeline to avoid history replay)
pipeline3 = BuildingPipeline()
print("=" * 60)
print("  Test 3: Check what we have")
print("=" * 60)
result3 = pipeline3.run("Tell me how many walls we have now and list them", verbose=True)

print()
print("=" * 60)
print("  All tests complete!")
print("=" * 60)
