#!/usr/bin/env python3
"""
Revit MCP Server - Model Context Protocol server for Revit BIM modeling.

Exposes Revit operations as MCP tools that can be used by any MCP-compatible
AI agent (hermes-agent, Claude Desktop, etc.).

Transport: stdio (stdin/stdout JSON-RPC)
Revit API: pyRevit Routes HTTP server at localhost:48884

Usage:
  python revit_mcp_server.py

Configure in ~/.hermes/config.yaml:
  mcp_servers:
    revit:
      command: "F:/Anaconda/envs/hermes/python.exe"
      args: ["F:/VibeBuilding/mcp/revit_mcp_server.py"]
      timeout: 120
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

# MCP SDK
from mcp.server.fastmcp import FastMCP

# =============================================================================
# Configuration
# =============================================================================

REVIT_HOST = os.environ.get("REVIT_HOST", "localhost")
REVIT_PORT = int(os.environ.get("REVIT_PORT", "48884"))
REVIT_API_PREFIX = "vibe-building"
BASE_URL = f"http://{REVIT_HOST}:{REVIT_PORT}/{REVIT_API_PREFIX}"

# =============================================================================
# Revit HTTP Client (same as tools/revit_api.py)
# =============================================================================

def _revit_request(method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Send HTTP request to pyRevit Routes server."""
    url = f"{BASE_URL}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib_request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode("utf-8")
            if response_data:
                return json.loads(response_data)
            return {"success": True}
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        try:
            error_data = json.loads(error_body)
        except json.JSONDecodeError:
            error_data = {"error": error_body}
        return {"error": f"HTTP {e.code}: {error_data.get('error', 'Unknown error')}"}
    except URLError as e:
        return {
            "error": f"Cannot connect to Revit at {url}. "
                     f"Make sure Revit is running with VibeBuilding extension. "
                     f"Details: {e.reason}"
        }
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# MCP Server
# =============================================================================

mcp = FastMCP("Revit BIM")


# ---------------------------------------------------------------------------
# Health & Info Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_health() -> str:
    """Check if Revit is running and the VibeBuilding extension is accessible.
    Returns connection status, document name, and Revit version."""
    result = _revit_request("GET", "health")
    if result.get("status") == "ok":
        return json.dumps({
            "status": "connected",
            "document": result.get("document_name", "Unknown"),
            "revit_version": result.get("revit_version", "Unknown"),
        }, ensure_ascii=False)
    else:
        return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def revit_get_model_info() -> str:
    """Get comprehensive information about the current Revit model,
    including document name, levels, wall count, and element categories."""
    health = _revit_request("GET", "health")
    levels = _revit_request("GET", "model/levels")
    walls = _revit_request("GET", "walls")
    elements = _revit_request("GET", "model/elements")

    return json.dumps({
        "document": health.get("document_name"),
        "revit_version": health.get("revit_version"),
        "levels": levels.get("levels", []),
        "wall_count": walls.get("count", 0),
        "elements": elements.get("elements", {}),
    }, ensure_ascii=False)


@mcp.tool()
def revit_get_levels() -> str:
    """Get all levels/floors in the Revit model with their names and elevations."""
    result = _revit_request("GET", "model/levels")
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def revit_get_wall_types() -> str:
    """Get all available wall types in the model with their IDs and thicknesses."""
    result = _revit_request("GET", "wall-types")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Wall Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_list_walls() -> str:
    """List all walls in the current Revit model.
    Returns wall IDs, types, lengths, and coordinates."""
    result = _revit_request("GET", "walls")
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def revit_create_wall(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    height: float = 3.0,
    level: str = "Level 1",
) -> str:
    """Create a wall in the Revit model between two points.

    Args:
        start_x: Start point X coordinate in meters
        start_y: Start point Y coordinate in meters
        end_x: End point X coordinate in meters
        end_y: End point Y coordinate in meters
        height: Wall height in meters (default: 3.0)
        level: Level/floor name (default: "Level 1")
    """
    data = {
        "start": {"x": start_x, "y": start_y, "z": 0},
        "end": {"x": end_x, "y": end_y, "z": 0},
        "height": height,
        "level": level,
    }
    result = _revit_request("POST", "walls", data)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def revit_delete_wall(wall_id: int) -> str:
    """Delete a wall by its element ID.

    Args:
        wall_id: The Revit element ID of the wall to delete
    """
    result = _revit_request("DELETE", f"walls/{wall_id}")
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def revit_delete_all_walls() -> str:
    """Delete all walls in the current Revit model. Use with caution."""
    result = _revit_request("DELETE", "walls/all")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Room Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_create_room(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    height: float = 3.0,
    level: str = "Level 1",
) -> str:
    """Create a rectangular room with 4 walls.

    The room is defined by two opposite corners (bottom-left and top-right).

    Args:
        x1: Bottom-left corner X coordinate in meters
        y1: Bottom-left corner Y coordinate in meters
        x2: Top-right corner X coordinate in meters
        y2: Top-right corner Y coordinate in meters
        height: Wall height in meters (default: 3.0)
        level: Level/floor name (default: "Level 1")
    """
    walls_created = []

    # Bottom wall (y = y1)
    r1 = _revit_request("POST", "walls", {
        "start": {"x": x1, "y": y1, "z": 0},
        "end": {"x": x2, "y": y1, "z": 0},
        "height": height, "level": level,
    })
    walls_created.append(r1)

    # Right wall (x = x2)
    r2 = _revit_request("POST", "walls", {
        "start": {"x": x2, "y": y1, "z": 0},
        "end": {"x": x2, "y": y2, "z": 0},
        "height": height, "level": level,
    })
    walls_created.append(r2)

    # Top wall (y = y2)
    r3 = _revit_request("POST", "walls", {
        "start": {"x": x2, "y": y2, "z": 0},
        "end": {"x": x1, "y": y2, "z": 0},
        "height": height, "level": level,
    })
    walls_created.append(r3)

    # Left wall (x = x1)
    r4 = _revit_request("POST", "walls", {
        "start": {"x": x1, "y": y2, "z": 0},
        "end": {"x": x1, "y": y1, "z": 0},
        "height": height, "level": level,
    })
    walls_created.append(r4)

    width = abs(x2 - x1)
    depth = abs(y2 - y1)
    success_count = sum(1 for w in walls_created if w.get("success"))

    return json.dumps({
        "success": success_count == 4,
        "room_dimensions": f"{width:.1f}m x {depth:.1f}m",
        "area_sqm": round(width * depth, 2),
        "walls_created": success_count,
        "walls_total": 4,
        "wall_ids": [w.get("wall_id") for w in walls_created if w.get("success")],
        "level": level,
        "height_m": height,
    }, ensure_ascii=False)


@mcp.tool()
def revit_build_floor(
    floor_name: str,
    level: str,
    rooms: str,
    height: float = 3.0,
) -> str:
    """Build all rooms for a floor from a JSON layout definition.

    Args:
        floor_name: Name of the floor (e.g., "First Floor")
        level: Level name in Revit
        rooms: JSON string of room definitions, each with name, x1, y1, x2, y2
        height: Wall height in meters (default: 3.0)
    """
    try:
        room_list = json.loads(rooms)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON for rooms parameter"})

    results = []
    for room in room_list:
        r = revit_create_room(
            x1=room["x1"], y1=room["y1"],
            x2=room["x2"], y2=room["y2"],
            height=height, level=level,
        )
        room_result = json.loads(r)
        room_result["name"] = room.get("name", "Room")
        results.append(room_result)

    success_count = sum(1 for r in results if r.get("success"))
    total_area = sum(r.get("area_sqm", 0) for r in results)

    return json.dumps({
        "floor_name": floor_name,
        "level": level,
        "rooms_created": success_count,
        "rooms_total": len(room_list),
        "total_area_sqm": round(total_area, 2),
        "rooms": results,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Family / Type Discovery Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_list_families(category: str = "", name: str = "") -> str:
    """List available family symbols (door types, window types, furniture, etc.).

    Args:
        category: Filter by category: doors, windows, furniture, columns, floors, roofs
        name: Filter by name substring
    """
    params = []
    if category:
        params.append(f"category={category}")
    if name:
        params.append(f"name={name}")
    query = "&".join(params)
    path = f"model/families?{query}" if query else "model/families"
    result = _revit_request("GET", path)
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Door Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_place_door(
    wall_id: int,
    position_x: float,
    position_y: float = 0.0,
    level: str = "Level 1",
) -> str:
    """Place a door in an existing wall.

    Args:
        wall_id: The Revit element ID of the host wall
        position_x: X coordinate along the wall in meters
        position_y: Y coordinate in meters (usually 0)
        level: Level name (default: "Level 1")
    """
    data = {
        "wall_id": wall_id,
        "position": {"x": position_x, "y": position_y},
        "level": level,
    }
    result = _revit_request("POST", "doors", data)
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Window Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_place_window(
    wall_id: int,
    position_x: float,
    position_y: float = 0.0,
    level: str = "Level 1",
) -> str:
    """Place a window in an existing wall.

    Args:
        wall_id: The Revit element ID of the host wall
        position_x: X coordinate along the wall in meters
        position_y: Y coordinate in meters (usually 0)
        level: Level name (default: "Level 1")
    """
    data = {
        "wall_id": wall_id,
        "position": {"x": position_x, "y": position_y},
        "level": level,
    }
    result = _revit_request("POST", "windows", data)
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Floor Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_create_floor(
    corners: str,
    level: str = "Level 1",
) -> str:
    """Create a floor slab from a polygon outline.

    Args:
        corners: JSON string of corner points, e.g. '[{"x":0,"y":0},{"x":14,"y":0},{"x":14,"y":10},{"x":0,"y":10}]'
        level: Level name (default: "Level 1")
    """
    try:
        corner_list = json.loads(corners)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON for corners"})

    data = {
        "corners": corner_list,
        "level": level,
    }
    result = _revit_request("POST", "floors", data)
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Full Villa Build
# ---------------------------------------------------------------------------

@mcp.tool()
def revit_build_villa(
    steps: str = "levels,grids,walls,floors,roof,windows,doors,rooms",
) -> str:
    """Build the complete two-story VibeVilla (14m x 10m, ~250 sqm).

    Creates a full villa with 16 rooms across 2 floors, including walls,
    floors, windows, doors, and room labels.

    Args:
        steps: Comma-separated build steps to execute. Available:
               levels, grids, walls, floors, roof, windows, doors, rooms
               Default: all steps
    """
    step_list = [s.strip() for s in steps.split(",")]
    data = {"steps": step_list}
    result = _revit_request("POST", "villa/build", data)
    return json.dumps(result, ensure_ascii=False)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
