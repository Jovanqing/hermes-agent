#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test for Vibe Building AI
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Vibe Building AI Test")
print("=" * 60)
print()

# Test 1: Revit API connection
print("[1/4] Testing Revit API connection...")
try:
    from tools import revit_api
    health = revit_api.health_check()
    if health.get("status") == "ok":
        print(f"   [OK] Revit connected")
        print(f"   Version: {health.get('version')}")
        print(f"   Document: {health.get('document')}")
    else:
        print(f"   [FAIL] Revit API returned: {health}")
        sys.exit(1)
except Exception as e:
    print(f"   [FAIL] Connection failed: {e}")
    sys.exit(1)

print()

# Test 2: Query walls
print("[2/4] Testing wall query...")
try:
    walls = revit_api.list_walls()
    print(f"   [OK] Found {len(walls)} walls")
    if walls:
        print(f"   Example: Wall #{walls[0].get('id')} - {walls[0].get('type')}")
except Exception as e:
    print(f"   [FAIL] Query failed: {e}")
    sys.exit(1)

print()

# Test 3: Query levels
print("[3/4] Testing level query...")
try:
    levels = revit_api.get_levels()
    print(f"   [OK] Found {len(levels)} levels")
    for level in levels[:3]:
        print(f"   - {level.get('name')} @ {level.get('elevation')}")
except Exception as e:
    print(f"   [FAIL] Query failed: {e}")
    sys.exit(1)

print()

# Test 4: OpenAI API
print("[4/4] Testing OpenAI API...")
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("   [WARN] OPENAI_API_KEY environment variable not set")
    print("   AI assistant needs OpenAI API key to run")
    print()
    print("   How to set:")
    print("   Windows CMD: set OPENAI_API_KEY=your-key-here")
    print("   PowerShell: $env:OPENAI_API_KEY='your-key-here'")
    print("   Linux/Mac: export OPENAI_API_KEY=your-key-here")
else:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # Simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print(f"   [OK] OpenAI API connected")
    except Exception as e:
        print(f"   [FAIL] OpenAI API call failed: {e}")
        sys.exit(1)

print()
print("=" * 60)
print("[OK] All tests passed!")
print()
print("You can now run the AI assistant:")
print("  F:/Anaconda/envs/hermes/python.exe vibe_building_simple.py")
print("=" * 60)
