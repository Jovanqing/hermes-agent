#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vibe Building AI Demo - Non-interactive test

Sends commands to AI and executes them in Revit
"""

import os
import sys
import json

os.environ["OPENAI_API_KEY"] = "sk-e39ef94abba74acb8ffed3a6ca9752ea"
os.environ["OPENAI_BASE_URL"] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import revit_api


SYSTEM_PROMPT = """You are a professional BIM modeling assistant for VibeBuilding.
You help users create building elements in Revit using natural language.

Available functions:
1. create_wall(start_x, start_y, end_x, end_y, height, level) - Create a wall
2. create_room(x1, y1, x2, y2, height, level) - Create a rectangular room (4 walls)
3. list_walls() - List all walls
4. get_levels() - Get all levels
5. delete_wall(wall_id) - Delete a wall
6. delete_all_walls() - Delete all walls

Coordinate system:
- X axis: East-West (positive = East)
- Y axis: North-South (positive = North)
- Units: meters

When the user describes what they want:
1. Understand the intent
2. Choose reasonable coordinates if not specified
3. Call the appropriate function
4. Report the result concisely in Chinese

If no coordinates are specified, start from origin (0,0) or next to existing elements.
Always respond in Chinese."""

FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_wall",
            "description": "Create a wall between two points",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "number", "description": "Start X coordinate (meters)"},
                    "start_y": {"type": "number", "description": "Start Y coordinate (meters)"},
                    "end_x": {"type": "number", "description": "End X coordinate (meters)"},
                    "end_y": {"type": "number", "description": "End Y coordinate (meters)"},
                    "height": {"type": "number", "description": "Wall height (meters)", "default": 3.0},
                    "level": {"type": "string", "description": "Level name", "default": "Level 1"}
                },
                "required": ["start_x", "start_y", "end_x", "end_y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_room",
            "description": "Create a rectangular room with 4 walls",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "number", "description": "Bottom-left X (meters)"},
                    "y1": {"type": "number", "description": "Bottom-left Y (meters)"},
                    "x2": {"type": "number", "description": "Top-right X (meters)"},
                    "y2": {"type": "number", "description": "Top-right Y (meters)"},
                    "height": {"type": "number", "description": "Wall height (meters)", "default": 3.0},
                    "level": {"type": "string", "description": "Level name", "default": "Level 1"}
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
            "name": "delete_wall",
            "description": "Delete a wall by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "wall_id": {"type": "integer", "description": "Wall ID"}
                },
                "required": ["wall_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_all_walls",
            "description": "Delete all walls in the model",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]


def execute_function(name, args):
    """Execute a Revit API function."""
    try:
        if name == "create_wall":
            return revit_api.create_wall(**args)
        elif name == "create_room":
            return revit_api.create_room(**args)
        elif name == "list_walls":
            walls = revit_api.list_walls()
            return {"walls": walls[:10], "count": len(walls)}
        elif name == "get_levels":
            levels = revit_api.get_levels()
            return {"levels": levels, "count": len(levels)}
        elif name == "delete_wall":
            return revit_api.delete_wall(args["wall_id"])
        elif name == "delete_all_walls":
            return revit_api.delete_all_walls()
        else:
            return {"error": f"Unknown function: {name}"}
    except Exception as e:
        return {"error": str(e)}


def run_command(client, user_message):
    """Send a command to AI and execute it."""
    print(f"\n[User] {user_message}")
    print("-" * 60)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=messages,
            tools=FUNCTIONS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1000
        )

        msg = response.choices[0].message

        # Check for tool calls
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                print(f"  AI calls: {func_name}({func_args})")

                # Execute the function
                result = execute_function(func_name, func_args)
                print(f"  Result: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}")

                # Add function call and result to messages
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": tool_call.function.arguments
                        }
                    }]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            # Get final response with function results
            final_response = client.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            print(f"\n[AI] {final_response.choices[0].message.content}")

        else:
            print(f"\n[AI] {msg.content}")

    except Exception as e:
        print(f"  Error: {e}")


def main():
    print("=" * 60)
    print("  Vibe Building AI Demo")
    print("  Powered by Qwen (DashScope) + Revit API")
    print("=" * 60)

    # Check Revit connection
    print("\nChecking Revit API...")
    try:
        health = revit_api.health_check()
        if health.get("status") == "ok":
            print(f"  [OK] Revit connected: {health.get('document_name', 'Unknown')}")
        else:
            print(f"  [FAIL] Revit not responding")
            return
    except Exception as e:
        print(f"  [FAIL] {e}")
        return

    # Initialize AI client
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"]
    )

    # Test AI
    print("\nTesting AI (Qwen)...")
    try:
        test_resp = client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "Say hello in Chinese, one word only"}],
            max_tokens=10
        )
        print(f"  [OK] AI responding: {test_resp.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"  [FAIL] AI error: {e}")
        return

    print("\n" + "=" * 60)
    print("  Running demo commands...")
    print("=" * 60)

    # Demo commands
    commands = [
        "List all walls in the model",
        "Create a 5x4 meter bedroom starting at position (20, 20)",
        "List all walls again to see the new bedroom"
    ]

    for cmd in commands:
        run_command(client, cmd)
        print("\n" + "=" * 60)

    print("\nDemo complete!")
    print("\nTo use interactively, run:")
    print("  F:/Anaconda/envs/hermes/python.exe vibe_building_simple.py")


if __name__ == "__main__":
    main()
