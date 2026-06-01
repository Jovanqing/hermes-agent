#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create an L-shaped corridor using AI
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

When creating complex shapes like L-shaped corridors:
- Break them into multiple rectangular sections
- Use create_room for each rectangular section
- Make sure sections connect properly
- Explain the layout in Chinese

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
            max_tokens=2000
        )

        msg = response.choices[0].message

        # Handle multiple tool calls
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                print(f"  -> {func_name}({func_args})")

                # Execute the function
                result = execute_function(func_name, func_args)

                # Print result summary
                if 'success' in result:
                    print(f"     Success: {result.get('success')}")
                    if 'room_dimensions' in result:
                        print(f"     Room: {result.get('room_dimensions')}")
                    if 'area_sqm' in result:
                        print(f"     Area: {result.get('area_sqm')} sqm")
                elif 'count' in result:
                    print(f"     Count: {result.get('count')}")
                elif 'error' in result:
                    print(f"     Error: {result.get('error')}")

                # Add to messages
                messages.append({
                    "role": "assistant",
                    "content": None,
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

            # Get final response
            final_response = client.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            final_msg = final_response.choices[0].message.content
            print(f"\n[AI] {final_msg}")
            return final_msg

        else:
            print(f"\n[AI] {msg.content}")
            return msg.content

    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("=" * 60)
    print("  Vibe Building - L-Shaped Corridor Demo")
    print("=" * 60)

    # Check Revit connection
    print("\nChecking Revit API...")
    try:
        health = revit_api.health_check()
        if health.get("status") == "ok":
            print(f"  [OK] Revit connected")
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

    print("\n" + "=" * 60)
    print("  Command: Create an L-shaped corridor")
    print("=" * 60)

    # First delete all walls for a clean start
    print("\n[Step 1] Clearing existing walls...")
    revit_api.delete_all_walls()
    print("  Done!")

    # Now create the L-shaped corridor
    run_command(client, "创建一个 L 形走廊。走廊宽度为 2 米。水平部分长 10 米，从 (0,0) 到 (10,2)。垂直部分长 8 米，从 (8,0) 到 (10,8)。两部分在角落连接形成 L 形。")

    print("\n" + "=" * 60)
    print("  Demo complete! Check Revit to see the L-shaped corridor.")
    print("=" * 60)


if __name__ == "__main__":
    main()
