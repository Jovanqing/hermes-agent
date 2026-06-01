"""
Revit Structural Extractor - Extract structural elements from Revit model

Extracts:
- Structural columns
- Structural beams
- Structural slabs/floors
- Load-bearing walls
- Loads and supports
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .structural_analyzer import StructuralElement, ElementType


@dataclass
class StructuralModel:
    """Complete structural model extracted from Revit"""
    columns: List[StructuralElement] = field(default_factory=list)
    beams: List[StructuralElement] = field(default_factory=list)
    slabs: List[StructuralElement] = field(default_factory=list)
    walls: List[StructuralElement] = field(default_factory=list)
    foundations: List[StructuralElement] = field(default_factory=list)
    levels: List[Dict[str, Any]] = field(default_factory=list)

    def get_all_elements(self) -> List[StructuralElement]:
        """Get all structural elements"""
        return (
            self.columns +
            self.beams +
            self.slabs +
            self.walls +
            self.foundations
        )


class RevitStructuralExtractor:
    """Extract structural elements from Revit API"""

    def __init__(self, revit_api):
        """
        Initialize extractor

        Args:
            revit_api: Revit API module
        """
        self.revit_api = revit_api

    def extract(self) -> StructuralModel:
        """
        Extract complete structural model from Revit

        Returns:
            StructuralModel with all elements
        """
        model = StructuralModel()

        # Extract levels
        model.levels = self._extract_levels()

        # Extract structural elements
        model.columns = self._extract_columns()
        model.beams = self._extract_beams()
        model.slabs = self._extract_slabs()
        model.walls = self._extract_walls()
        model.foundations = self._extract_foundations()

        # Calculate spans and relationships
        self._calculate_spans(model)
        self._establish_supports(model)

        return model

    def _extract_levels(self) -> List[Dict[str, Any]]:
        """Extract level information"""
        try:
            levels_data = self.revit_api.get_levels()
            if isinstance(levels_data, dict):
                return levels_data.get("levels", [])
            elif isinstance(levels_data, list):
                return levels_data
        except Exception:
            pass
        return []

    def _extract_columns(self) -> List[StructuralElement]:
        """Extract structural columns"""
        columns = []

        try:
            # Try to get columns from Revit API
            if hasattr(self.revit_api, 'list_columns'):
                columns_data = self.revit_api.list_columns()
                if isinstance(columns_data, dict):
                    columns_data = columns_data.get("columns", [])
            else:
                columns_data = []

            for col_data in columns_data:
                column = StructuralElement(
                    id=col_data.get("id", ""),
                    element_type=ElementType.COLUMN,
                    width=col_data.get("width", 0) * 1000,  # m to mm
                    depth=col_data.get("depth", 0) * 1000,  # m to mm
                    height=col_data.get("height", 0),
                    material=col_data.get("material", "concrete"),
                    level=col_data.get("level", ""),
                )
                columns.append(column)

        except Exception as e:
            print(f"Warning: Could not extract columns: {e}")

        return columns

    def _extract_beams(self) -> List[StructuralElement]:
        """Extract structural beams"""
        beams = []

        try:
            # Try to get beams from Revit API
            if hasattr(self.revit_api, 'list_beams'):
                beams_data = self.revit_api.list_beams()
                if isinstance(beams_data, dict):
                    beams_data = beams_data.get("beams", [])
            else:
                beams_data = []

            for beam_data in beams_data:
                beam = StructuralElement(
                    id=beam_data.get("id", ""),
                    element_type=ElementType.BEAM,
                    length=beam_data.get("length", 0),
                    width=beam_data.get("width", 0) * 1000,  # m to mm
                    depth=beam_data.get("depth", 0) * 1000,  # m to mm
                    material=beam_data.get("material", "concrete"),
                    level=beam_data.get("level", ""),
                )
                beam.span = beam.length  # Initial span = length
                beams.append(beam)

        except Exception as e:
            print(f"Warning: Could not extract beams: {e}")

        return beams

    def _extract_slabs(self) -> List[StructuralElement]:
        """Extract structural slabs/floors"""
        slabs = []

        try:
            # Get floors from Revit API (already exists)
            floors_data = self.revit_api.list_floors()
            if isinstance(floors_data, dict):
                floors_data = floors_data.get("floors", [])

            for floor_data in floors_data:
                slab = StructuralElement(
                    id=floor_data.get("id", ""),
                    element_type=ElementType.SLAB,
                    length=floor_data.get("length", 0),
                    width=floor_data.get("width", 0),
                    depth=floor_data.get("thickness", 0) * 1000,  # m to mm
                    area=floor_data.get("area", 0),
                    material=floor_data.get("material", "concrete"),
                    level=floor_data.get("level", ""),
                )

                # Calculate span (use longer dimension)
                slab.span = max(slab.length, slab.width)

                slabs.append(slab)

        except Exception as e:
            print(f"Warning: Could not extract slabs: {e}")

        return slabs

    def _extract_walls(self) -> List[StructuralElement]:
        """Extract load-bearing walls"""
        walls = []

        try:
            # Get walls from Revit API (already exists)
            walls_data = self.revit_api.list_walls()
            if isinstance(walls_data, dict):
                walls_data = walls_data.get("walls", [])

            for wall_data in walls_data:
                # Check if load-bearing (simplified: assume all walls are load-bearing)
                is_structural = wall_data.get("is_structural", True)

                if is_structural:
                    wall = StructuralElement(
                        id=wall_data.get("id", ""),
                        element_type=ElementType.WALL,
                        length=wall_data.get("length", 0),
                        height=wall_data.get("height", 0),
                        depth=wall_data.get("thickness", 0) * 1000,  # m to mm
                        material=wall_data.get("material", "concrete"),
                        level=wall_data.get("level", ""),
                    )

                    # Store opening information if available
                    if "opening_width" in wall_data:
                        wall.loads["opening_width"] = wall_data["opening_width"]

                    walls.append(wall)

        except Exception as e:
            print(f"Warning: Could not extract walls: {e}")

        return walls

    def _extract_foundations(self) -> List[StructuralElement]:
        """Extract foundations"""
        foundations = []

        try:
            # Try to get foundations from Revit API
            if hasattr(self.revit_api, 'list_foundations'):
                foundations_data = self.revit_api.list_foundations()
                if isinstance(foundations_data, dict):
                    foundations_data = foundations_data.get("foundations", [])
            else:
                foundations_data = []

            for found_data in foundations_data:
                foundation = StructuralElement(
                    id=found_data.get("id", ""),
                    element_type=ElementType.FOUNDATION,
                    length=found_data.get("length", 0),
                    width=found_data.get("width", 0),
                    depth=found_data.get("depth", 0) * 1000,  # m to mm
                    area=found_data.get("area", 0),
                    material=found_data.get("material", "concrete"),
                )
                foundations.append(foundation)

        except Exception as e:
            print(f"Warning: Could not extract foundations: {e}")

        return foundations

    def _calculate_spans(self, model: StructuralModel):
        """Calculate spans for beams and slabs"""
        # Beams: span is already set to length
        for beam in model.beams:
            if beam.span == 0:
                beam.span = beam.length

        # Slabs: span is already set to max(length, width)
        for slab in model.slabs:
            if slab.span == 0:
                slab.span = max(slab.length, slab.width)

    def _establish_supports(self, model: StructuralModel):
        """Establish support relationships between elements"""
        # Simplified approach: assume columns support beams, beams support slabs
        # In reality, would need geometric analysis

        # Columns support beams at same level
        for beam in model.beams:
            for column in model.columns:
                if column.level == beam.level:
                    beam.supports.append(column.id)
                    column.supported_by.append(beam.id)

        # Beams support slabs at same level
        for slab in model.slabs:
            for beam in model.beams:
                if beam.level == slab.level:
                    slab.supports.append(beam.id)
                    beam.supported_by.append(slab.id)
