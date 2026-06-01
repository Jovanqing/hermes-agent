"""
SAP2000 Integration Module

Provides integration between Revit structural model and SAP2000:
- Export structural model to SAP2000 format (.s2k)
- Import model into SAP2000 via COM API
- Run analysis and retrieve results
- Optional: Write results back to Revit
"""

import os
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

# Try to import COM interface (Windows only)
try:
    import win32com.client
    import pythoncom
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False
    print("Warning: pywin32 not installed. COM API not available.")
    print("Install with: pip install pywin32")


class SAP2000Integration:
    """Integration with SAP2000 via COM API"""

    def __init__(self, sap2000_path: Optional[str] = None):
        """
        Initialize SAP2000 integration

        Args:
            sap2000_path: Path to SAP2000 installation
                         (default: auto-detect)
        """
        self.sap2000_path = sap2000_path or self._find_sap2000()
        self.sap_object = None
        self.model_initialized = False

    def _find_sap2000(self) -> Optional[str]:
        """Auto-detect SAP2000 installation path"""
        possible_paths = [
            r"C:\Program Files\Computers and Structures\SAP2000 26",
            r"C:\Program Files\Computers and Structures\SAP2000 25",
            r"C:\Program Files\Computers and Structures\SAP2000 24",
            r"C:\Program Files (x86)\Computers and Structures\SAP2000 26",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def connect(self) -> bool:
        """
        Connect to running SAP2000 instance

        Returns:
            True if connected successfully
        """
        if not COM_AVAILABLE:
            print("Error: COM interface not available. Install pywin32.")
            return False

        try:
            # Initialize COM
            pythoncom.CoInitialize()

            # Try to connect to running instance
            try:
                self.sap_object = win32com.client.GetActiveObject("CSI.SAP2000.API.SapObject")
                print("Connected to running SAP2000 instance")
                return True
            except:
                # No running instance, start new one
                if self.sap2000_path:
                    exe_path = os.path.join(self.sap2000_path, "SAP2000.exe")
                    if os.path.exists(exe_path):
                        self.sap_object = win32com.client.Dispatch("CSI.SAP2000.API.SapObject")
                        self.sap_object.ApplicationStart()
                        print("Started new SAP2000 instance")
                        return True

            print("Error: Could not connect to SAP2000")
            return False

        except Exception as e:
            print(f"Error connecting to SAP2000: {e}")
            return False

    def disconnect(self):
        """Disconnect from SAP2000"""
        if self.sap_object:
            try:
                self.sap_object.ApplicationExit(False)
                pythoncom.CoUninitialize()
                print("Disconnected from SAP2000")
            except:
                pass
            self.sap_object = None

    def open_model(self, model_path: str) -> bool:
        """
        Open a model in SAP2000

        Args:
            model_path: Path to .s2k or .sdb file

        Returns:
            True if opened successfully
        """
        if not self.sap_object:
            print("Error: Not connected to SAP2000")
            return False

        try:
            if not os.path.exists(model_path):
                print(f"Error: Model file not found: {model_path}")
                return False

            # Open file
            ret = self.sap_object.SapModel.File.OpenFile(model_path)
            if ret == 0:
                print(f"Opened model: {model_path}")
                self.model_initialized = True
                return True
            else:
                print(f"Error opening model: return code {ret}")
                return False

        except Exception as e:
            print(f"Error opening model: {e}")
            return False

    def save_model(self, save_path: str) -> bool:
        """
        Save current model

        Args:
            save_path: Path to save .sdb file

        Returns:
            True if saved successfully
        """
        if not self.sap_object or not self.model_initialized:
            print("Error: No model loaded")
            return False

        try:
            ret = self.sap_object.SapModel.File.Save(save_path)
            if ret == 0:
                print(f"Saved model: {save_path}")
                return True
            else:
                print(f"Error saving model: return code {ret}")
                return False

        except Exception as e:
            print(f"Error saving model: {e}")
            return False

    def run_analysis(self) -> bool:
        """
        Run structural analysis

        Returns:
            True if analysis completed successfully
        """
        if not self.sap_object or not self.model_initialized:
            print("Error: No model loaded")
            return False

        try:
            ret = self.sap_object.SapModel.Analyze.RunAnalysis()
            if ret == 0:
                print("Analysis completed successfully")
                return True
            else:
                print(f"Analysis failed: return code {ret}")
                return False

        except Exception as e:
            print(f"Error running analysis: {e}")
            return False

    def get_joint_displacements(self, joint_name: str) -> Optional[Dict[str, float]]:
        """
        Get displacements for a joint

        Args:
            joint_name: Name of joint

        Returns:
            Dictionary with U1, U2, U3, R1, R2, R3 displacements
        """
        if not self.sap_object or not self.model_initialized:
            return None

        try:
            ret, u1, u2, u3, r1, r2, r3 = self.sap_object.SapModel.Results.Joint.Disp(
                joint_name, 0, 0
            )

            if ret == 0:
                return {
                    "U1": u1[0],  # Translation X
                    "U2": u2[0],  # Translation Y
                    "U3": u3[0],  # Translation Z
                    "R1": r1[0],  # Rotation X
                    "R2": r2[0],  # Rotation Y
                    "R3": r3[0],  # Rotation Z
                }
            else:
                print(f"Error getting displacements: return code {ret}")
                return None

        except Exception as e:
            print(f"Error getting displacements: {e}")
            return None

    def get_frame_forces(self, frame_name: str) -> Optional[Dict[str, Any]]:
        """
        Get internal forces for a frame element

        Args:
            frame_name: Name of frame element

        Returns:
            Dictionary with P, V2, V3, T, M2, M3 forces
        """
        if not self.sap_object or not self.model_initialized:
            return None

        try:
            ret, p, v2, v3, t, m2, m3 = self.sap_object.SapModel.Results.Frame.Force(
                frame_name, 0, 0
            )

            if ret == 0:
                return {
                    "P": p,   # Axial force
                    "V2": v2, # Shear force (major)
                    "V3": v3, # Shear force (minor)
                    "T": t,   # Torsion
                    "M2": m2, # Moment (major)
                    "M3": m3, # Moment (minor)
                }
            else:
                print(f"Error getting frame forces: return code {ret}")
                return None

        except Exception as e:
            print(f"Error getting frame forces: {e}")
            return None

    def get_analysis_results_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get summary of analysis results

        Returns:
            Dictionary with analysis summary
        """
        if not self.sap_object or not self.model_initialized:
            return None

        try:
            # Get model info
            ret, num_joints = self.sap_object.SapModel.PointElm.Count()
            ret2, num_frames = self.sap_object.SapModel.FrameElm.Count()
            ret3, num_areas = self.sap_object.SapModel.AreaElm.Count()

            summary = {
                "num_joints": num_joints if ret == 0 else 0,
                "num_frames": num_frames if ret2 == 0 else 0,
                "num_areas": num_areas if ret3 == 0 else 0,
            }

            return summary

        except Exception as e:
            print(f"Error getting analysis summary: {e}")
            return None


class RevitToSAP2000Workflow:
    """Complete workflow from Revit to SAP2000"""

    def __init__(self, revit_api, sap2000_integration: SAP2000Integration):
        """
        Initialize workflow

        Args:
            revit_api: Revit API module
            sap2000_integration: SAP2000 integration instance
        """
        self.revit_api = revit_api
        self.sap2000 = sap2000_integration

    def export_and_analyze(
        self,
        export_path: str,
        run_analysis: bool = True,
        open_in_sap2000: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Complete workflow: Revit → SAP2000 → Analysis

        Args:
            export_path: Path to save .s2k file
            run_analysis: Whether to run analysis automatically
            open_in_sap2000: Whether to open model in SAP2000

        Returns:
            Analysis results or None
        """
        from structural import RevitStructuralExtractor, StructuralExporter, ExportFormat

        print("=" * 80)
        print("REVIT TO SAP2000 WORKFLOW")
        print("=" * 80)

        # Step 1: Extract structural model from Revit
        print("\n[Step 1] Extracting structural model from Revit...")
        extractor = RevitStructuralExtractor(self.revit_api)
        structural_model = extractor.extract()

        num_elements = len(structural_model.get_all_elements())
        print(f"  Extracted {num_elements} structural elements")
        print(f"    Columns: {len(structural_model.columns)}")
        print(f"    Beams: {len(structural_model.beams)}")
        print(f"    Slabs: {len(structural_model.slabs)}")
        print(f"    Walls: {len(structural_model.walls)}")

        if num_elements == 0:
            print("\nError: No structural elements found in Revit model")
            return None

        # Step 2: Export to SAP2000 format
        print(f"\n[Step 2] Exporting to SAP2000 format...")
        exporter = StructuralExporter(structural_model)

        # Ensure path has .s2k extension
        if not export_path.endswith('.s2k'):
            export_path += '.s2k'

        s2k_content = exporter.export(ExportFormat.SAP2000)

        # Save to file
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(s2k_content)

        print(f"  Exported to: {export_path}")
        print(f"  File size: {len(s2k_content)} characters")

        # Step 3: Open in SAP2000 (if requested)
        if open_in_sap2000:
            print(f"\n[Step 3] Opening model in SAP2000...")

            if not self.sap2000.connect():
                print("  Warning: Could not connect to SAP2000")
                print("  You can manually open the file in SAP2000")
                return None

            if not self.sap2000.open_model(export_path):
                print("  Warning: Could not open model in SAP2000")
                return None

        # Step 4: Run analysis (if requested)
        if run_analysis and open_in_sap2000:
            print(f"\n[Step 4] Running structural analysis...")

            if not self.sap2000.run_analysis():
                print("  Warning: Analysis failed")
                return None

            # Get analysis summary
            print(f"\n[Step 5] Retrieving analysis results...")
            summary = self.sap2000.get_analysis_results_summary()

            if summary:
                print(f"  Analysis Summary:")
                print(f"    Joints: {summary['num_joints']}")
                print(f"    Frames: {summary['num_frames']}")
                print(f"    Areas: {summary['num_areas']}")

                return summary

        return None

    def get_joint_results(self, joint_names: List[str]) -> Dict[str, Dict]:
        """
        Get results for specific joints

        Args:
            joint_names: List of joint names

        Returns:
            Dictionary with joint displacements
        """
        results = {}

        for joint_name in joint_names:
            disp = self.sap2000.get_joint_displacements(joint_name)
            if disp:
                results[joint_name] = disp

        return results

    def get_frame_results(self, frame_names: List[str]) -> Dict[str, Dict]:
        """
        Get results for specific frame elements

        Args:
            frame_names: List of frame names

        Returns:
            Dictionary with frame forces
        """
        results = {}

        for frame_name in frame_names:
            forces = self.sap2000.get_frame_forces(frame_name)
            if forces:
                results[frame_name] = forces

        return results


def create_revit_to_sap2000_workflow(revit_api) -> Optional[RevitToSAP2000Workflow]:
    """
    Factory function to create workflow

    Args:
        revit_api: Revit API module

    Returns:
        RevitToSAP2000Workflow instance or None
    """
    # Create SAP2000 integration
    sap2000 = SAP2000Integration()

    # Check if SAP2000 is available
    if not sap2000.sap2000_path:
        print("Error: SAP2000 installation not found")
        return None

    print(f"Found SAP2000 at: {sap2000.sap2000_path}")

    # Create workflow
    workflow = RevitToSAP2000Workflow(revit_api, sap2000)

    return workflow
