# -*- coding: utf-8 -*-
"""VibeVilla HTTP API - Endpoints for AI-driven BIM modeling.

Provides REST endpoints for creating and modifying Revit BIM elements.
Uses the existing revit_helpers.py for Revit API operations.

Example:
    POST http://localhost:48884/vibe-building/walls
    {
        "start": {"x": 0, "y": 0, "z": 0},
        "end": {"x": 5, "y": 0, "z": 0},
        "height": 3.0,
        "level": "标高 1"
    }
"""

from pyrevit import routes
from pyrevit.coreutils.logger import get_logger

# Import Revit helpers from the extension's lib
import revit_helpers

mlogger = get_logger(__name__)

# Create API instance
api = routes.API('vibe-building')


# =============================================================================
# Simple Test Endpoint
# =============================================================================

@api.route('/test-wall', methods=['POST'])
def test_create_wall(uiapp, request):
    """Simple wall creation test with detailed error reporting."""
    import traceback
    doc = uiapp.ActiveUIDocument.Document
    if not doc:
        return {"error": "No document open"}

    try:
        from Autodesk.Revit.DB import (
            Line, Wall, XYZ,
            FilteredElementCollector, WallType, Level
        )
        from pyrevit import revit

        data = request.data or {}
        x1 = data.get("x1", 30)
        x2 = data.get("x2", 35)
        height_m = data.get("height", 3.0)

        # Create points (convert meters to feet)
        ft = 1.0 / 0.3048
        p1 = XYZ(x1 * ft, 0, 0)
        p2 = XYZ(x2 * ft, 0, 0)

        # Get first level
        levels = list(FilteredElementCollector(doc).OfClass(Level))
        if not levels:
            return {"error": "No levels in model"}
        level = levels[0]

        # Get first wall type
        wall_types = list(FilteredElementCollector(doc).OfClass(WallType))
        if not wall_types:
            return {"error": "No wall types in model"}
        wall_type = wall_types[0]

        # Create line and wall
        line = Line.CreateBound(p1, p2)
        height_ft = height_m * ft

        with revit.Transaction("Test Wall"):
            wall = Wall.Create(doc, line, wall_type.Id, level.Id, height_ft, 0, False, True)
            doc.Regenerate()

            return {
                "success": True,
                "wall_id": wall.Id.IntegerValue,
                "wall_type_id": wall_type.Id.IntegerValue,
                "level_id": level.Id.IntegerValue,
                "length_m": x2 - x1,
                "height_m": height_m,
            }

    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# =============================================================================
# Health & Info
# =============================================================================

@api.route('/health', methods=['GET'])
def health_check(uiapp):
    """Health check - verify connection to Revit."""
    try:
        doc = uiapp.ActiveUIDocument.Document if uiapp.ActiveUIDocument else None
        return {
            "status": "ok",
            "revit_version": uiapp.Application.VersionNumber,
            "document_open": doc is not None,
            "document_name": doc.Title if doc else None,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@api.route('/model/levels', methods=['GET'])
def get_levels(uiapp):
    """Get all levels in the model."""
    doc = uiapp.ActiveUIDocument.Document
    if not doc:
        return {"error": "No document open"}

    try:
        from Autodesk.Revit.DB import FilteredElementCollector, Level
        levels = []
        for lv in FilteredElementCollector(doc).OfClass(Level):
            levels.append({
                "id": lv.Id.IntegerValue,
                "name": lv.Name,
                "elevation_m": round(lv.Elevation / revit_helpers.FT_PER_M, 3),
            })
        return {"levels": sorted(levels, key=lambda x: x["elevation_m"])}
    except Exception as e:
        return {"error": str(e)}


@api.route('/wall-types', methods=['GET'])
def get_wall_types(uiapp):
    """Get available wall types."""
    doc = uiapp.ActiveUIDocument.Document
    if not doc:
        return {"error": "No document open"}

    try:
        from Autodesk.Revit.DB import FilteredElementCollector, WallType
        types = []
        for wt in FilteredElementCollector(doc).OfClass(WallType):
            type_info = {"id": wt.Id.IntegerValue}
            try:
                type_info["name"] = wt.Name
            except:
                type_info["name"] = "Type {}".format(wt.Id.IntegerValue)
            try:
                type_info["width_m"] = round(wt.Width / revit_helpers.FT_PER_M, 3)
            except:
                pass
            types.append(type_info)
        return {"wall_types": types, "count": len(types)}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Wall Operations
# =============================================================================

@api.route('/walls', methods=['GET'])
def list_walls(uiapp):
    """List all walls in the model."""
    doc = uiapp.ActiveUIDocument.Document
    if not doc:
        return {"error": "No document open"}

    try:
        from Autodesk.Revit.DB import FilteredElementCollector, Wall, LocationCurve
        walls = []
        for wall in FilteredElementCollector(doc).OfClass(Wall):
            info = {
                "id": wall.Id.IntegerValue,
            }
            # Get wall type name safely
            try:
                if wall.WallType:
                    info["type"] = wall.WallType.Name
            except:
                info["type"] = "Unknown"

            # Get geometry if available
            loc = wall.Location
            if isinstance(loc, LocationCurve):
                curve = loc.Curve
                p1 = curve.GetEndPoint(0)
                p2 = curve.GetEndPoint(1)
                info["start"] = {
                    "x": round(p1.X / revit_helpers.FT_PER_M, 3),
                    "y": round(p1.Y / revit_helpers.FT_PER_M, 3),
                    "z": round(p1.Z / revit_helpers.FT_PER_M, 3),
                }
                info["end"] = {
                    "x": round(p2.X / revit_helpers.FT_PER_M, 3),
                    "y": round(p2.Y / revit_helpers.FT_PER_M, 3),
                    "z": round(p2.Z / revit_helpers.FT_PER_M, 3),
                }
                info["length_m"] = round(curve.Length / revit_helpers.FT_PER_M, 3)
            walls.append(info)
        return {"walls": walls, "count": len(walls)}
    except Exception as e:
        mlogger.error("List walls failed: {}".format(str(e)))
        return {"error": str(e)}


@api.route('/walls', methods=['POST'])
def create_wall(uiapp, request):
    """Create a new wall.

    Request body (coordinates in meters):
    {
        "start": {"x": 0, "y": 0, "z": 0},
        "end": {"x": 5, "y": 0, "z": 0},
        "height": 3.0,
        "level": "标高 1",
        "wall_type": "Generic - 200mm"
    }
    """
    doc = uiapp.ActiveUIDocument.Document
    if not doc:
        return {"error": "No document open"}

    data = request.data
    if not data:
        return {"error": "No request data"}

    try:
        from Autodesk.Revit.DB import (
            Transaction, Line, Wall, XYZ,
            FilteredElementCollector, WallType, Level
        )

        # Parse coordinates (in meters, with defaults for missing keys)
        start = data.get("start", {})
        end = data.get("end", {})
        height_m = data.get("height", 3.0)
        level_name = data.get("level")
        wall_type_name = data.get("wall_type")

        # Convert to Revit points (meters to feet)
        p1 = revit_helpers.pt(
            start.get("x", 0),
            start.get("y", 0),
            start.get("z", 0)
        )
        p2 = revit_helpers.pt(
            end.get("x", 5),
            end.get("y", 0),
            end.get("z", 0)
        )

        # Find or create level
        level = None
        if level_name:
            for lv in FilteredElementCollector(doc).OfClass(Level):
                if lv.Name == level_name:
                    level = lv
                    break
        if not level:
            # Use first level
            level = list(FilteredElementCollector(doc).OfClass(Level))[0]

        # Find wall type
        wall_type = None
        if wall_type_name:
            wall_type = revit_helpers.find_wall_type(doc, name_contains=wall_type_name)

        if not wall_type:
            # Get first available wall type
            wall_types = list(FilteredElementCollector(doc).OfClass(WallType))
            if wall_types:
                wall_type = wall_types[0]
            else:
                return {"error": "No wall types available in model"}

        # Create wall
        line = Line.CreateBound(p1, p2)
        height_ft = revit_helpers.m_to_ft(height_m)

        from pyrevit import revit
        with revit.Transaction("Create Wall via VibeBuilding API"):
            wall = Wall.Create(doc, line, wall_type.Id, level.Id, height_ft, 0, False, True)

            # Safely get names
            try:
                wt_name = wall_type.Name
            except:
                wt_name = "Type {}".format(wall_type.Id.IntegerValue)
            try:
                lv_name = level.Name
            except:
                lv_name = "Level {}".format(level.Id.IntegerValue)

            result = {
                "success": True,
                "wall_id": wall.Id.IntegerValue,
                "wall_type": wt_name,
                "level": lv_name,
                "length_m": round(line.Length / revit_helpers.FT_PER_M, 3),
                "height_m": height_m,
            }
            mlogger.info("Created wall: {}".format(result))
            return result

    except Exception as e:
        mlogger.error("Create wall failed: {}".format(str(e)))
        return {"error": str(e)}


# =============================================================================
# Room Operations
# =============================================================================

@api.route('/room', methods=['POST'])
def create_room_walls(uiapp, request):
    """Create a room by building its four walls.

    Request body (coordinates in meters):
    {
        "name": "客厅",
        "x1": 0, "z1": 0,
        "x2": 7, "z2": 5.5,
        "level": "标高 1",
        "height": 3.0
    }
    """
    doc = uiapp.ActiveUIDocument.Document
    if not doc:
        return {"error": "No document open"}

    data = request.data
    if not data:
        return {"error": "No request data"}

    try:
        from Autodesk.Revit.DB import (
            Transaction, Line, Wall, XYZ,
            FilteredElementCollector, WallType, Level
        )

        name = data.get("name", "Room")
        x1, z1 = data.get("x1", 0), data.get("z1", 0)
        x2, z2 = data.get("x2", 5), data.get("z2", 5)
        height_m = data.get("height", 3.0)
        level_name = data.get("level", "标高 1")

        # Find level
        level = None
        level_elev = 0
        for lv in FilteredElementCollector(doc).OfClass(Level):
            if lv.Name == level_name:
                level = lv
                level_elev = lv.Elevation / revit_helpers.FT_PER_M
                break
        if not level:
            level = list(FilteredElementCollector(doc).OfClass(Level))[0]
            level_elev = level.Elevation / revit_helpers.FT_PER_M

        # Find wall type
        wall_type = revit_helpers.find_wall_type(doc)

        # Define four corners
        y = level_elev
        corners = [
            (x1, z1), (x2, z1),  # South wall
            (x2, z1), (x2, z2),  # East wall
            (x2, z2), (x1, z2),  # North wall
            (x1, z2), (x1, z1),  # West wall
        ]

        height_ft = revit_helpers.m_to_ft(height_m)
        wall_ids = []

        from pyrevit import revit
        with revit.Transaction("Create Room: {}".format(name)):
            for i in range(0, len(corners), 2):
                p1_data, p2_data = corners[i], corners[i+1]
                p1 = revit_helpers.pt(p1_data[0], p1_data[1], y)
                p2 = revit_helpers.pt(p2_data[0], p2_data[1], y)
                line = Line.CreateBound(p1, p2)
                wall = Wall.Create(doc, line, wall_type.Id, level.Id, height_ft, 0, False, True)
                wall_ids.append(wall.Id.IntegerValue)

            result = {
                "success": True,
                "room_name": name,
                "wall_ids": wall_ids,
                "dimensions_m": {"width": x2 - x1, "depth": z2 - z1},
                "area_m2": round((x2 - x1) * (z2 - z1), 2),
                "level": level.Name,
            }
            mlogger.info("Created room: {}".format(result))
            return result

    except Exception as e:
        mlogger.error("Create room failed: {}".format(str(e)))
        return {"error": str(e)}


# =============================================================================
# Batch Operations
# =============================================================================

@api.route('/build/floor', methods=['POST'])
def build_floor_layout(uiapp, request):
    """Build all rooms for a floor from a layout definition.

    Request body:
    {
        "floor_name": "一层",
        "level": "标高 1",
        "rooms": [
            {"name": "客厅", "x1": 0, "z1": 0, "x2": 7, "z2": 5.5},
            ...
        ]
    }
    """
    doc = uiapp.ActiveUIDocument.Document
    if not doc:
        return {"error": "No document open"}

    data = request.data
    if not data:
        return {"error": "No request data"}

    rooms = data.get("rooms", [])
    level_name = data.get("level", "标高 1")
    floor_name = data.get("floor_name", "Floor")

    results = []
    for room in rooms:
        room["level"] = level_name
        # Create a mock request
        class MockRequest:
            def __init__(self, data):
                self.data = data

        result = create_room_walls(uiapp, MockRequest(room))
        results.append({"room": room.get("name"), "result": result})

    return {
        "floor_name": floor_name,
        "rooms_created": len([r for r in results if r["result"].get("success")]),
        "rooms_failed": len([r for r in results if not r["result"].get("success")]),
        "details": results,
    }
