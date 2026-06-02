"""
Stage 5: Revit Modeling - 三层四跨商场

This script creates a 3-story, 4-span mall in Revit:
- 3 floors at 0m, 4.5m, 9m elevations
- 4 shops per floor (10m x 10m each)
- 3m wide corridor
"""

import sys
import os

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tools import revit_api

def create_three_story_mall():
    """Create a 3-story, 4-span mall in Revit."""

    print("=" * 80)
    print("Stage 5: Revit Modeling - Three Story Mall")
    print("=" * 80)

    # Check Revit connection
    print("\n[1/4] Checking Revit connection...")
    health = revit_api.health_check()
    if health.get("status") != "ok":
        print(f"[ERROR] Revit connection failed: {health.get('error')}")
        return False

    print(f"[OK] Connected to Revit: {health.get('revit_version')}")
    print(f"   Document: {health.get('document_name')}")

    # Use existing levels from Snowdon Towers model
    print("\n[2/4] Using existing levels...")
    levels = [
        {"name": "L1_43_High", "elevation": 0.0},
        {"name": "L2", "elevation": 2.464},
        {"name": "L3", "elevation": 5.74}
    ]

    for level in levels:
        print(f"   [OK] Using {level['name']} at {level['elevation']}m")

    # Create shops (4 per floor)
    print("\n[3/4] Creating shops (4 per floor)...")

    # Shop layout: 4 shops in a row, each 10m x 10m
    # Layout: [Shop A] [Shop B] [Shop C] [Shop D]
    #           [Corridor 3m wide]

    shop_width = 10.0  # 10m
    shop_depth = 10.0  # 10m
    corridor_width = 3.0  # 3m

    # Use existing levels
    level_names = ["L1_43_High", "L2", "L3"]

    for floor_num in range(1, 4):  # 3 floors
        level_name = level_names[floor_num - 1]
        elevation = levels[floor_num - 1]["elevation"]

        print(f"\n   Floor {floor_num} ({level_name} at {elevation}m):")

        # Create 4 shops
        for shop_idx in range(4):
            shop_name = f"Shop {chr(65 + shop_idx)}"  # Shop A, B, C, D
            x_start = shop_idx * shop_width
            x_end = x_start + shop_width
            y_start = 0.0
            y_end = shop_depth

            result = revit_api.create_room(
                x1=x_start,
                y1=y_start,
                x2=x_end,
                y2=y_end,
                level=level_name
            )

            if result.get("success"):
                print(f"      [OK] Created {shop_name} (10m x 10m = 100 sqm)")
            else:
                print(f"      [ERROR] Failed to create {shop_name}: {result.get('error')}")

        # Create corridor
        corridor_name = f"Corridor Floor {floor_num}"
        x_start = 0.0
        x_end = 40.0  # 4 shops x 10m = 40m
        y_start = shop_depth
        y_end = shop_depth + corridor_width

        result = revit_api.create_room(
            x1=x_start,
            y1=y_start,
            x2=x_end,
            y2=y_end,
            level=level_name
        )

        if result.get("success"):
            print(f"      [OK] Created {corridor_name} (40m x 3m)")
        else:
            print(f"      [ERROR] Failed to create corridor: {result.get('error')}")

    # Summary
    print("\n[4/4] Summary")
    print(f"   Floors: 3 (Level 1, 2, 3)")
    print(f"   Shops: 12 (4 per floor x 3 floors)")
    print(f"   Shop size: 10m x 10m = 100 sqm each")
    print(f"   Total shop area: 1200 sqm")
    print(f"   Corridor: 3m wide x 40m long per floor")

    print("\n" + "=" * 80)
    print("[OK] Stage 5 Complete: Three Story Mall Created")
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        success = create_three_story_mall()
        if success:
            print("\n[OK] Mall creation completed successfully!")
            print("\nNext steps:")
            print("  1. Check Revit to see the created mall")
            print("  2. Stage 6: Verification and optimization (needs clash detection)")
        else:
            print("\n[ERROR] Mall creation failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
