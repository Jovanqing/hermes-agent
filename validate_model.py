#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate the real Revit model
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tools import revit_api
from validation.design_validator import extract_model_data, DesignValidator
import json

print('='*80)
print('VALIDATING REAL REVIT MODEL')
print('='*80)

# Extract data from real model
print('\n[1] Extracting model data...')
model_data = extract_model_data(revit_api)

print('  Levels: {}'.format(len(model_data['levels'])))
print('  Walls: {}'.format(len(model_data['walls'])))
print('  Rooms: {}'.format(len(model_data['rooms'])))
print('  Doors: {}'.format(len(model_data['doors'])))
print('  Windows: {}'.format(len(model_data['windows'])))
print('  Floors: {}'.format(len(model_data['floors'])))
print('  Gross Area: {:.1f} m2'.format(model_data['gross_area']))

# Show level details
if model_data['levels']:
    print('\n  Level details:')
    for level in model_data['levels']:
        print('    - {}: {:.1f}m'.format(
            level.get('name', 'Unknown'),
            level.get('elevation_m', 0)
        ))

# Show wall details
if model_data['walls']:
    print('\n  Wall details (first 5):')
    for wall in model_data['walls'][:5]:
        print('    - ID {}: {:.1f}m long'.format(
            wall.get('id', 'Unknown'),
            wall.get('length_m', 0)
        ))

# Run validation
print('\n[2] Running validation...')
validator = DesignValidator()
result = validator.validate(model_data)

print('  Score: {}/100'.format(result.score))
print('  Valid: {}'.format(result.is_valid()))
print('  Issues: {}'.format(len(result.issues)))

# Show issues by category
issues_by_category = {}
for issue in result.issues:
    cat = issue.category
    if cat not in issues_by_category:
        issues_by_category[cat] = []
    issues_by_category[cat].append(issue)

print('\n[3] Issues by category:')
for category, issues in issues_by_category.items():
    print('  {}: {} issues'.format(category, len(issues)))
    for issue in issues[:2]:  # Show first 2 per category
        msg = issue.message[:60]
        print('    - [{}] {}'.format(issue.severity.value.upper(), msg))
        if issue.suggestion:
            sug = issue.suggestion[:60]
            print('      Suggestion: {}'.format(sug))

print('\n' + '='*80)
print('VALIDATION COMPLETE')
print('='*80)
