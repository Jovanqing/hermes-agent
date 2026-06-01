#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test validation with different building types
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from validation import DesignValidator

# Create validator
validator = DesignValidator()

# Test data for different building types
test_data = {
    "rooms": [
        {
            "id": "room_1",
            "name": "Office Workspace",
            "type": "office",
            "area": 50.0,
            "height": 2.5,  # Below minimum 2.7m
            "width": 5.0,
            "depth": 10.0,
            "person_count": 15,
        },
        {
            "id": "room_2",
            "name": "Meeting Room",
            "type": "meeting",
            "area": 20.0,
            "height": 2.8,
            "width": 4.0,
            "depth": 5.0,
        },
        {
            "id": "room_3",
            "name": "Retail Shop",
            "type": "retail",
            "area": 100.0,
            "height": 3.5,  # Below minimum 4.5m for retail
            "width": 10.0,
            "depth": 10.0,
        },
        {
            "id": "room_4",
            "name": "Patient Room (Single)",
            "type": "single_patient",
            "area": 18.0,  # Below minimum 20.0sqm
            "height": 3.2,  # Below minimum 3.3m for inpatient
            "width": 3.6,
            "depth": 5.0,
        },
    ],
    "doors": [
        {
            "id": "door_1",
            "width": 1.2,
            "is_exit": True,
        },
    ],
    "walls": [],
    "windows": [],
    "floors": [],
    "levels": [
        {"id": "level_1", "name": "Level 1", "elevation_m": 0.0},
        {"id": "level_2", "name": "Level 2", "elevation_m": 3.0},
        {"id": "level_3", "name": "Roof", "elevation_m": 6.0},
    ],
    "gross_area": 200.0,
    "orientation": 0,
}

print('='*80)
print('TESTING BUILDING TYPE VALIDATION')
print('='*80)

# Test 1: Residential (default)
print('\n[1] Residential Building:')
result = validator.validate(test_data, "residential")
print('  Score: {}/100'.format(result.score))
print('  Valid: {}'.format(result.is_valid()))
print('  Issues: {}'.format(len(result.issues)))
for issue in result.issues[:3]:
    print('    - [{}] {}: {}'.format(
        issue.severity.value.upper(),
        issue.category,
        issue.message[:60]
    ))

# Test 2: Commercial
print('\n[2] Commercial Building:')
result = validator.validate(test_data, "commercial")
print('  Score: {}/100'.format(result.score))
print('  Valid: {}'.format(result.is_valid()))
print('  Issues: {}'.format(len(result.issues)))
for issue in result.issues:
    print('    - [{}] {}: {}'.format(
        issue.severity.value.upper(),
        issue.category,
        issue.message[:60]
    ))

# Test 3: Office
print('\n[3] Office Building:')
result = validator.validate(test_data, "office")
print('  Score: {}/100'.format(result.score))
print('  Valid: {}'.format(result.is_valid()))
print('  Issues: {}'.format(len(result.issues)))
for issue in result.issues:
    print('    - [{}] {}: {}'.format(
        issue.severity.value.upper(),
        issue.category,
        issue.message[:60]
    ))

# Test 4: Healthcare
print('\n[4] Healthcare Building:')
result = validator.validate(test_data, "healthcare")
print('  Score: {}/100'.format(result.score))
print('  Valid: {}'.format(result.is_valid()))
print('  Issues: {}'.format(len(result.issues)))
for issue in result.issues:
    print('    - [{}] {}: {}'.format(
        issue.severity.value.upper(),
        issue.category,
        issue.message[:60]
    ))

print('\n' + '='*80)
print('VALIDATION TEST COMPLETE')
print('='*80)
