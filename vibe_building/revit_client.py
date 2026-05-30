"""
Revit HTTP Client - Communicates with pyRevit Routes API.

The pyRevit Routes server runs inside Revit and exposes REST endpoints
for creating and modifying BIM elements.

Usage:
    client = RevitClient("http://localhost:48884")

    # Check connection
    health = client.health()

    # Create a wall
    wall = client.create_wall(
        start={"x": 0, "y": 0, "z": 0},
        end={"x": 5000, "y": 0, "z": 0},
        height=3000,
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


@dataclass
class RevitConnection:
    """Connection information for a Revit instance."""

    host: str = "localhost"
    port: int = 48884  # Default pyRevit routes port
    api_prefix: str = "vibe-building"

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/{self.api_prefix}"


@dataclass
class WallInfo:
    """Information about a wall element."""

    id: int
    wall_type: str
    length_mm: float
    height_mm: Optional[float] = None
    start: Optional[Dict[str, float]] = None
    end: Optional[Dict[str, float]] = None
    level: Optional[int] = None


@dataclass
class LevelInfo:
    """Information about a level."""

    id: int
    name: str
    elevation_mm: float
    elevation_ft: float


@dataclass
class ModelInfo:
    """Information about the current Revit model."""

    document_name: str
    document_path: str
    levels: List[LevelInfo] = field(default_factory=list)
    element_counts: Dict[str, int] = field(default_factory=dict)


class RevitClient:
    """HTTP client for pyRevit Routes API.

    Communicates with the VibeBuilding extension running inside Revit.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 48884,
        api_prefix: str = "vibe-building",
        timeout: float = 30.0,
    ):
        """Initialize the Revit client.

        Args:
            host: Revit host address
            port: pyRevit routes server port
            api_prefix: API route prefix
            timeout: Request timeout in seconds
        """
        self.connection = RevitConnection(host, port, api_prefix)
        self.timeout = timeout

    @property
    def base_url(self) -> str:
        return self.connection.base_url

    # -------------------------------------------------------------------------
    # HTTP methods
    # -------------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the pyRevit routes server.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API path (appended to base_url)
            data: Request body (for POST)

        Returns:
            Response data as dict

        Raises:
            ConnectionError: If cannot connect to Revit
            RevitAPIError: If API returns an error
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
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
            with urllib_request.urlopen(req, timeout=self.timeout) as response:
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
            raise RevitAPIError(
                f"HTTP {e.code}: {error_data.get('error', 'Unknown error')}",
                status_code=e.code,
                response=error_data,
            )

        except URLError as e:
            logger.error("Cannot connect to Revit at %s: %s", url, e.reason)
            raise ConnectionError(
                f"Cannot connect to Revit at {url}. "
                f"Make sure Revit is running with the VibeBuilding extension. "
                f"Error: {e.reason}"
            )

    def _get(self, path: str) -> Dict[str, Any]:
        return self._request("GET", path)

    def _post(self, path: str, data: Dict) -> Dict[str, Any]:
        return self._request("POST", path, data)

    def _delete(self, path: str) -> Dict[str, Any]:
        return self._request("DELETE", path)

    # -------------------------------------------------------------------------
    # Health & Info
    # -------------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Check if Revit is running and accessible.

        Returns:
            Health status dict with Revit version info
        """
        return self._get("/health")

    def is_connected(self) -> bool:
        """Check if connected to Revit.

        Returns:
            True if connected, False otherwise
        """
        try:
            result = self.health()
            return result.get("status") == "ok"
        except (ConnectionError, RevitAPIError):
            return False

    def get_model_info(self) -> ModelInfo:
        """Get information about the current Revit model.

        Returns:
            ModelInfo with document name, levels, and element counts
        """
        data = self._get("/model")

        levels = []
        for lvl in data.get("levels", []):
            levels.append(LevelInfo(
                id=lvl["id"],
                name=lvl["name"],
                elevation_mm=lvl["elevation"],
                elevation_ft=lvl["elevation"] / 304.8,
            ))

        return ModelInfo(
            document_name=data.get("document_name", ""),
            document_path=data.get("document_path", ""),
            levels=levels,
            element_counts=data.get("element_counts", {}),
        )

    def get_levels(self) -> List[LevelInfo]:
        """Get all levels in the model.

        Returns:
            List of LevelInfo objects
        """
        data = self._get("/model/levels")
        levels = []
        for lvl in data.get("levels", []):
            levels.append(LevelInfo(
                id=lvl["id"],
                name=lvl["name"],
                elevation_mm=lvl["elevation_mm"],
                elevation_ft=lvl["elevation_ft"],
            ))
        return levels

    def get_wall_types(self) -> List[Dict[str, Any]]:
        """Get available wall types.

        Returns:
            List of wall type info dicts
        """
        data = self._get("/model/wall-types")
        return data.get("wall_types", [])

    # -------------------------------------------------------------------------
    # Wall Operations
    # -------------------------------------------------------------------------

    def list_walls(self) -> List[WallInfo]:
        """List all walls in the model.

        Returns:
            List of WallInfo objects
        """
        data = self._get("/walls")
        walls = []
        for w in data.get("walls", []):
            walls.append(WallInfo(
                id=w["id"],
                wall_type=w["wall_type"],
                length_mm=w["length_mm"],
                height_mm=w.get("height_mm"),
                start=w.get("start"),
                end=w.get("end"),
                level=w.get("level"),
            ))
        return walls

    def create_wall(
        self,
        start: Dict[str, float],
        end: Dict[str, float],
        height: float = 3000,
        wall_type: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new wall.

        Args:
            start: Start point {"x": mm, "y": mm, "z": mm}
            end: End point {"x": mm, "y": mm, "z": mm}
            height: Wall height in mm (default: 3000)
            wall_type: Wall type name (optional, uses default if not specified)
            level: Level name (optional, uses first level if not specified)

        Returns:
            Created wall info dict with wall_id
        """
        data = {
            "start": start,
            "end": end,
            "height": height,
        }
        if wall_type:
            data["wall_type"] = wall_type
        if level:
            data["level"] = level

        return self._post("/walls", data)

    def delete_wall(self, wall_id: int) -> Dict[str, Any]:
        """Delete a wall by ID.

        Args:
            wall_id: The Revit element ID of the wall

        Returns:
            Deletion result dict
        """
        return self._delete(f"/walls/{wall_id}")

    # -------------------------------------------------------------------------
    # Room Operations
    # -------------------------------------------------------------------------

    def list_rooms(self) -> List[Dict[str, Any]]:
        """List all rooms in the model.

        Returns:
            List of room info dicts
        """
        data = self._get("/rooms")
        return data.get("rooms", [])


class RevitAPIError(Exception):
    """Error returned by the Revit API."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        response: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def get_client(
    host: str = "localhost",
    port: int = 48884,
) -> RevitClient:
    """Get a RevitClient instance.

    Args:
        host: Revit host address
        port: pyRevit routes server port

    Returns:
        Configured RevitClient
    """
    return RevitClient(host=host, port=port)
