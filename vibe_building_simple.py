#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vibe Building - AI 驱动的 Revit 建筑建模助手

使用阿里云 DashScope (通义千问) + Revit API
"""

import os
import sys
import json

# 配置 DashScope API
os.environ["OPENAI_API_KEY"] = "sk-e39ef94abba74acb8ffed3a6ca9752ea"
os.environ["OPENAI_BASE_URL"] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

try:
    from openai import OpenAI
except ImportError:
    print("需要安装 openai: pip install openai")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import revit_api


# 系统提示词
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

# 可用函数定义
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


def chat_with_ai(client, user_message, history):
    """Send message to AI and get response with possible function calls."""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

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

                print(f"   -> {func_name}({func_args})")

                # Execute the function
                result = execute_function(func_name, func_args)

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

            return final_response.choices[0].message.content, func_name, result

        else:
            return msg.content, None, None

    except Exception as e:
        return f"AI error: {e}", None, None


def main():
    print("=" * 60)
    print("  Vibe Building - AI Revit Modeling Assistant")
    print("  Powered by Qwen (DashScope) + Revit API")
    print("=" * 60)
    print()

    # Check Revit connection
    print("Checking Revit API...")
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

    print()

    # Initialize AI client
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"]
    )

    # Test AI
    print("Testing AI (Qwen)...")
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

    print()
    print("=" * 60)
    print("  Ready! Describe what you want to build.")
    print()
    print("  Examples:")
    print("    - 'Create a 5x4 meter bedroom'")
    print("    - 'Build a wall from (0,0) to (10,0)'")
    print("    - 'List all walls'")
    print("    - 'Delete all walls and create a living room'")
    print()
    print("  Type 'quit' to exit")
    print("=" * 60)
    print()

    history = []

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            # Get AI response
            response, func_name, func_result = chat_with_ai(client, user_input, history)

            print(f"\nAI: {response}\n")

            # Update history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})

            # Keep history manageable
            if len(history) > 20:
                history = history[-20:]

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
