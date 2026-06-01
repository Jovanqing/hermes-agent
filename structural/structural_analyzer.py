"""
Structural Analyzer - Core structural analysis and validation engine

Performs structural checks and validation:
- Span limits for beams and slabs
- Load calculations (dead, live, wind, seismic)
- Deflection limits
- Column load checks
- Opening checks in load-bearing walls
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math


class ElementType(Enum):
    """Structural element types"""
    BEAM = "beam"
    COLUMN = "column"
    SLAB = "slab"
    WALL = "wall"
    FOUNDATION = "foundation"


class LoadType(Enum):
    """Load types"""
    DEAD = "dead"
    LIVE = "live"
    WIND = "wind"
    SEISMIC = "seismic"
    SNOW = "snow"


class CheckSeverity(Enum):
    """Check severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class StructuralElement:
    """Represents a structural element"""
    id: str
    element_type: ElementType
    length: float = 0.0  # meters
    width: float = 0.0  # meters
    height: float = 0.0  # meters
    depth: float = 0.0  # meters (for beams/slabs)
    area: float = 0.0  # sqm
    volume: float = 0.0  # cubic meters
    material: str = "concrete"
    level: str = ""
    loads: Dict[str, float] = field(default_factory=dict)  # kN or kN/m
    supports: List[str] = field(default_factory=list)  # IDs of supporting elements
    supported_by: List[str] = field(default_factory=list)  # IDs of elements this supports

    # Calculated properties
    span: float = 0.0  # meters (for beams/slabs)
    load_ratio: float = 0.0  # actual / capacity
    deflection: float = 0.0  # meters
    deflection_ratio: float = 0.0  # deflection / span


@dataclass
class StructuralCheck:
    """Result of a structural check"""
    element_id: str
    check_name: str
    severity: CheckSeverity
    message: str
    value: Optional[float] = None
    limit: Optional[float] = None
    unit: str = ""
    suggestion: str = ""


@dataclass
class StructuralReport:
    """Complete structural analysis report"""
    elements: List[StructuralElement] = field(default_factory=list)
    checks: List[StructuralCheck] = field(default_factory=list)
    score: float = 100.0  # 0-100, higher is better

    def add_check(self, check: StructuralCheck):
        """Add a check result"""
        self.checks.append(check)
        # Deduct points based on severity
        if check.severity == CheckSeverity.ERROR:
            self.score -= 10
        elif check.severity == CheckSeverity.WARNING:
            self.score -= 5
        elif check.severity == CheckSeverity.INFO:
            self.score -= 1
        self.score = max(0, self.score)

    def get_summary(self) -> Dict[str, int]:
        """Get summary of checks by severity"""
        summary = {"error": 0, "warning": 0, "info": 0}
        for check in self.checks:
            summary[check.severity.value] += 1
        return summary

    def is_valid(self) -> bool:
        """Check if structure is valid (no errors)"""
        return self.get_summary()["error"] == 0


class StructuralAnalyzer:
    """Main structural analysis engine"""

    # Span limits (meters) - based on GB 50010-2010
    MAX_BEAM_SPAN = 8.0  # Simply supported
    MAX_BEAM_SPAN_CONTINUOUS = 10.0  # Continuous
    MAX_BEAM_CANTILEVER = 3.0
    MAX_SLAB_SPAN_ONE_WAY = 4.0
    MAX_SLAB_SPAN_TWO_WAY = 6.0
    MAX_SLAB_CANTILEVER = 2.0

    # Minimum sizes (mm)
    MIN_BEAM_DEPTH_RATIO = 1.0 / 12.0  # depth/span
    MIN_BEAM_WIDTH = 200  # mm
    MIN_COLUMN_SIZE = 300  # mm
    MIN_SLAB_THICKNESS = 100  # mm
    MIN_SLAB_THICKNESS_CANTILEVER = 150  # mm

    # Deflection limits (span ratio)
    MAX_DEFLECTION_BEAM = 1.0 / 250.0  # L/250
    MAX_DEFLECTION_SLAB = 1.0 / 250.0
    MAX_DEFLECTION_CANTILEVER = 1.0 / 100.0  # L/100

    # Load limits (kN/m²) - based on GB 50009-2012
    LIVE_LOADS = {
        "residential": 2.0,
        "office": 2.0,
        "commercial": 3.5,
        "library": 2.5,
        "gym": 4.0,
        "assembly": 3.5,
        "storage": 5.0,
    }

    # Column load capacity (kN) - simplified
    COLUMN_CAPACITIES = {
        "300x300": 2000,
        "350x350": 2500,
        "400x400": 3500,
        "450x450": 4500,
        "500x500": 5500,
    }

    # Wall opening limits
    MAX_OPENING_WIDTH = 1.5  # meters (for load-bearing walls)
    MAX_OPENING_RATIO = 0.5  # opening width / wall length

    def __init__(self):
        self.report = StructuralReport()

    def analyze(self, elements: List[StructuralElement]) -> StructuralReport:
        """
        Analyze structural elements and generate report

        Args:
            elements: List of structural elements

        Returns:
            StructuralReport with all checks
        """
        self.report = StructuralReport(elements=elements)

        # Run all checks
        self._check_beam_spans(elements)
        self._check_beam_sizes(elements)
        self._check_slab_spans(elements)
        self._check_slab_thickness(elements)
        self._check_column_sizes(elements)
        self._check_column_loads(elements)
        self._check_wall_openings(elements)
        self._check_deflections(elements)

        return self.report

    def _check_beam_spans(self, elements: List[StructuralElement]):
        """Check beam span limits"""
        beams = [e for e in elements if e.element_type == ElementType.BEAM]

        for beam in beams:
            if beam.span == 0:
                continue

            # Determine if cantilever
            is_cantilever = len(beam.supports) == 1

            if is_cantilever:
                max_span = self.MAX_BEAM_CANTILEVER
                check_name = "Beam Cantilever Span"
            else:
                # Check if continuous (more than 2 supports)
                is_continuous = len(beam.supports) > 2
                max_span = self.MAX_BEAM_SPAN_CONTINUOUS if is_continuous else self.MAX_BEAM_SPAN
                check_name = "Beam Span"

            if beam.span > max_span:
                self.report.add_check(StructuralCheck(
                    element_id=beam.id,
                    check_name=check_name,
                    severity=CheckSeverity.WARNING,
                    message=f"{check_name} {beam.span:.2f}m exceeds recommended {max_span}m",
                    value=beam.span,
                    limit=max_span,
                    unit="m",
                    suggestion=f"Reduce span to {max_span}m or add intermediate support",
                ))

    def _check_beam_sizes(self, elements: List[StructuralElement]):
        """Check beam size requirements"""
        beams = [e for e in elements if e.element_type == ElementType.BEAM]

        for beam in beams:
            if beam.span == 0:
                continue

            # Check depth/span ratio
            min_depth = beam.span * self.MIN_BEAM_DEPTH_RATIO
            actual_depth = beam.depth / 1000.0  # Convert mm to m

            if actual_depth < min_depth:
                self.report.add_check(StructuralCheck(
                    element_id=beam.id,
                    check_name="Beam Depth",
                    severity=CheckSeverity.WARNING,
                    message=f"Beam depth {actual_depth:.2f}m below minimum {min_depth:.2f}m (L/12)",
                    value=actual_depth,
                    limit=min_depth,
                    unit="m",
                    suggestion=f"Increase beam depth to at least {min_depth:.2f}m",
                ))

            # Check minimum width
            if beam.width < self.MIN_BEAM_WIDTH:
                self.report.add_check(StructuralCheck(
                    element_id=beam.id,
                    check_name="Beam Width",
                    severity=CheckSeverity.WARNING,
                    message=f"Beam width {beam.width}mm below minimum {self.MIN_BEAM_WIDTH}mm",
                    value=beam.width,
                    limit=self.MIN_BEAM_WIDTH,
                    unit="mm",
                    suggestion=f"Increase beam width to at least {self.MIN_BEAM_WIDTH}mm",
                ))

    def _check_slab_spans(self, elements: List[StructuralElement]):
        """Check slab span limits"""
        slabs = [e for e in elements if e.element_type == ElementType.SLAB]

        for slab in slabs:
            if slab.span == 0:
                continue

            # Determine if one-way or two-way
            is_one_way = slab.length / slab.width > 2 if slab.width > 0 else True
            max_span = self.MAX_SLAB_SPAN_ONE_WAY if is_one_way else self.MAX_SLAB_SPAN_TWO_WAY

            if slab.span > max_span:
                self.report.add_check(StructuralCheck(
                    element_id=slab.id,
                    check_name="Slab Span",
                    severity=CheckSeverity.WARNING,
                    message=f"Slab span {slab.span:.2f}m exceeds recommended {max_span}m",
                    value=slab.span,
                    limit=max_span,
                    unit="m",
                    suggestion=f"Reduce span to {max_span}m or add beams",
                ))

    def _check_slab_thickness(self, elements: List[StructuralElement]):
        """Check slab thickness requirements"""
        slabs = [e for e in elements if e.element_type == ElementType.SLAB]

        for slab in slabs:
            if slab.depth == 0:
                continue

            # Determine minimum thickness
            is_cantilever = len(slab.supports) == 1
            min_thickness = self.MIN_SLAB_THICKNESS_CANTILEVER if is_cantilever else self.MIN_SLAB_THICKNESS

            if slab.depth < min_thickness:
                self.report.add_check(StructuralCheck(
                    element_id=slab.id,
                    check_name="Slab Thickness",
                    severity=CheckSeverity.WARNING,
                    message=f"Slab thickness {slab.depth}mm below minimum {min_thickness}mm",
                    value=slab.depth,
                    limit=min_thickness,
                    unit="mm",
                    suggestion=f"Increase slab thickness to at least {min_thickness}mm",
                ))

    def _check_column_sizes(self, elements: List[StructuralElement]):
        """Check column size requirements"""
        columns = [e for e in elements if e.element_type == ElementType.COLUMN]

        for column in columns:
            if column.width == 0 or column.depth == 0:
                continue

            min_size = self.MIN_COLUMN_SIZE

            if column.width < min_size or column.depth < min_size:
                self.report.add_check(StructuralCheck(
                    element_id=column.id,
                    check_name="Column Size",
                    severity=CheckSeverity.WARNING,
                    message=f"Column size {column.width}x{column.depth}mm below minimum {min_size}x{min_size}mm",
                    value=min(column.width, column.depth),
                    limit=min_size,
                    unit="mm",
                    suggestion=f"Increase column size to at least {min_size}x{min_size}mm",
                ))

    def _check_column_loads(self, elements: List[StructuralElement]):
        """Check column load capacity"""
        columns = [e for e in elements if e.element_type == ElementType.COLUMN]

        for column in columns:
            # Get total load on column
            total_load = sum(column.loads.values())

            if total_load == 0:
                continue

            # Determine column capacity based on size
            size_key = f"{int(column.width)}x{int(column.depth)}"
            capacity = self.COLUMN_CAPACITIES.get(size_key, 2000)  # Default 2000 kN

            if total_load > capacity:
                self.report.add_check(StructuralCheck(
                    element_id=column.id,
                    check_name="Column Load",
                    severity=CheckSeverity.ERROR,
                    message=f"Column load {total_load:.0f}kN exceeds capacity {capacity}kN",
                    value=total_load,
                    limit=capacity,
                    unit="kN",
                    suggestion=f"Increase column size or reduce load",
                ))

    def _check_wall_openings(self, elements: List[StructuralElement]):
        """Check wall opening limits"""
        walls = [e for e in elements if e.element_type == ElementType.WALL]

        for wall in walls:
            if wall.length == 0:
                continue

            # Get opening width from loads dict (simplified approach)
            opening_width = wall.loads.get("opening_width", 0)

            if opening_width == 0:
                continue

            # Check absolute limit
            if opening_width > self.MAX_OPENING_WIDTH:
                self.report.add_check(StructuralCheck(
                    element_id=wall.id,
                    check_name="Wall Opening Width",
                    severity=CheckSeverity.WARNING,
                    message=f"Wall opening {opening_width:.2f}m exceeds recommended {self.MAX_OPENING_WIDTH}m",
                    value=opening_width,
                    limit=self.MAX_OPENING_WIDTH,
                    unit="m",
                    suggestion=f"Reduce opening width or add lintel beam",
                ))

            # Check ratio limit
            opening_ratio = opening_width / wall.length
            if opening_ratio > self.MAX_OPENING_RATIO:
                self.report.add_check(StructuralCheck(
                    element_id=wall.id,
                    check_name="Wall Opening Ratio",
                    severity=CheckSeverity.WARNING,
                    message=f"Wall opening ratio {opening_ratio:.1%} exceeds {self.MAX_OPENING_RATIO:.0%}",
                    value=opening_ratio,
                    limit=self.MAX_OPENING_RATIO,
                    unit="",
                    suggestion=f"Reduce opening width or increase wall length",
                ))

    def _check_deflections(self, elements: List[StructuralElement]):
        """Check deflection limits"""
        beams = [e for e in elements if e.element_type == ElementType.BEAM]
        slabs = [e for e in elements if e.element_type == ElementType.SLAB]

        for element in beams + slabs:
            if element.deflection == 0 or element.span == 0:
                continue

            # Determine if cantilever
            is_cantilever = len(element.supports) == 1
            max_deflection_ratio = self.MAX_DEFLECTION_CANTILEVER if is_cantilever else self.MAX_DEFLECTION_BEAM

            if element.deflection_ratio > max_deflection_ratio:
                self.report.add_check(StructuralCheck(
                    element_id=element.id,
                    check_name="Deflection",
                    severity=CheckSeverity.WARNING,
                    message=f"Deflection ratio {element.deflection_ratio:.1%} exceeds limit {max_deflection_ratio:.1%}",
                    value=element.deflection_ratio,
                    limit=max_deflection_ratio,
                    unit="",
                    suggestion=f"Increase element depth or add support",
                ))
