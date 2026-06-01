#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo: Revit ↔ SAP2000 Integration

Demonstrates the complete workflow:
1. Extract structural model from Revit
2. Export to SAP2000 format (.s2k)
3. Open in SAP2000 automatically
4. Run structural analysis
5. Retrieve results

Requirements:
- Revit running with VibeBuilding extension
- SAP2000 installed (auto-detected)
- pywin32 (for COM API) - optional
"""

import sys
import io
import os

# UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("REVIT ↔ SAP2000 INTEGRATION DEMO")
print("=" * 80)

# Check if pywin32 is available
try:
    import win32com.client
    print("\n✓ pywin32 installed - COM API available")
    COM_AVAILABLE = True
except ImportError:
    print("\n✗ pywin32 not installed - COM API not available")
    print("  Install with: pip install pywin32")
    print("  Then run: python -m pywin32_postinstall -install")
    COM_AVAILABLE = False

# Import modules
from tools import revit_api
from structural import (
    RevitStructuralExtractor,
    StructuralExporter,
    ExportFormat,
    SAP2000Integration,
)

# Step 1: Check Revit connection
print("\n" + "=" * 80)
print("[STEP 1] Checking Revit Connection")
print("=" * 80)

health = revit_api.health_check()
if health.get("status") == "ok":
    print(f"✓ Connected to Revit {health.get('revit_version')}")
    print(f"  Document: {health.get('document_name')}")
else:
    print("✗ Cannot connect to Revit")
    print("  Make sure Revit is running with VibeBuilding extension")
    sys.exit(1)

# Step 2: Extract structural model from Revit
print("\n" + "=" * 80)
print("[STEP 2] Extracting Structural Model from Revit")
print("=" * 80)

extractor = RevitStructuralExtractor(revit_api)
structural_model = extractor.extract()

num_elements = len(structural_model.get_all_elements())
print(f"\nExtracted {num_elements} structural elements:")
print(f"  Columns: {len(structural_model.columns)}")
print(f"  Beams: {len(structural_model.beams)}")
print(f"  Slabs: {len(structural_model.slabs)}")
print(f"  Walls: {len(structural_model.walls)}")
print(f"  Foundations: {len(structural_model.foundations)}")

if num_elements == 0:
    print("\n⚠ Warning: No structural elements found in Revit model")
    print("  The current model may only contain architectural elements")
    print("  Continuing with export to show the workflow...")

# Step 3: Export to SAP2000 format
print("\n" + "=" * 80)
print("[STEP 3] Exporting to SAP2000 Format")
print("=" * 80)

exporter = StructuralExporter(structural_model)

# Create export directory
export_dir = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(export_dir, exist_ok=True)

# Export to SAP2000 format
s2k_path = os.path.join(export_dir, "vibevilla_structural.s2k")
s2k_content = exporter.export(ExportFormat.SAP2000)

with open(s2k_path, 'w', encoding='utf-8') as f:
    f.write(s2k_content)

print(f"\n✓ Exported to: {s2k_path}")
print(f"  File size: {len(s2k_content)} characters")
print(f"  Lines: {len(s2k_content.splitlines())}")

# Show preview of exported file
print("\nPreview (first 30 lines):")
print("-" * 80)
for i, line in enumerate(s2k_content.splitlines()[:30]):
    print(f"  {line}")
if len(s2k_content.splitlines()) > 30:
    print(f"  ... ({len(s2k_content.splitlines()) - 30} more lines)")

# Also export to other formats
csv_path = os.path.join(export_dir, "vibevilla_structural.csv")
csv_content = exporter.export(ExportFormat.CSV)
with open(csv_path, 'w', encoding='utf-8') as f:
    f.write(csv_content)
print(f"\n✓ Also exported CSV: {csv_path}")

json_path = os.path.join(export_dir, "vibevilla_structural.json")
json_content = exporter.export(ExportFormat.JSON)
with open(json_path, 'w', encoding='utf-8') as f:
    f.write(json_content)
print(f"✓ Also exported JSON: {json_path}")

# Step 4: Try to open in SAP2000
print("\n" + "=" * 80)
print("[STEP 4] Opening in SAP2000")
print("=" * 80)

sap2000 = SAP2000Integration()

if sap2000.sap2000_path:
    print(f"\n✓ Found SAP2000 at: {sap2000.sap2000_path}")

    if COM_AVAILABLE:
        print("\nAttempting to connect to SAP2000 via COM API...")

        if sap2000.connect():
            print("✓ Connected to SAP2000")

            print(f"\nOpening model: {s2k_path}")
            if sap2000.open_model(s2k_path):
                print("✓ Model opened in SAP2000")

                # Step 5: Run analysis
                print("\n" + "=" * 80)
                print("[STEP 5] Running Structural Analysis")
                print("=" * 80)

                print("\nRunning analysis...")
                if sap2000.run_analysis():
                    print("✓ Analysis completed successfully")

                    # Get results summary
                    print("\nRetrieving analysis results...")
                    summary = sap2000.get_analysis_results_summary()

                    if summary:
                        print("\n✓ Analysis Summary:")
                        print(f"  Joints: {summary['num_joints']}")
                        print(f"  Frames: {summary['num_frames']}")
                        print(f"  Areas: {summary['num_areas']}")

                    print("\n" + "=" * 80)
                    print("[STEP 6] Analysis Complete!")
                    print("=" * 80)
                    print("\n✓ Workflow completed successfully!")
                    print("\nYou can now:")
                    print("  1. View results in SAP2000")
                    print("  2. Check displacements, forces, and stresses")
                    print("  3. Modify the model and re-analyze")
                    print("  4. Export results back to Revit (future feature)")

                    # Don't disconnect - let user work with SAP2000
                    print("\nNote: SAP2000 remains open for you to work with")
                    print("      Disconnect when done (sap2000.disconnect())")

                else:
                    print("✗ Analysis failed")
                    print("  You can manually run analysis in SAP2000")

            else:
                print("✗ Could not open model in SAP2000")
                print("\nYou can manually open the file:")
                print(f"  1. Open SAP2000")
                print(f"  2. File → Open → {s2k_path}")

        else:
            print("✗ Could not connect to SAP2000")
            print("\nManual workflow:")
            print(f"  1. Open SAP2000")
            print(f"  2. File → Open → {s2k_path}")
            print(f"  3. Analyze → Run Analysis")

    else:
        print("\n⚠ pywin32 not available")
        print("\nManual workflow:")
        print(f"  1. Open SAP2000")
        print(f"  2. File → Open → {s2k_path}")
        print(f"  3. Analyze → Run Analysis")

else:
    print("\n✗ SAP2000 installation not found")
    print("\nManual workflow:")
    print(f"  1. Open SAP2000")
    print(f"  2. File → Open → {s2k_path}")
    print(f"  3. Analyze → Run Analysis")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print("\n✓ Workflow completed!")
print("\nExported files:")
print(f"  • SAP2000: {s2k_path}")
print(f"  • CSV: {csv_path}")
print(f"  • JSON: {json_path}")

print("\nNext steps:")
if COM_AVAILABLE and sap2000.sap2000_path:
    print("  1. Work with the model in SAP2000 (already open)")
    print("  2. View displacements, forces, stresses")
    print("  3. Modify and re-analyze as needed")
else:
    print("  1. Open SAP2000 manually")
    print(f"  2. Open: {s2k_path}")
    print("  3. Run analysis: Analyze → Run Analysis")
    print("  4. View results")

print("\n" + "=" * 80)
