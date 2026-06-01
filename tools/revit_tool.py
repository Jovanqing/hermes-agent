#!/usr/bin/env python3
"""
Revit Building Tool - AI-driven BIM modeling via pyRevit HTTP API.

Allows the agent to create and modify building elements in Revit
by sending HTTP requests to the VibeBuilding pyRevit extension.

Requirements:
- Revit 2025 running with VibeBuilding extension loaded
- pyRevit routes server active (default port 48884)
"""

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from tools.registry import registry

logger = logging.getLogger(__name__)

# Default Revit API endpoint
DEFAULT_REVIT_HOST = os.environ.get("REVIT_HOST", "localhost")
DEFAULT_REVIT_PORT = int(os.environ.get("REVIT_PORT", "48884"))
REVIT_API_PREFIX = "vibe-building"


def _revit_request(
    method: str,
    path: str,
    data: Optional[Dict] = None,
    host: str = DEFAULT_REVIT_HOST,
    port: int = DEFAULT_REVIT_PORT,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Make an HTTP request to the pyRevit routes server.

    Args:
        method: HTTP method (GET, POST, DELETE)
        path: API path (appended to base URL)
        data: Request body for POST requests
        host: Revit host address
        port: pyRevit routes server port
        timeout: Request timeout in seconds

    Returns:
        Response data as dict

    Raises:
        ConnectionError: If cannot connect to Revit
    """
    url = f"http://{host}:{port}/{REVIT_API_PREFIX}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib_request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            response_data = response.read().decode("utf-8")
            if response_data:
                return json.loads(response_data)
            return {}

    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        try:
            error_data = json.loads(error_body)
        except json.JSONDecodeError:
            error_data = {"error": error_body}

        logger.error("Revit API error %d: %s", e.code, error_data)
        return {"error": f"HTTP {e.code}: {error_data.get('error', 'Unknown error')}"}

    except URLError as e:
        logger.error("Cannot connect to Revit at %s: %s", url, e.reason)
        return {
            "error": f"Cannot connect to Revit at {url}. "
                     f"Make sure Revit is running with the VibeBuilding extension. "
                     f"Error: {e.reason}"
        }


def check_revit_available() -> bool:
    """Check if Revit is running and the API is accessible."""
    try:
        result = _revit_request("GET", "/health", timeout=5.0)
        return result.get("status") == "ok"
    except Exception:
        return False


# =============================================================================
# Tool Handlers
# =============================================================================


def revit_health() -> str:
    """Check if Revit is connected and accessible."""
    result = _revit_request("GET", "/health")
    return json.dumps(result, ensure_ascii=False, indent=2)


def revit_get_levels() -> str:
    """Get all levels/floors in the Revit model."""
    result = _revit_request("GET", "/model/levels")
    return json.dumps(result, ensure_ascii=False, indent=2)


def revit_get_wall_types() -> str:
    """Get available wall types in the Revit model."""
    result = _revit_request("GET", "/wall-types")
    return json.dumps(result, ensure_ascii=False, indent=2)


def revit_list_walls() -> str:
    """List all walls in the current Revit model."""
    result = _revit_request("GET", "/walls")
    return json.dumps(result, ensure_ascii=False, indent=2)


def revit_create_wall(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    height: float = 3.0,
    level: str = "Level 1",
    wall_type: Optional[str] = None,
    start_z: float = 0.0,
    end_z: float = 0.0,
) -> str:
    """Create a wall in the Revit model.

    Args:
        start_x: Start point X coordinate (meters)
        start_y: Start point Y coordinate (meters)
        end_x: End point X coordinate (meters)
        end_y: End point Y coordinate (meters)
        height: Wall height in meters (default: 3.0)
        level: Level name (default: "Level 1")
        wall_type: Wall type name (optional, uses default if not specified)
        start_z: Start point Z coordinate (meters, default: 0)
        end_z: End point Z coordinate (meters, default: 0)

    Returns:
        JSON string with wall creation result
    """
    data = {
        "start": {"x": start_x, "y": start_y, "z": start_z},
        "end": {"x": end_x, "y": end_y, "z": end_z},
        "height": height,
        "level": level,
    }
    if wall_type:
        data["wall_type"] = wall_type

    result = _revit_request("POST", "/walls", data)
    return json.dumps(result, ensure_ascii=False, indent=2)


def revit_create_room(
    name: str,
    x1: float,
    z1: float,
    x2: float,
    z2: float,
    level: str = "Level 1",
    height: float = 3.0,
) -> str:
    """Create a room by building four walls.

    Args:
        name: Room name (e.g., "客厅", "Bedroom")
        x1: First corner X coordinate (meters)
        z1: First corner Z coordinate (meters)
        x2: Opposite corner X coordinate (meters)
        z2: Opposite corner Z coordinate (meters)
        level: Level name (default: "Level 1")
        height: Wall height in meters (default: 3.0)

    Returns:
        JSON string with room creation result
    """
    data = {
        "name": name,
        "x1": x1,
        "z1": z1,
        "x2": x2,
        "z2": z2,
        "level": level,
        "height": height,
    }

    result = _revit_request("POST", "/room", data)
    return json.dumps(result, ensure_ascii=False, indent=2)


def revit_build_floor(
    floor_name: str,
    level: str,
    rooms: list,
) -> str:
    """Build all rooms for a floor from a layout definition.

    Args:
        floor_name: Name of the floor (e.g., "一层", "First Floor")
        level: Level name in Revit
        rooms: List of room definitions, each with:
            - name: Room name
            - x1, z1: First corner coordinates
            - x2, z2: Opposite corner coordinates

    Returns:
        JSON string with floor building result
    """
    data = {
        "floor_name": floor_name,
        "level": level,
        "rooms": rooms,
    }

    result = _revit_request("POST", "/build/floor", data)
    return json.dumps(result, ensure_ascii=False, indent=2)


def revit_get_model_info() -> str:
    """Get information about the current Revit model."""
    # Get basic info
    health = _revit_request("GET", "/health")
    levels = _revit_request("GET", "/model/levels")
    walls = _revit_request("GET", "/walls")

    info = {
        "document": health.get("document_name"),
        "revit_version": health.get("revit_version"),
        "levels": levels.get("levels", []),
        "wall_count": walls.get("count", 0),
    }

    return json.dumps(info, ensure_ascii=False, indent=2)


# =============================================================================
# Tool Registration
# =============================================================================

registry.register(
    name="revit_health",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_health",
            "description": "Check if Revit is running and accessible via the VibeBuilding API.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    handler=revit_health,
    check_fn=check_revit_available,
    description="Check Revit connection status",
    emoji="🏗️",
)

registry.register(
    name="revit_get_levels",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_get_levels",
            "description": "Get all levels/floors in the Revit model with their elevations.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    handler=revit_get_levels,
    check_fn=check_revit_available,
    description="List Revit levels",
    emoji="🏗️",
)

registry.register(
    name="revit_get_wall_types",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_get_wall_types",
            "description": "Get available wall types in the Revit model.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    handler=revit_get_wall_types,
    check_fn=check_revit_available,
    description="List wall types",
    emoji="🏗️",
)

registry.register(
    name="revit_list_walls",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_list_walls",
            "description": "List all walls in the current Revit model with their positions and dimensions.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    handler=revit_list_walls,
    check_fn=check_revit_available,
    description="List all walls",
    emoji="🏗️",
)

registry.register(
    name="revit_create_wall",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_create_wall",
            "description": (
                "Create a wall in the Revit model. Coordinates are in meters. "
                "The wall is created on the specified level with the given height."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_x": {
                        "type": "number",
                        "description": "Start point X coordinate in meters",
                    },
                    "start_y": {
                        "type": "number",
                        "description": "Start point Y coordinate in meters",
                    },
                    "end_x": {
                        "type": "number",
                        "description": "End point X coordinate in meters",
                    },
                    "end_y": {
                        "type": "number",
                        "description": "End point Y coordinate in meters",
                    },
                    "height": {
                        "type": "number",
                        "description": "Wall height in meters (default: 3.0)",
                        "default": 3.0,
                    },
                    "level": {
                        "type": "string",
                        "description": "Level name in Revit (default: 'Level 1')",
                        "default": "Level 1",
                    },
                    "wall_type": {
                        "type": "string",
                        "description": "Wall type name (optional, uses default if not specified)",
                    },
                },
                "required": ["start_x", "start_y", "end_x", "end_y"],
            },
        },
    },
    handler=revit_create_wall,
    check_fn=check_revit_available,
    description="Create a wall in Revit",
    emoji="🧱",
)

registry.register(
    name="revit_create_room",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_create_room",
            "description": (
                "Create a room by building four walls. Define the room by two opposite corners. "
                "Coordinates are in meters. The room will have walls on all four sides."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Room name (e.g., '客厅', 'Bedroom', 'Kitchen')",
                    },
                    "x1": {
                        "type": "number",
                        "description": "First corner X coordinate in meters",
                    },
                    "z1": {
                        "type": "number",
                        "description": "First corner Z coordinate in meters",
                    },
                    "x2": {
                        "type": "number",
                        "description": "Opposite corner X coordinate in meters",
                    },
                    "z2": {
                        "type": "number",
                        "description": "Opposite corner Z coordinate in meters",
                    },
                    "level": {
                        "type": "string",
                        "description": "Level name in Revit (default: 'Level 1')",
                        "default": "Level 1",
                    },
                    "height": {
                        "type": "number",
                        "description": "Wall height in meters (default: 3.0)",
                        "default": 3.0,
                    },
                },
                "required": ["name", "x1", "z1", "x2", "z2"],
            },
        },
    },
    handler=revit_create_room,
    check_fn=check_revit_available,
    description="Create a room with four walls",
    emoji="🏠",
)

registry.register(
    name="revit_build_floor",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_build_floor",
            "description": (
                "Build all rooms for a floor from a layout definition. "
                "Use this to create multiple rooms at once for an entire floor plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "floor_name": {
                        "type": "string",
                        "description": "Name of the floor (e.g., '一层', 'First Floor')",
                    },
                    "level": {
                        "type": "string",
                        "description": "Level name in Revit",
                    },
                    "rooms": {
                        "type": "array",
                        "description": "List of room definitions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "x1": {"type": "number"},
                                "z1": {"type": "number"},
                                "x2": {"type": "number"},
                                "z2": {"type": "number"},
                            },
                            "required": ["name", "x1", "z1", "x2", "z2"],
                        },
                    },
                },
                "required": ["floor_name", "level", "rooms"],
            },
        },
    },
    handler=revit_build_floor,
    check_fn=check_revit_available,
    description="Build entire floor layout",
    emoji="🏢",
)

registry.register(
    name="revit_get_model_info",
    toolset="revit",
    schema={
        "type": "function",
        "function": {
            "name": "revit_get_model_info",
            "description": "Get comprehensive information about the current Revit model including levels, wall count, and document info.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    handler=revit_get_model_info,
    check_fn=check_revit_available,
    description="Get model information",
    emoji="📊",
)
