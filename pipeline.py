# -*- coding: utf-8 -*-
"""
Vibe Building - Interactive AI Pipeline (Optimized)

Natural language driven Revit BIM modeling with:
- Streaming AI responses
- Rich terminal output
- Command shortcuts (/help, /walls, /undo, /villa, /clear)
- Session history
- Better error handling
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Optional

try:
    import readline  # Unix/macOS only
except ImportError:
    pass  # Windows doesn't have readline, that's OK

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("OPENAI_API_KEY", "sk-e39ef94abba74acb8ffed3a6ca9752ea")
os.environ.setdefault("OPENAI_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")

from openai import OpenAI
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import revit_api

# ============================================================================
# Terminal Colors
# ============================================================================

class C:
    """ANSI color codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    @staticmethod
    def disable():
        for attr in dir(C):
            if not attr.startswith("_") and attr != "disable" and isinstance(getattr(C, attr), str):
                setattr(C, attr, "")

# Disable colors if not a terminal
if not sys.stdout.isatty():
    C.disable()


def header(text):
    print(f"\n{C.BOLD}{C.CYAN}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{C.RESET}\n")

def step(num, total, label):
    print(f"  {C.GRAY}[{num}/{total}]{C.RESET} {label}...", end=" ", flush=True)

def ok(text="OK"):
    print(f"{C.GREEN}{text}{C.RESET}")

def fail(text="FAIL"):
    print(f"{C.RED}{text}{C.RESET}")

def info(text):
    print(f"  {C.GRAY}{text}{C.RESET}")

def result(text):
    print(f"\n  {C.BOLD}{C.WHITE}{text}{C.RESET}")

def ai_say(text):
    print(f"\n  {C.BOLD}{C.BLUE}AI:{C.RESET} {text}")


# ============================================================================
# System Prompt
# ============================================================================

SYSTEM_PROMPT = """You are a professional BIM modeling assistant for VibeBuilding.
You help users create building elements in Revit using natural language.

IMPORTANT:
- Only execute what the user CURRENTLY asks. Do NOT repeat previous commands.
- Each user message is a new, independent request.
- Always respond in Chinese.
- Be concise in your responses.

Available functions:
1. create_wall(start_x, start_y, end_x, end_y, height, level) - Create a wall
2. create_room(x1, y1, x2, y2, height, level) - Create a rectangular room (4 walls)
3. list_walls() - List all walls in the model
4. get_levels() - Get all levels/floors
5. delete_all_walls() - Delete all walls
6. get_model_info() - Get model summary (wall count, levels, etc.)
7. list_families(category, name) - List available family types (doors, windows, furniture)
8. place_door(wall_id, position_x, position_y, level) - Place a door in a wall
9. place_window(wall_id, position_x, position_y, level) - Place a window in a wall
10. create_floor(corners, level) - Create a floor slab
11. build_villa(steps) - Build complete two-story villa (levels, walls, floors, windows, doors)

Coordinate system:
- X axis: East-West (positive = East)
- Y axis: North-South (positive = North)
- Units: meters

For complex shapes, break into multiple rectangular sections.
When building a villa, use build_villa to create the complete structure in one call.
"""

FUNCTIONS = [
    {"type": "function", "function": {
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
    }},
    {"type": "function", "function": {
        "name": "create_room",
        "description": "Create a rectangular room with 4 walls",
        "parameters": {
            "type": "object",
            "properties": {
                "x1": {"type": "number"}, "y1": {"type": "number"},
                "x2": {"type": "number"}, "y2": {"type": "number"},
                "height": {"type": "number", "default": 3.0},
                "level": {"type": "string", "default": "Level 1"}
            },
            "required": ["x1", "y1", "x2", "y2"]
        }
    }},
    {"type": "function", "function": {
        "name": "list_walls", "description": "List all walls in the model",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "get_levels", "description": "Get all levels/floors",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "delete_all_walls", "description": "Delete all walls",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "get_model_info", "description": "Get model summary",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "list_families",
        "description": "List available family types (doors, windows, furniture, columns, floors, roofs)",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category: doors, windows, furniture, columns, floors, roofs"},
                "name": {"type": "string", "description": "Name filter substring"}
            }
        }
    }},
    {"type": "function", "function": {
        "name": "place_door",
        "description": "Place a door in an existing wall",
        "parameters": {
            "type": "object",
            "properties": {
                "wall_id": {"type": "integer", "description": "Host wall element ID"},
                "position_x": {"type": "number", "description": "X position along wall (meters)"},
                "position_y": {"type": "number", "default": 0.0},
                "level": {"type": "string", "default": "Level 1"}
            },
            "required": ["wall_id", "position_x"]
        }
    }},
    {"type": "function", "function": {
        "name": "place_window",
        "description": "Place a window in an existing wall",
        "parameters": {
            "type": "object",
            "properties": {
                "wall_id": {"type": "integer", "description": "Host wall element ID"},
                "position_x": {"type": "number", "description": "X position along wall (meters)"},
                "position_y": {"type": "number", "default": 0.0},
                "level": {"type": "string", "default": "Level 1"}
            },
            "required": ["wall_id", "position_x"]
        }
    }},
    {"type": "function", "function": {
        "name": "create_floor",
        "description": "Create a floor slab from polygon corners",
        "parameters": {
            "type": "object",
            "properties": {
                "corners": {"type": "string", "description": "JSON array of corner points, e.g. '[{\"x\":0,\"y\":0},{\"x\":14,\"y\":0},{\"x\":14,\"y\":10},{\"x\":0,\"y\":10}]'"},
                "level": {"type": "string", "default": "Level 1"}
            },
            "required": ["corners"]
        }
    }},
    {"type": "function", "function": {
        "name": "build_villa",
        "description": "Build the complete two-story VibeVilla (14m x 10m, ~250 sqm, 16 rooms, walls, floors, windows, doors)",
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {"type": "string", "description": "Comma-separated steps: levels,grids,walls,floors,roof,windows,doors,rooms (default: all)"}
            }
        }
    }},
]


# ============================================================================
# Execute Revit Functions
# ============================================================================

def execute_function(name, args):
    """Dispatch to the correct revit_api function."""
    try:
        if name == "create_wall":
            return revit_api.create_wall(
                start_x=args["start_x"], start_y=args["start_y"],
                end_x=args["end_x"], end_y=args["end_y"],
                height=args.get("height", 3.0),
                level=args.get("level", "Level 1"),
            )
        elif name == "create_room":
            return revit_api.create_room(
                x1=args["x1"], y1=args["y1"],
                x2=args["x2"], y2=args["y2"],
                height=args.get("height", 3.0),
                level=args.get("level", "Level 1"),
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
                "revit_version": health.get("revit_version"),
                "wall_count": len(walls),
                "level_count": len(levels),
            }
        elif name == "list_families":
            result = revit_api._make_request("model/families")
            return result
        elif name == "place_door":
            return revit_api._make_request("doors", method="POST", data={
                "wall_id": args["wall_id"],
                "position": {"x": args["position_x"], "y": args.get("position_y", 0)},
                "level": args.get("level", "Level 1"),
            })
        elif name == "place_window":
            return revit_api._make_request("windows", method="POST", data={
                "wall_id": args["wall_id"],
                "position": {"x": args["position_x"], "y": args.get("position_y", 0)},
                "level": args.get("level", "Level 1"),
            })
        elif name == "create_floor":
            corners = json.loads(args["corners"]) if isinstance(args["corners"], str) else args["corners"]
            return revit_api._make_request("floors", method="POST", data={
                "corners": corners,
                "level": args.get("level", "Level 1"),
            })
        elif name == "build_villa":
            step_str = args.get("steps", "levels,grids,walls,floors,roof,windows,doors,rooms")
            step_list = [s.strip() for s in step_str.split(",")]
            return revit_api._make_request("villa/build", method="POST", data={
                "steps": step_list,
            })
        else:
            return {"error": f"Unknown function: {name}"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# AI Interaction
# ============================================================================

def process_command(ai, user_input, history):
    """Process a user command through AI and execute in Revit."""
    start_time = time.time()

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_input})

    # Step 1: AI understanding
    step(1, 3, "AI understanding")
    try:
        response = ai.chat.completions.create(
            model="qwen-plus",
            messages=messages,
            tools=FUNCTIONS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=2000,
        )
        msg = response.choices[0].message
        ok()
    except Exception as e:
        fail(f"AI error: {e}")
        return None

    # Step 2: Execute tool calls
    tool_calls = msg.tool_calls or []
    tool_results = []

    if tool_calls:
        step(2, 3, f"Executing {len(tool_calls)} operation(s)")
        for tc in tool_calls:
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)

            r = execute_function(func_name, func_args)
            tool_results.append({
                "function": func_name,
                "args": func_args,
                "result": r,
            })

            # Add to messages for follow-up
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": tc.id, "type": "function",
                    "function": {"name": func_name, "arguments": tc.function.arguments}}],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(r, ensure_ascii=False),
            })

        # Summarize
        for tr in tool_results:
            r = tr["result"]
            fn = tr["function"]
            if r.get("success"):
                if "room_dimensions" in r:
                    info(f"  -> {fn}: {r['room_dimensions']}, {r.get('area_sqm', '?')} sqm")
                elif "wall_id" in r:
                    info(f"  -> {fn}: wall #{r['wall_id']}")
                elif "count" in r:
                    info(f"  -> {fn}: {r['count']} items")
                elif "total_elements_created" in r:
                    info(f"  -> {fn}: {r['total_elements_created']} elements created")
                else:
                    info(f"  -> {fn}: OK")
            elif r.get("error"):
                info(f"  -> {fn}: ERROR - {r['error'][:60]}")
        ok(f"{len(tool_results)} done")
    else:
        step(2, 3, "No operations needed")
        ok("skipped")

    # Step 3: Generate report
    step(3, 3, "AI report")
    try:
        if tool_calls:
            final_response = ai.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            report = final_response.choices[0].message.content or ""
        else:
            report = msg.content or ""
        ok()
    except Exception as e:
        report = str(msg.content or "")
        ok("(from step 1)")

    elapsed = time.time() - start_time
    info(f"  Completed in {elapsed:.1f}s")

    return {
        "report": report,
        "tool_results": tool_results,
        "elapsed": elapsed,
    }


# ============================================================================
# Quick Commands
# ============================================================================

QUICK_COMMANDS = {
    "/help": """
  Quick Commands:
    /help          Show this help
    /walls         List all walls
    /levels        List all levels
    /info          Model summary
    /villa         Build complete two-story villa
    /families      List available family types
    /doors         List available door types
    /windows       List available window types
    /clear         Clear screen
    /history       Show command history
    /quit          Exit
""",
    "/walls": "List all walls in the model",
    "/levels": "List all levels and their elevations",
    "/info": "Show model summary including wall count, levels, and element types",
    "/villa": "Build the complete two-story VibeVilla with all elements (levels, walls, floors, windows, doors)",
    "/families": "List all available family symbols in the model",
    "/doors": "List all available door family types",
    "/windows": "List all available window family types",
    "/clear": None,
    "/history": None,
    "/quit": None,
}

def expand_quick_command(cmd):
    """Convert quick command to natural language prompt."""
    cmd_lower = cmd.lower().strip()
    mapping = {
        "/walls": "List all walls in the Revit model",
        "/levels": "List all levels and their elevations",
        "/info": "Show model summary including wall count, levels, and element types",
        "/villa": "Build the complete two-story VibeVilla with all elements",
        "/families": "List all available family symbols in the model",
        "/doors": "List all available door family types in the model",
        "/windows": "List all available window family types in the model",
    }
    return mapping.get(cmd_lower, None)


# ============================================================================
# Main Interactive Loop
# ============================================================================

def main():
    header("Vibe Building - AI Revit Modeling Assistant")

    # Check Revit connection
    print(f"  {C.GRAY}Checking Revit connection...{C.RESET}", end=" ", flush=True)
    try:
        health = revit_api.health_check()
        if health.get("status") == "ok":
            doc = health.get("document_name", "Unknown")
            ver = health.get("revit_version", "?")
            print(f"{C.GREEN}Connected{C.RESET}")
            info(f"  Document: {doc} | Revit {ver}")
        else:
            print(f"{C.RED}Failed{C.RESET}")
            info(f"  Make sure Revit is running with VibeBuilding extension")
            return
    except Exception as e:
        print(f"{C.RED}Error: {e}{C.RESET}")
        return

    # Initialize AI
    print(f"  {C.GRAY}Initializing AI (Qwen)...{C.RESET}", end=" ", flush=True)
    try:
        ai = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"],
        )
        # Quick test
        ai.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        print(f"{C.GREEN}Ready{C.RESET}")
    except Exception as e:
        print(f"{C.RED}Error: {e}{C.RESET}")
        return

    print()
    info("  Type your building commands in natural language.")
    info("  Try: 'build a 5x4 meter bedroom' or '/villa' for full demo")
    info("  Type /help for quick commands, /quit to exit")
    print()

    history = []
    command_history = []

    while True:
        try:
            user_input = input(f"{C.BOLD}{C.GREEN}You:{C.RESET} ").strip()

            if not user_input:
                continue

            # Handle quick commands
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]

                if cmd in ("/quit", "/exit", "/q"):
                    print(f"\n  {C.GRAY}Goodbye!{C.RESET}\n")
                    break

                if cmd == "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    continue

                if cmd == "/history":
                    print(f"\n  {C.BOLD}Command History:{C.RESET}")
                    for i, h in enumerate(command_history[-20:], 1):
                        print(f"    {i}. {h}")
                    print()
                    continue

                if cmd == "/help":
                    print(QUICK_COMMANDS["/help"])
                    continue

                # Expand to natural language
                expanded = expand_quick_command(cmd)
                if expanded:
                    info(f"  -> {expanded}")
                    user_input = expanded
                else:
                    info(f"  Unknown command: {cmd}. Type /help for options.")
                    continue

            command_history.append(user_input)

            # Process through AI pipeline
            print()
            output = process_command(ai, user_input, history)

            if output and output.get("report"):
                ai_say(output["report"])
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": output["report"]})

                # Keep history manageable
                if len(history) > 20:
                    history = history[-20:]

            print()

        except KeyboardInterrupt:
            print(f"\n\n  {C.GRAY}Goodbye!{C.RESET}\n")
            break
        except EOFError:
            break
        except Exception as e:
            print(f"\n  {C.RED}Error: {e}{C.RESET}\n")


if __name__ == "__main__":
    main()
