"""
Design Validation Engine for Vibe Building

Validates architectural designs against:
- Building codes (GB 50096, GB 50016, IBC)
- Structural requirements
- Design patterns
- Optimization criteria

Returns validation report with issues and suggestions.
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    category: str
    severity: Severity
    message: str
    suggestion: str = ""
    element_id: str = ""
    value: Any = None
    limit: Any = None


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 100.0  # 0-100, higher is better

    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue)
        # Deduct points based on severity
        if issue.severity == Severity.ERROR:
            self.score -= 10
        elif issue.severity == Severity.WARNING:
            self.score -= 5
        elif issue.severity == Severity.INFO:
            self.score -= 1
        self.score = max(0, self.score)

    def get_summary(self) -> Dict[str, int]:
        summary = {"error": 0, "warning": 0, "info": 0}
        for issue in self.issues:
            summary[issue.severity.value] += 1
        return summary

    def is_valid(self) -> bool:
        return self.get_summary()["error"] == 0


class DesignValidator:
    """Main validation engine"""

    def __init__(self):
        self.building_code = BuildingCodeValidator()
        self.structural = StructuralValidator()
        self.patterns = PatternValidator()
        self.optimization = OptimizationValidator()

    def validate(self, model_data: Dict) -> ValidationResult:
        """
        Validate complete design

        Args:
            model_data: Dict containing:
                - walls: List of wall dicts
                - rooms: List of room dicts
                - doors: List of door dicts
                - windows: List of window dicts
                - floors: List of floor dicts
                - levels: List of level dicts

        Returns:
            ValidationResult with issues and score
        """
        result = ValidationResult()

        # Run all validators
        self.building_code.validate(model_data, result)
        self.structural.validate(model_data, result)
        self.patterns.validate(model_data, result)
        self.optimization.validate(model_data, result)

        return result


class BuildingCodeValidator:
    """Validates against building codes (GB 50096, GB 50016, IBC)"""

    # Minimum requirements from GB 50096-2011
    MIN_ROOM_AREAS = {
        "bedroom": 9.0,  # sqm (double), 5.0 (single)
        "living": 12.0,
        "kitchen": 4.0,
        "bathroom": 2.5,
    }

    MIN_ROOM_WIDTHS = {
        "bedroom": 2.4,  # m
        "living": 3.0,
    }

    MIN_CEILING_HEIGHT = 2.4  # m (net height)
    MIN_DOOR_WIDTH = 0.9  # m
    MIN_CORRIDOR_WIDTH = 1.1  # m

    # Window-to-floor ratio
    MIN_WINDOW_RATIO = 1.0 / 7.0  # ~14.3%

    def validate(self, model_data: Dict, result: ValidationResult):
        """Validate building code compliance"""

        # Validate rooms
        for room in model_data.get("rooms", []):
            self._validate_room(room, result)

        # Validate doors
        for door in model_data.get("doors", []):
            self._validate_door(door, result)

        # Validate windows
        for window in model_data.get("windows", []):
            self._validate_window(window, model_data, result)

        # Validate ceiling heights
        for level in model_data.get("levels", []):
            self._validate_ceiling_height(level, result)

    def _validate_room(self, room: Dict, result: ValidationResult):
        """Validate room dimensions"""
        room_type = room.get("type", "").lower()
        area = room.get("area", 0)
        width = room.get("width", 0)
        room_id = room.get("id", "")

        # Check minimum area
        if room_type in self.MIN_ROOM_AREAS:
            min_area = self.MIN_ROOM_AREAS[room_type]
            if area < min_area:
                result.add_issue(ValidationIssue(
                    category="Building Code",
                    severity=Severity.ERROR,
                    message=f"{room_type.capitalize()} area {area:.1f}㎡ below minimum {min_area}㎡",
                    suggestion=f"Increase room area to at least {min_area}㎡",
                    element_id=room_id,
                    value=area,
                    limit=min_area,
                ))

        # Check minimum width
        if room_type in self.MIN_ROOM_WIDTHS:
            min_width = self.MIN_ROOM_WIDTHS[room_type]
            if width < min_width:
                result.add_issue(ValidationIssue(
                    category="Building Code",
                    severity=Severity.ERROR,
                    message=f"{room_type.capitalize()} width {width:.2f}m below minimum {min_width}m",
                    suggestion=f"Increase room width to at least {min_width}m",
                    element_id=room_id,
                    value=width,
                    limit=min_width,
                ))

    def _validate_door(self, door: Dict, result: ValidationResult):
        """Validate door width"""
        width = door.get("width", 0)
        door_id = door.get("id", "")

        if width < self.MIN_DOOR_WIDTH:
            result.add_issue(ValidationIssue(
                category="Building Code",
                severity=Severity.ERROR,
                message=f"Door width {width:.2f}m below minimum {self.MIN_DOOR_WIDTH}m",
                suggestion=f"Increase door width to at least {self.MIN_DOOR_WIDTH}m for accessibility",
                element_id=door_id,
                value=width,
                limit=self.MIN_DOOR_WIDTH,
            ))

    def _validate_window(self, window: Dict, model_data: Dict, result: ValidationResult):
        """Validate window-to-floor ratio"""
        room_id = window.get("room_id", "")
        window_area = window.get("area", 0)
        window_id = window.get("id", "")

        # Find room
        room = next((r for r in model_data.get("rooms", []) if r.get("id") == room_id), None)
        if not room:
            return

        floor_area = room.get("area", 0)
        if floor_area == 0:
            return

        ratio = window_area / floor_area

        if ratio < self.MIN_WINDOW_RATIO:
            result.add_issue(ValidationIssue(
                category="Building Code",
                severity=Severity.WARNING,
                message=f"Window-to-floor ratio {ratio:.1%} below minimum {self.MIN_WINDOW_RATIO:.1%}",
                suggestion=f"Increase window area to at least {floor_area * self.MIN_WINDOW_RATIO:.2f}㎡",
                element_id=window_id,
                value=ratio,
                limit=self.MIN_WINDOW_RATIO,
            ))

    def _validate_ceiling_height(self, level: Dict, result: ValidationResult):
        """Validate ceiling height"""
        height = level.get("height", 0)
        level_id = level.get("id", "")

        if height < self.MIN_CEILING_HEIGHT:
            result.add_issue(ValidationIssue(
                category="Building Code",
                severity=Severity.ERROR,
                message=f"Ceiling height {height:.2f}m below minimum {self.MIN_CEILING_HEIGHT}m",
                suggestion=f"Increase ceiling height to at least {self.MIN_CEILING_HEIGHT}m",
                element_id=level_id,
                value=height,
                limit=self.MIN_CEILING_HEIGHT,
            ))


class StructuralValidator:
    """Validates structural requirements"""

    # Span limits
    MAX_SLAB_SPAN = 6.0  # m (two-way slab)
    MAX_BEAM_SPAN = 8.0  # m
    MAX_CANTILEVER = 2.0  # m

    # Minimum sizes
    MIN_SLAB_THICKNESS = 100  # mm
    MIN_COLUMN_SIZE = 300  # mm
    MIN_BEAM_DEPTH_RATIO = 1.0 / 12.0  # depth/span

    def validate(self, model_data: Dict, result: ValidationResult):
        """Validate structural requirements"""

        # Validate rooms (span checks)
        for room in model_data.get("rooms", []):
            self._validate_room_spans(room, result)

        # Validate openings in load-bearing walls
        for wall in model_data.get("walls", []):
            self._validate_wall_openings(wall, model_data, result)

    def _validate_room_spans(self, room: Dict, result: ValidationResult):
        """Check if room spans exceed limits"""
        width = room.get("width", 0)
        depth = room.get("depth", 0)
        room_id = room.get("id", "")

        # Check slab span (use larger dimension)
        max_span = max(width, depth)

        if max_span > self.MAX_SLAB_SPAN:
            result.add_issue(ValidationIssue(
                category="Structural",
                severity=Severity.WARNING,
                message=f"Room span {max_span:.2f}m exceeds recommended {self.MAX_SLAB_SPAN}m",
                suggestion=f"Add intermediate beam or reduce span to {self.MAX_SLAB_SPAN}m",
                element_id=room_id,
                value=max_span,
                limit=self.MAX_SLAB_SPAN,
            ))

    def _validate_wall_openings(self, wall: Dict, model_data: Dict, result: ValidationResult):
        """Check openings in load-bearing walls"""
        wall_id = wall.get("id", "")
        wall_length = wall.get("length", 0)
        is_load_bearing = wall.get("load_bearing", False)

        if not is_load_bearing:
            return

        # Find doors/windows in this wall
        doors = [d for d in model_data.get("doors", []) if d.get("wall_id") == wall_id]
        windows = [w for w in model_data.get("windows", []) if w.get("wall_id") == wall_id]

        # Calculate total opening width
        total_opening = sum(d.get("width", 0) for d in doors)
        total_opening += sum(w.get("width", 0) for w in windows)

        # Check if opening ratio exceeds 50%
        if wall_length > 0 and total_opening / wall_length > 0.5:
            result.add_issue(ValidationIssue(
                category="Structural",
                severity=Severity.ERROR,
                message=f"Load-bearing wall openings {total_opening:.2f}m exceed 50% of wall length {wall_length:.2f}m",
                suggestion="Reduce openings or add structural support (lintel beam)",
                element_id=wall_id,
                value=total_opening / wall_length,
                limit=0.5,
            ))


class PatternValidator:
    """Validates design patterns"""

    # Circulation ratio targets
    MAX_CIRCULATION_RATIO = 0.20  # 20%
    TARGET_CIRCULATION_RATIO = 0.15  # 15%

    # Privacy checks
    PRIVATE_ROOMS = ["bedroom", "bathroom"]
    PUBLIC_ROOMS = ["living", "dining", "kitchen"]

    def validate(self, model_data: Dict, result: ValidationResult):
        """Validate design patterns"""

        # Check circulation ratio
        self._validate_circulation(model_data, result)

        # Check privacy
        self._validate_privacy(model_data, result)

        # Check cross-ventilation
        self._validate_ventilation(model_data, result)

    def _validate_circulation(self, model_data: Dict, result: ValidationResult):
        """Check circulation area ratio"""
        rooms = model_data.get("rooms", [])

        # Calculate total and circulation area
        total_area = sum(r.get("area", 0) for r in rooms)
        circulation_area = sum(r.get("area", 0) for r in rooms if r.get("type") == "corridor")

        if total_area == 0:
            return

        ratio = circulation_area / total_area

        if ratio > self.MAX_CIRCULATION_RATIO:
            result.add_issue(ValidationIssue(
                category="Design Pattern",
                severity=Severity.WARNING,
                message=f"Circulation ratio {ratio:.1%} exceeds {self.MAX_CIRCULATION_RATIO:.0%}",
                suggestion=f"Reduce corridor area or convert to multi-use spaces",
                value=ratio,
                limit=self.MAX_CIRCULATION_RATIO,
            ))
        elif ratio > self.TARGET_CIRCULATION_RATIO:
            result.add_issue(ValidationIssue(
                category="Design Pattern",
                severity=Severity.INFO,
                message=f"Circulation ratio {ratio:.1%} above target {self.TARGET_CIRCULATION_RATIO:.0%}",
                suggestion="Consider optimizing circulation for better space efficiency",
                value=ratio,
                limit=self.TARGET_CIRCULATION_RATIO,
            ))

    def _validate_privacy(self, model_data: Dict, result: ValidationResult):
        """Check privacy (bedroom visibility from public spaces)"""
        rooms = model_data.get("rooms", [])
        doors = model_data.get("doors", [])

        # Find bedroom doors
        bedroom_doors = [d for d in doors if d.get("room_type") in self.PRIVATE_ROOMS]

        # Check if any bedroom door is visible from living room
        # (simplified check - in reality would need sight line analysis)
        living_rooms = [r for r in rooms if r.get("type") == "living"]

        for bedroom_door in bedroom_doors:
            # Check if door connects directly to living room
            if bedroom_door.get("connects_to") in [r.get("id") for r in living_rooms]:
                result.add_issue(ValidationIssue(
                    category="Design Pattern",
                    severity=Severity.WARNING,
                    message="Bedroom door opens directly to living room",
                    suggestion="Add corridor or vestibule for privacy",
                    element_id=bedroom_door.get("id", ""),
                ))

    def _validate_ventilation(self, model_data: Dict, result: ValidationResult):
        """Check cross-ventilation"""
        rooms = model_data.get("rooms", [])
        windows = model_data.get("windows", [])

        for room in rooms:
            if room.get("type") in ["bathroom", "corridor", "storage"]:
                continue  # Skip non-habitable rooms

            room_id = room.get("id", "")
            room_windows = [w for w in windows if w.get("room_id") == room_id]

            # Check if windows on multiple walls
            walls_with_windows = set(w.get("wall_orientation") for w in room_windows)

            if len(walls_with_windows) < 2:
                result.add_issue(ValidationIssue(
                    category="Design Pattern",
                    severity=Severity.WARNING,
                    message=f"Room has windows on only {len(walls_with_windows)} wall(s) - poor cross-ventilation",
                    suggestion="Add windows on opposite wall for cross-ventilation",
                    element_id=room_id,
                ))


class OptimizationValidator:
    """Validates optimization criteria"""

    # Targets
    TARGET_NET_TO_GROSS = 0.80  # 80%
    TARGET_ENERGY = 50.0  # kWh/㎡·year

    # Modular grid
    MODULE_SIZE = 300  # mm

    def validate(self, model_data: Dict, result: ValidationResult):
        """Validate optimization"""

        # Check net-to-gross ratio
        self._validate_efficiency(model_data, result)

        # Check modular grid
        self._validate_modularity(model_data, result)

        # Check orientation
        self._validate_orientation(model_data, result)

    def _validate_efficiency(self, model_data: Dict, result: ValidationResult):
        """Check net-to-gross ratio"""
        gross_area = model_data.get("gross_area", 0)
        net_area = sum(r.get("area", 0) for r in model_data.get("rooms", []))

        if gross_area == 0:
            return

        ratio = net_area / gross_area

        if ratio < self.TARGET_NET_TO_GROSS:
            result.add_issue(ValidationIssue(
                category="Optimization",
                severity=Severity.INFO,
                message=f"Net-to-gross ratio {ratio:.1%} below target {self.TARGET_NET_TO_GROSS:.0%}",
                suggestion="Optimize wall thickness, structural efficiency, or reduce MEP shafts",
                value=ratio,
                limit=self.TARGET_NET_TO_GROSS,
            ))

    def _validate_modularity(self, model_data: Dict, result: ValidationResult):
        """Check if dimensions follow modular grid"""
        rooms = model_data.get("rooms", [])

        non_modular_count = 0
        for room in rooms:
            width_mm = room.get("width", 0) * 1000
            depth_mm = room.get("depth", 0) * 1000

            if width_mm % self.MODULE_SIZE != 0 or depth_mm % self.MODULE_SIZE != 0:
                non_modular_count += 1

        if non_modular_count > 0:
            result.add_issue(ValidationIssue(
                category="Optimization",
                severity=Severity.INFO,
                message=f"{non_modular_count} room(s) have non-modular dimensions",
                suggestion=f"Round dimensions to nearest {self.MODULE_SIZE}mm for standardization",
                value=non_modular_count,
            ))

    def _validate_orientation(self, model_data: Dict, result: ValidationResult):
        """Check building orientation"""
        building_orientation = model_data.get("orientation", 0)  # degrees from north

        # Optimal: long axis east-west (south-facing)
        # Acceptable: ±30° from south

        optimal = 180  # south
        deviation = abs(building_orientation - optimal)
        if deviation > 180:
            deviation = 360 - deviation

        if deviation > 45:  # More than 45° from south
            result.add_issue(ValidationIssue(
                category="Optimization",
                severity=Severity.INFO,
                message=f"Building orientation {building_orientation}° deviates {deviation}° from optimal south",
                suggestion="Rotate building to maximize south-facing facade for solar gain",
                value=deviation,
                limit=45,
            ))


# Utility function to convert Revit model to validation format
def extract_model_data(revit_api) -> Dict:
    """
    Extract model data from Revit API for validation

    Args:
        revit_api: revit_api module

    Returns:
        Dict with walls, rooms, doors, windows, floors, levels
    """
    model_data = {
        "walls": [],
        "rooms": [],
        "doors": [],
        "windows": [],
        "floors": [],
        "levels": [],
        "gross_area": 0,
        "orientation": 0,
    }

    try:
        # Get walls
        walls_data = revit_api.list_walls()
        if isinstance(walls_data, dict):
            model_data["walls"] = walls_data.get("walls", [])
    except Exception:
        # Revit API not available or failed
        pass

    try:
        # Get levels
        levels_data = revit_api.get_levels()
        if isinstance(levels_data, dict):
            model_data["levels"] = levels_data.get("levels", [])
    except Exception:
        pass

    try:
        # Get rooms (if available)
        if hasattr(revit_api, 'list_rooms'):
            rooms_data = revit_api.list_rooms()
            if isinstance(rooms_data, dict):
                model_data["rooms"] = rooms_data.get("rooms", [])
    except Exception:
        pass

    try:
        # Get doors (if available)
        if hasattr(revit_api, 'list_doors'):
            doors_data = revit_api.list_doors()
            if isinstance(doors_data, dict):
                model_data["doors"] = doors_data.get("doors", [])
    except Exception:
        pass

    try:
        # Get windows (if available)
        if hasattr(revit_api, 'list_windows'):
            windows_data = revit_api.list_windows()
            if isinstance(windows_data, dict):
                model_data["windows"] = windows_data.get("windows", [])
    except Exception:
        pass

    try:
        # Get floors (if available)
        if hasattr(revit_api, 'list_floors'):
            floors_data = revit_api.list_floors()
            if isinstance(floors_data, dict):
                model_data["floors"] = floors_data.get("floors", [])
    except Exception:
        pass

    # Calculate gross area (simplified - use first floor footprint)
    if model_data["walls"]:
        # Estimate from wall bounding box
        # In reality, would use Revit API to get floor area
        pass

    return model_data
