"""
Test script for Vibe Building validation and learning system

Demonstrates:
1. Design validation against building codes
2. Pattern discovery from validation results
3. Learning from design experience
4. Self-evolution through skill updates
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from validation import DesignValidator, Severity
from hermes_integration import (
    revit_validate_design,
    revit_get_building_code_reference,
    revit_check_room_compliance,
    revit_optimize_design,
    revit_learn_from_design,
)


def test_validation():
    """Test design validation"""
    print("=" * 80)
    print("TEST 1: Design Validation")
    print("=" * 80)

    result_json = revit_validate_design()
    result = json.loads(result_json)

    print(f"\nValidation Score: {result['score']}/100")
    print(f"Valid: {result['valid']}")
    print(f"\nSummary:")
    for severity, count in result['summary'].items():
        print(f"  {severity.upper()}: {count}")

    print(f"\nIssues Found: {len(result['issues'])}")
    for i, issue in enumerate(result['issues'][:5], 1):  # Show first 5
        print(f"\n{i}. [{issue['severity'].upper()}] {issue['category']}")
        print(f"   {issue['message']}")
        if issue['suggestion']:
            print(f"   → {issue['suggestion']}")

    if len(result['issues']) > 5:
        print(f"\n   ... and {len(result['issues']) - 5} more issues")

    return result


def test_building_codes():
    """Test building code reference"""
    print("\n" + "=" * 80)
    print("TEST 2: Building Code Reference")
    print("=" * 80)

    # Test GB 50096
    print("\nGB 50096 - Residential Design Code:")
    result_json = revit_get_building_code_reference("GB 50096")
    result = json.loads(result_json)

    print(f"\nName: {result['name']} ({result['year']})")
    print("\nKey Requirements:")
    for req, details in result['key_requirements'].items():
        print(f"  {req}: {details['min']} {details.get('unit', '')}")
        if 'note' in details:
            print(f"    Note: {details['note']}")


def test_room_compliance():
    """Test room compliance checking"""
    print("\n" + "=" * 80)
    print("TEST 3: Room Compliance Check")
    print("=" * 80)

    result_json = revit_check_room_compliance()
    result = json.loads(result_json)

    print(f"\nRooms Checked: {result['rooms_checked']}")

    # Handle case when room listing is not available
    if 'message' in result:
        print(f"Note: {result['message']}")
        return

    print(f"Compliant: {result['compliant_count']}/{result['rooms_checked']}")

    for room in result['results'][:3]:  # Show first 3
        print(f"\n{room['room_name']} ({room['room_type']}):")
        print(f"  Compliant: {room['compliant']}")
        if room['issues']:
            for issue in room['issues']:
                print(f"  ⚠ {issue['parameter']}: {issue['value']} {issue['unit']} < {issue['minimum']} {issue['unit']}")


def test_optimization():
    """Test design optimization"""
    print("\n" + "=" * 80)
    print("TEST 4: Design Optimization")
    print("=" * 80)

    for objective in ["space", "cost", "energy"]:
        print(f"\n{objective.upper()} Optimization:")
        result_json = revit_optimize_design(objective)
        result = json.loads(result_json)

        print(f"  Suggestions: {result['count']}")
        for suggestion in result['suggestions'][:2]:  # Show first 2
            print(f"  → {suggestion.get('type', 'optimization')}")
            if 'action' in suggestion:
                print(f"    Action: {suggestion['action']}")
            if 'benefit' in suggestion:
                print(f"    Benefit: {suggestion['benefit']}")


def test_learning():
    """Test learning from design"""
    print("\n" + "=" * 80)
    print("TEST 5: Learning from Design (Self-Evolution)")
    print("=" * 80)

    print("\nAnalyzing design patterns and learning...")
    result_json = revit_learn_from_design(
        design_type="residential",
        lessons="Optimized circulation, improved natural lighting, better privacy"
    )
    result = json.loads(result_json)

    print(f"\nLearning Results:")
    print(f"  Success: {result['success']}")
    print(f"  Patterns Found: {result['patterns_found']}")
    print(f"  Validation Score: {result['validation_score']}/100")

    print(f"\nNext Steps:")
    for step in result['next_steps']:
        print(f"  → {step}")

    if result['details']['patterns']:
        print(f"\nDiscovered Patterns:")
        for pattern in result['details']['patterns'][:3]:
            print(f"  Category: {pattern['category']}")
            print(f"    Frequency: {pattern['frequency']}")
            print(f"    Pattern: {pattern['common_message']}")


def demo_self_evolution_loop():
    """Demonstrate the complete self-evolution loop"""
    print("\n" + "=" * 80)
    print("SELF-EVOLUTION LOOP DEMONSTRATION")
    print("=" * 80)

    print("""
The Vibe Building system implements a complete self-evolution loop:

1. DESIGN CREATION
   └─> User creates design in Revit using natural language

2. DESIGN VALIDATION
   └─> System validates against building codes, structural requirements,
       design patterns, and optimization criteria

3. PATTERN DISCOVERY
   └─> System analyzes validation results to discover common patterns
   └─> Identifies recurring issues and best practices

4. SKILL CREATION/UPDATE
   └─> Creates new architectural skills in hermes
   └─> Updates existing skills with new patterns
   └─> Stores in ~/.hermes/skills/architecture/

5. BACKGROUND REVIEW (Hermes Self-Evolution)
   └─> Hermes background review consolidates patterns
   └─> Merges similar skills into umbrella skills
   └─> Archives unused skills, promotes successful ones

6. MEMORY INTEGRATION
   └─> Stores design decisions in hermes memory
   └─> Remembers user preferences and project context
   └─> Provides context for future designs

7. CONTINUOUS IMPROVEMENT
   └─> Next design benefits from learned patterns
   └─> Validation becomes more accurate
   └─> Suggestions become more relevant
   └─> Cycle repeats with improved knowledge

This creates a virtuous cycle where the system gets better with every project!
""")

    print("\n" + "=" * 80)
    print("ARCHITECTURE SKILLS CREATED")
    print("=" * 80)

    skills_dir = Path(__file__).parent / "skills" / "architecture"
    if skills_dir.exists():
        print("\nSkills Directory: skills/architecture/")
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    print(f"  [OK] {skill_dir.name}/")
                    print(f"    └─ SKILL.md")
                    # Count reference files
                    refs_dir = skill_dir / "references"
                    if refs_dir.exists():
                        refs = list(refs_dir.glob("*.md"))
                        if refs:
                            print(f"    └─ references/ ({len(refs)} files)")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("VIBE BUILDING - VALIDATION & LEARNING SYSTEM TEST")
    print("=" * 80)

    try:
        # Run tests
        test_validation()
        test_building_codes()
        test_room_compliance()
        test_optimization()
        test_learning()

        # Demo self-evolution
        demo_self_evolution_loop()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
