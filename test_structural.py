#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test structural analysis module
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from structural import (
    StructuralAnalyzer,
    StructuralElement,
    ElementType,
    RevitStructuralExtractor,
    StructuralExporter,
    ExportFormat,
)
from tools import revit_api

print('='*80)
print('TESTING STRUCTURAL ANALYSIS MODULE')
print('='*80)

# Test 1: Create sample structural elements
print('\n[1] Creating sample structural elements...')

columns = [
    StructuralElement(
        id="COL1",
        element_type=ElementType.COLUMN,
        width=300,  # mm
        depth=300,  # mm
        height=3.0,  # m
        level="Level 1",
    ),
    StructuralElement(
        id="COL2",
        element_type=ElementType.COLUMN,
        width=350,  # mm
        depth=350,  # mm
        height=3.0,  # m
        level="Level 1",
        loads={"total": 2800},  # kN (exceeds capacity)
    ),
]

beams = [
    StructuralElement(
        id="BEAM1",
        element_type=ElementType.BEAM,
        length=6.0,  # m
        width=250,  # mm
        depth=400,  # mm (too shallow for 6m span)
        level="Level 1",
        span=6.0,
        supports=["COL1", "COL2"],
    ),
    StructuralElement(
        id="BEAM2",
        element_type=ElementType.BEAM,
        length=9.0,  # m (exceeds max span)
        width=300,  # mm
        depth=600,  # mm
        level="Level 1",
        span=9.0,
        supports=["COL1"],
    ),
]

slabs = [
    StructuralElement(
        id="SLAB1",
        element_type=ElementType.SLAB,
        length=5.0,  # m
        width=4.0,  # m
        depth=120,  # mm
        area=20.0,  # sqm
        level="Level 1",
        span=5.0,  # max(5, 4)
        supports=["BEAM1"],
    ),
]

walls = [
    StructuralElement(
        id="WALL1",
        element_type=ElementType.WALL,
        length=6.0,  # m
        height=3.0,  # m
        depth=200,  # mm
        level="Level 1",
        loads={"opening_width": 2.0},  # m (exceeds limit)
    ),
]

elements = columns + beams + slabs + walls
print(f'  Created {len(elements)} elements')

# Test 2: Run structural analysis
print('\n[2] Running structural analysis...')
analyzer = StructuralAnalyzer()
report = analyzer.analyze(elements)

print(f'  Score: {report.score}/100')
print(f'  Valid: {report.is_valid()}')
print(f'  Checks: {len(report.checks)}')

summary = report.get_summary()
print(f'  Errors: {summary["error"]}')
print(f'  Warnings: {summary["warning"]}')
print(f'  Info: {summary["info"]}')

# Show detailed checks
print('\n[3] Structural check results:')
for check in report.checks:
    print(f'  [{check.severity.value.upper()}] {check.check_name}')
    print(f'    {check.message}')
    if check.suggestion:
        print(f'    Suggestion: {check.suggestion}')
    print()

# Test 3: Extract from Revit
print('[4] Testing Revit extraction...')
try:
    extractor = RevitStructuralExtractor(revit_api)
    revit_model = extractor.extract()
    print(f'  Extracted {len(revit_model.get_all_elements())} elements from Revit')
    print(f'    Columns: {len(revit_model.columns)}')
    print(f'    Beams: {len(revit_model.beams)}')
    print(f'    Slabs: {len(revit_model.slabs)}')
    print(f'    Walls: {len(revit_model.walls)}')
except Exception as e:
    print(f'  Warning: Could not extract from Revit: {e}')
    revit_model = None

# Test 4: Export to different formats
print('\n[5] Testing export functionality...')

# Create a model for export
from structural.revit_structural_extractor import StructuralModel
test_model = StructuralModel()
test_model.columns = columns
test_model.beams = beams
test_model.slabs = slabs
test_model.walls = walls

exporter = StructuralExporter(test_model)

# Export to JSON
json_output = exporter.export(ExportFormat.JSON)
print(f'  JSON export: {len(json_output)} characters')

# Export to CSV
csv_output = exporter.export(ExportFormat.CSV)
print(f'  CSV export: {len(csv_output)} characters')

# Export to ETABS
etabs_output = exporter.export(ExportFormat.ETABS)
print(f'  ETABS export: {len(etabs_output)} characters')

# Export to SAP2000
sap_output = exporter.export(ExportFormat.SAP2000)
print(f'  SAP2000 export: {len(sap_output)} characters')

# Show sample ETABS output
print('\n[6] Sample ETABS output (first 30 lines):')
etabs_lines = etabs_output.split('\n')
for i, line in enumerate(etabs_lines[:30]):
    print(f'  {line}')

print('\n' + '='*80)
print('STRUCTURAL ANALYSIS TEST COMPLETE')
print('='*80)
