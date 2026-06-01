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
        self.commercial = CommercialBuildingValidator()
        self.office = OfficeBuildingValidator()
        self.healthcare = HealthcareBuildingValidator()

    def validate(self, model_data: Dict, building_type: str = "residential") -> ValidationResult:
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
            building_type: Type of building (residential, commercial, office, healthcare)

        Returns:
            ValidationResult with issues and score
        """
        result = ValidationResult()

        # Run common validators
        self.building_code.validate(model_data, result)
        self.structural.validate(model_data, result)
        self.patterns.validate(model_data, result)
        self.optimization.validate(model_data, result)

        # Run building type specific validators
        if building_type == "commercial":
            self.commercial.validate(model_data, result)
        elif building_type == "office":
            self.office.validate(model_data, result)
        elif building_type == "healthcare":
            self.healthcare.validate(model_data, result)

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

        # Validate ceiling heights (calculate from level elevations)
        levels = model_data.get("levels", [])
        self._validate_ceiling_heights(levels, result)

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

    def _validate_ceiling_heights(self, levels: List[Dict], result: ValidationResult):
        """Validate ceiling heights by calculating from level elevations"""
        if len(levels) < 2:
            return

        # Sort levels by elevation
        sorted_levels = sorted(levels, key=lambda x: x.get("elevation_m", 0))

        # Calculate ceiling height for each level (except the top one)
        for i in range(len(sorted_levels) - 1):
            current_level = sorted_levels[i]
            next_level = sorted_levels[i + 1]

            current_elev = current_level.get("elevation_m", 0)
            next_elev = next_level.get("elevation_m", 0)
            ceiling_height = next_elev - current_elev

            level_id = current_level.get("id", "")
            level_name = current_level.get("name", f"Level {i+1}")

            # Skip basement levels (negative elevation)
            if current_elev < 0:
                continue

            if ceiling_height < self.MIN_CEILING_HEIGHT:
                result.add_issue(ValidationIssue(
                    category="Building Code",
                    severity=Severity.ERROR,
                    message=f"{level_name} ceiling height {ceiling_height:.2f}m below minimum {self.MIN_CEILING_HEIGHT}m",
                    suggestion=f"Increase ceiling height to at least {self.MIN_CEILING_HEIGHT}m",
                    element_id=level_id,
                    value=ceiling_height,
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


class CommercialBuildingValidator:
    """Validates commercial buildings (retail, malls, restaurants)"""

    # Minimum ceiling heights by area type (GB 50352-2019)
    MIN_CEILING_HEIGHTS = {
        "retail": 4.5,
        "supermarket": 4.2,
        "restaurant": 3.6,
        "back_of_house": 2.8,
    }

    # Minimum corridor widths
    MIN_CORRIDOR_WIDTHS = {
        "main_aisle": 2.5,
        "secondary_aisle": 1.8,
        "exit_corridor": 1.4,
    }

    def validate(self, model_data: Dict, result: ValidationResult):
        """Validate commercial building design"""
        rooms = model_data.get("rooms", [])

        # Validate ceiling heights
        for room in rooms:
            room_type = room.get("type", "").lower()
            ceiling_height = room.get("height", 0)

            # Map room types to commercial categories
            commercial_type = None
            if any(keyword in room_type for keyword in ["shop", "retail", "store"]):
                commercial_type = "retail"
            elif "supermarket" in room_type:
                commercial_type = "supermarket"
            elif any(keyword in room_type for keyword in ["restaurant", "cafe", "dining"]):
                commercial_type = "restaurant"
            elif any(keyword in room_type for keyword in ["storage", "kitchen", "back"]):
                commercial_type = "back_of_house"

            if commercial_type and commercial_type in self.MIN_CEILING_HEIGHTS:
                min_height = self.MIN_CEILING_HEIGHTS[commercial_type]
                if ceiling_height < min_height:
                    result.add_issue(ValidationIssue(
                        category="Commercial Code",
                        severity=Severity.ERROR,
                        message=f"{room.get('name', room_type)} ceiling height {ceiling_height:.2f}m below minimum {min_height}m",
                        suggestion=f"Increase ceiling height to at least {min_height}m",
                        element_id=room.get("id", ""),
                        value=ceiling_height,
                        limit=min_height,
                    ))

        # Validate egress width (simplified check)
        doors = model_data.get("doors", [])
        for door in doors:
            if door.get("is_exit", False):
                width = door.get("width", 0)
                if width < 1.4:
                    result.add_issue(ValidationIssue(
                        category="Fire Safety",
                        severity=Severity.ERROR,
                        message=f"Exit door width {width:.2f}m below minimum 1.4m",
                        suggestion="Increase exit door width to at least 1.4m",
                        element_id=door.get("id", ""),
                        value=width,
                        limit=1.4,
                    ))


class OfficeBuildingValidator:
    """Validates office buildings (offices, corporate, co-working)"""

    # Minimum ceiling heights (GB 50352-2019)
    MIN_CEILING_HEIGHT = 2.7  # Net height for offices

    # Area per person requirements
    MIN_AREA_PER_PERSON = 4.0  # sqm

    # Meeting room ratios
    MEETING_ROOM_RATIO = 0.1  # 10% of office area

    def validate(self, model_data: Dict, result: ValidationResult):
        """Validate office building design"""
        rooms = model_data.get("rooms", [])

        office_area = 0
        meeting_area = 0
        person_count = 0

        for room in rooms:
            room_type = room.get("type", "").lower()
            area = room.get("area", 0)
            ceiling_height = room.get("height", 0)

            # Validate office ceiling heights
            if any(keyword in room_type for keyword in ["office", "workspace", "desk"]):
                office_area += area
                person_count += room.get("person_count", 0)

                if ceiling_height < self.MIN_CEILING_HEIGHT:
                    result.add_issue(ValidationIssue(
                        category="Office Code",
                        severity=Severity.ERROR,
                        message=f"{room.get('name', room_type)} ceiling height {ceiling_height:.2f}m below minimum {self.MIN_CEILING_HEIGHT}m",
                        suggestion=f"Increase ceiling height to at least {self.MIN_CEILING_HEIGHT}m",
                        element_id=room.get("id", ""),
                        value=ceiling_height,
                        limit=self.MIN_CEILING_HEIGHT,
                    ))

            # Accumulate meeting room area
            elif any(keyword in room_type for keyword in ["meeting", "conference"]):
                meeting_area += area

        # Validate area per person
        if person_count > 0 and office_area > 0:
            area_per_person = office_area / person_count
            if area_per_person < self.MIN_AREA_PER_PERSON:
                result.add_issue(ValidationIssue(
                    category="Office Code",
                    severity=Severity.WARNING,
                    message=f"Office area per person {area_per_person:.2f}sqm below recommended {self.MIN_AREA_PER_PERSON}sqm",
                    suggestion="Increase office area or reduce person count",
                    value=area_per_person,
                    limit=self.MIN_AREA_PER_PERSON,
                ))

        # Validate meeting room ratio
        if office_area > 0:
            meeting_ratio = meeting_area / office_area
            if meeting_ratio < self.MEETING_ROOM_RATIO:
                result.add_issue(ValidationIssue(
                    category="Office Design",
                    severity=Severity.INFO,
                    message=f"Meeting room ratio {meeting_ratio:.1%} below recommended {self.MEETING_ROOM_RATIO:.0%}",
                    suggestion=f"Increase meeting room area to at least {office_area * self.MEETING_ROOM_RATIO:.1f}sqm",
                    value=meeting_ratio,
                    limit=self.MEETING_ROOM_RATIO,
                ))


class HealthcareBuildingValidator:
    """Validates healthcare buildings (hospitals, clinics, medical facilities)"""

    # Minimum ceiling heights (GB 51039-2014)
    MIN_CEILING_HEIGHTS = {
        "outpatient": 3.6,
        "inpatient": 3.3,
        "surgery": 3.0,
        "medical_tech": 3.6,
        "admin": 3.0,
    }

    # Corridor widths
    MIN_CORRIDOR_WIDTHS = {
        "patient_corridor": 2.4,
        "bed_movement": 2.4,
        "service_corridor": 1.8,
    }

    # Room area requirements
    MIN_ROOM_AREAS = {
        "single_patient": 20.0,
        "double_patient": 25.0,
        "triple_patient": 30.0,
        "operating_room": 37.0,
        "icu": 15.0,
    }

    def validate(self, model_data: Dict, result: ValidationResult):
        """Validate healthcare building design"""
        rooms = model_data.get("rooms", [])

        for room in rooms:
            room_type = room.get("type", "").lower()
            area = room.get("area", 0)
            ceiling_height = room.get("height", 0)

            # Map room types to healthcare categories
            healthcare_type = None
            if any(keyword in room_type for keyword in ["outpatient", "clinic", "consultation"]):
                healthcare_type = "outpatient"
            elif any(keyword in room_type for keyword in ["ward", "inpatient", "patient_room"]):
                healthcare_type = "inpatient"
            elif any(keyword in room_type for keyword in ["operating", "surgery", "or"]):
                healthcare_type = "surgery"
            elif any(keyword in room_type for keyword in ["lab", "imaging", "radiology"]):
                healthcare_type = "medical_tech"
            elif any(keyword in room_type for keyword in ["admin", "office"]):
                healthcare_type = "admin"

            # Validate ceiling heights
            if healthcare_type and healthcare_type in self.MIN_CEILING_HEIGHTS:
                min_height = self.MIN_CEILING_HEIGHTS[healthcare_type]
                if ceiling_height < min_height:
                    result.add_issue(ValidationIssue(
                        category="Healthcare Code",
                        severity=Severity.ERROR,
                        message=f"{room.get('name', room_type)} ceiling height {ceiling_height:.2f}m below minimum {min_height}m",
                        suggestion=f"Increase ceiling height to at least {min_height}m",
                        element_id=room.get("id", ""),
                        value=ceiling_height,
                        limit=min_height,
                    ))

            # Validate room areas
            if "single" in room_type and "patient" in room_type:
                min_area = self.MIN_ROOM_AREAS["single_patient"]
            elif "double" in room_type and "patient" in room_type:
                min_area = self.MIN_ROOM_AREAS["double_patient"]
            elif "triple" in room_type and "patient" in room_type:
                min_area = self.MIN_ROOM_AREAS["triple_patient"]
            elif any(keyword in room_type for keyword in ["operating", "surgery"]):
                min_area = self.MIN_ROOM_AREAS["operating_room"]
            elif "icu" in room_type:
                min_area = self.MIN_ROOM_AREAS["icu"]
            else:
                min_area = None

            if min_area and area < min_area:
                result.add_issue(ValidationIssue(
                    category="Healthcare Code",
                    severity=Severity.ERROR,
                    message=f"{room.get('name', room_type)} area {area:.1f}sqm below minimum {min_area}sqm",
                    suggestion=f"Increase room area to at least {min_area}sqm",
                    element_id=room.get("id", ""),
                    value=area,
                    limit=min_area,
                ))

        # Validate patient corridors (simplified)
        corridors = [r for r in rooms if "corridor" in r.get("type", "").lower()]
        for corridor in corridors:
            if "patient" in corridor.get("type", "").lower():
                width = corridor.get("width", 0)
                min_width = self.MIN_CORRIDOR_WIDTHS["patient_corridor"]
                if width < min_width:
                    result.add_issue(ValidationIssue(
                        category="Healthcare Code",
                        severity=Severity.ERROR,
                        message=f"Patient corridor width {width:.2f}m below minimum {min_width}m",
                        suggestion="Increase corridor width to at least 2.4m for bed movement",
                        element_id=corridor.get("id", ""),
                        value=width,
                        limit=min_width,
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
        if isinstance(walls_data, list):
            model_data["walls"] = walls_data
        elif isinstance(walls_data, dict):
            model_data["walls"] = walls_data.get("walls", [])
    except Exception:
        # Revit API not available or failed
        pass

    try:
        # Get levels
        levels_data = revit_api.get_levels()
        if isinstance(levels_data, list):
            model_data["levels"] = levels_data
        elif isinstance(levels_data, dict):
            model_data["levels"] = levels_data.get("levels", [])
    except Exception:
        pass

    try:
        # Get rooms (if available)
        if hasattr(revit_api, 'list_rooms'):
            rooms_data = revit_api.list_rooms()
            if isinstance(rooms_data, list):
                model_data["rooms"] = rooms_data
            elif isinstance(rooms_data, dict):
                model_data["rooms"] = rooms_data.get("rooms", [])
    except Exception:
        pass

    try:
        # Get doors (if available)
        if hasattr(revit_api, 'list_doors'):
            doors_data = revit_api.list_doors()
            if isinstance(doors_data, list):
                model_data["doors"] = doors_data
            elif isinstance(doors_data, dict):
                model_data["doors"] = doors_data.get("doors", [])
    except Exception:
        pass

    try:
        # Get windows (if available)
        if hasattr(revit_api, 'list_windows'):
            windows_data = revit_api.list_windows()
            if isinstance(windows_data, list):
                model_data["windows"] = windows_data
            elif isinstance(windows_data, dict):
                model_data["windows"] = windows_data.get("windows", [])
    except Exception:
        pass

    try:
        # Get floors (if available)
        if hasattr(revit_api, 'list_floors'):
            floors_data = revit_api.list_floors()
            if isinstance(floors_data, list):
                model_data["floors"] = floors_data
            elif isinstance(floors_data, dict):
                model_data["floors"] = floors_data.get("floors", [])
    except Exception:
        pass

    # Calculate gross area from rooms
    if model_data["rooms"]:
        total_area = sum(room.get("area", 0) for room in model_data["rooms"])
        model_data["gross_area"] = total_area

    return model_data
