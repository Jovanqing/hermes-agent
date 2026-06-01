"""
Structural Analysis Module for Vibe Building

Provides structural analysis and integration with external tools:
- Extract structural elements from Revit (columns, beams, slabs, loads)
- Perform basic structural checks (span limits, load calculations, deflection)
- Export data for external analysis tools (ETABS, SAP2000)
- Validate against structural codes (GB 50009, GB 50010, GB 50011)
- Direct integration with SAP2000 via COM API
"""

from .structural_analyzer import (
    StructuralAnalyzer,
    StructuralElement,
    ElementType,
    LoadType,
    StructuralCheck,
    CheckSeverity,
    StructuralReport,
)

from .revit_structural_extractor import (
    RevitStructuralExtractor,
    StructuralModel,
)

from .structural_exporter import (
    StructuralExporter,
    ExportFormat,
)

from .sap2000_integration import (
    SAP2000Integration,
    RevitToSAP2000Workflow,
    create_revit_to_sap2000_workflow,
)

__all__ = [
    "StructuralAnalyzer",
    "StructuralElement",
    "ElementType",
    "LoadType",
    "StructuralCheck",
    "CheckSeverity",
    "StructuralReport",
    "RevitStructuralExtractor",
    "StructuralModel",
    "StructuralExporter",
    "ExportFormat",
    "SAP2000Integration",
    "RevitToSAP2000Workflow",
    "create_revit_to_sap2000_workflow",
]
