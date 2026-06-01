---
name: revit-modeling
description: Best practices for BIM modeling in Revit. Covers family organization, worksharing, parametric design, and model management.
version: 1.0.0
metadata:
  hermes:
    tags: [architecture, revit, bim, modeling, workflow]
---

# Revit BIM Modeling Best Practices

## 1. Project Organization

### 1.1 Browser Organization

**Standard Folder Structure**:
```
├── Views
│   ├── Floor Plans
│   │   ├── 01 - Ground Floor
│   │   ├── 02 - First Floor
│   │   └── 03 - Roof Plan
│   ├── 3D Views
│   │   ├── Overall
│   │   ├── Interior
│   │   └── Details
│   ├── Sections
│   │   ├── Building Sections
│   │   └── Wall Sections
│   └── Schedules
│       ├── Room Schedule
│       ├── Door Schedule
│       └── Window Schedule
├── Families
│   ├── Architectural
│   ├── Structural
│   └── MEP
└── Groups
    ├── Model Groups
    └── Detail Groups
```

### 1.2 Naming Conventions

**Views**: `{Type} - {Level} - {Description}`
- Example: `Floor Plan - 01 GF - Furniture Layout`
- Example: `Section - A-A - Stair Detail`

**Families**: `{Category} - {Type} - {Size}`
- Example: `Door - Single - 900×2100`
- Example: `Window - Fixed - 1200×1500`

**Levels**: `{Prefix} - {Name}`
- Example: `00 - Site`
- Example: `01 - Ground Floor`
- Example: `02 - First Floor`

**Sheets**: `{Number} - {Name}`
- Example: `A101 - Ground Floor Plan`
- Example: `A201 - First Floor Plan`

## 2. Modeling Best Practices

### 2.1 Wall Modeling

**DO**:
- Use wall types from template (don't create custom unless necessary)
- Set correct base/top constraints
- Use location line: "Finish Face: Exterior" for exterior walls
- Join walls at corners (use Join Geometry)
- Use wall sweeps/reveals for articulation

**DON'T**:
- Don't stack walls (use single multi-layer wall)
- Don't split walls unnecessarily (creates cleanup issues)
- Don't use in-place families for standard walls

**Validation Rules**:
```
IF wall.height > 5.0m AND wall.type == "Basic":
    WARNING: Tall basic wall may need structural support
    SUGGEST: Use structural wall type or add columns

IF wall.length > 10.0m AND no_control_joints:
    WARNING: Long wall without control joints
    SUGGEST: Add control joints every 6-8m
```

### 2.2 Floor Modeling

**DO**:
- Use floor boundary (sketch mode) for complex shapes
- Set correct level and offset
- Use slope arrow for sloped floors
- Join floors to walls (automatic join)

**DON'T**:
- Don't use floor for thin finishes (use wall sweep or paint)
- Don't create multiple overlapping floors
- Don't use in-place families for standard floors

**Validation Rules**:
```
IF floor.area > 100 sqm AND thickness < 150mm:
    WARNING: Large thin slab may deflect
    SUGGEST: Increase thickness or add beams

IF floor.slope > 5%:
    WARNING: Steep floor may be slippery
    SUGGEST: Add non-slip finish or reduce slope
```

### 2.3 Roof Modeling

**DO**:
- Use footprint roof for simple shapes
- Use extrusion roof for complex shapes
- Set correct slope (1:12 minimum for drainage)
- Add fascia/soffit for finish

**DON'T**:
- Don't use flat roof without slope (ponding risk)
- Don't forget roof drainage (gutters, downspouts)
- Don't ignore thermal bridging at eaves

**Validation Rules**:
```
IF roof.slope < 2%:
    WARNING: Insufficient slope for drainage
    REQUIRE: Minimum 2% slope (1:50)
    
IF roof.area > 200 sqm AND no_drainage:
    WARNING: Large roof without drainage
    REQUIRE: Add gutters and downspouts
```

### 2.4 Door/Window Modeling

**DO**:
- Use hosted families (wall-hosted)
- Set correct sill/head height
- Use type parameters for sizes
- Add rough opening in family

**DON'T**:
- Don't use face-hosted for standard doors/windows
- Don't forget to tag doors/windows
- Don't use generic models for doors/windows

**Validation Rules**:
```
IF door.width < 800mm:
    WARNING: Door too narrow for accessibility
    REQUIRE: Minimum 800mm clear width
    
IF window.sill_height < 900mm AND floor == upper:
    WARNING: Low window on upper floor (fall risk)
    REQUIRE: Window guard or increase sill to 900mm
    
IF window.area / room.area > 0.5:
    WARNING: Excessive glazing (heat loss/gain)
    SUGGEST: Reduce to 30-40% of wall area
```

## 3. Family Creation Best Practices

### 3.1 Parametric Families

**DO**:
- Use type parameters for standard sizes
- Use instance parameters for placement variations
- Add constraints (aligned dimensions)
- Use formulas for derived parameters
- Test flexibility (flex and stretch)

**DON'T**:
- Don't over-parameterize (keep it simple)
- Don't use reference planes unnecessarily
- Don't forget to purge unused types

**Example: Parametric Window**:
```
Type Parameters:
- Width: 900, 1200, 1500, 1800 mm
- Height: 1200, 1500, 1800, 2100 mm
- Frame Width: 60 mm (fixed)

Instance Parameters:
- Sill Height: 900 mm (adjustable)
- Head Height: = Sill Height + Height (formula)

Formulas:
- Rough Width = Width + 20mm (10mm each side)
- Rough Height = Height + 20mm (10mm each side)
```

### 3.2 Shared Parameters

**Use Shared Parameters When**:
- Parameter needs to appear in schedules
- Parameter needs to be tagged
- Parameter shared across multiple families

**Shared Parameter File**:
```
Location: Company shared parameters file
Format: .txt (Revit shared parameters)

Groups:
- Architectural (door width, window height)
- Structural (load capacity, material grade)
- MEP (flow rate, pressure drop)
```

## 4. Worksharing Best Practices

### 4.1 Worksets

**Standard Worksets**:
```
Shared Levels and Grids (always check out)
Exterior (exterior walls, windows, doors)
Interior (interior walls, doors)
Furniture (movable furniture)
MEP (mechanical, electrical, plumbing)
Site (topography, landscaping)
```

**Workset Rules**:
- Don't check out entire workset (use element borrowing)
- Reload latest frequently (every 30 minutes)
- Save to central every 2 hours
- Don't work in default workset

### 4.2 Collaboration

**DO**:
- Communicate before making major changes
- Use worksets to divide work
- Sync with central before leaving
- Purge unused families periodically

**DON'T**:
- Don't work offline for extended periods
- Don't make changes without syncing
- Don't delete worksets (archive instead)

## 5. Performance Optimization

### 5.1 Model Size

**Target File Sizes**:
| Project Type | Target Size |
|--------------|-------------|
| Small house | < 50 MB |
| Medium residential | < 150 MB |
| Large residential | < 300 MB |
| Commercial | < 500 MB |

**Optimization Strategies**:
```
IF file_size > target:
    TRY:
    1. Purge unused (families, types, materials)
    2. Remove imported CAD files
    3. Simplify complex families (reduce detail level)
    4. Use worksets to unload unused work
    5. Delete unused views and sheets
```

### 5.2 View Performance

**DO**:
- Use view templates for consistency
- Hide unnecessary categories in working views
- Use detail level: Coarse for working, Fine for documentation
- Use visibility/graphics overrides (VG)

**DON'T**:
- Don't use realistic view for working (slow)
- Don't show all categories in all views
- Don't use shadows in working views

### 5.3 Hardware Recommendations

**Minimum Specs**:
- CPU: 3.0 GHz, 6+ cores
- RAM: 32 GB (64 GB for large projects)
- GPU: 4 GB VRAM (8 GB for complex models)
- Storage: SSD (NVMe preferred)

**Optimization**:
```
IF model_slow:
    CHECK:
    1. RAM usage (should be < 80%)
    2. GPU drivers (update to latest)
    3. Disk space (should be > 20% free)
    4. Background processes (close unnecessary)
```

## 6. Documentation Best Practices

### 6.1 View Templates

**Standard Templates**:
```
Floor Plan - Working (1:100, coarse, no dimensions)
Floor Plan - Presentation (1:50, fine, with furniture)
Floor Plan - Construction (1:50, fine, with dimensions)
Section - Detail (1:10, fine, with annotations)
3D View - Perspective (realistic, with materials)
```

### 6.2 Sheet Organization

**Standard Sheet Order**:
```
A000 - Cover Sheet
A001 - Site Plan
A101 - Ground Floor Plan
A102 - First Floor Plan
A201 - Elevations (North, South)
A202 - Elevations (East, West)
A301 - Sections (Building)
A401 - Wall Sections
A501 - Schedules (Doors, Windows)
A601 - Details
```

### 6.3 Annotation

**DO**:
- Use keynotes for materials
- Use tags for elements (doors, windows, rooms)
- Use dimensions for construction
- Use text for notes

**DON'T**:
- Don't over-dimension (only what's needed)
- Don't use text for tags (use tag tool)
- Don't forget to coordinate dimensions

## 7. Quality Control

### 7.1 Model Audit Checklist

**Weekly Checks**:
- [ ] All walls joined at corners
- [ ] All floors joined to walls
- [ ] All doors/windows tagged
- [ ] All rooms placed and named
- [ ] Warnings < 10 (resolve critical)
- [ ] File size within target
- [ ] Central file synced

**Monthly Checks**:
- [ ] Purge unused families
- [ ] Audit worksets
- [ ] Review naming conventions
- [ ] Check for duplicate families
- [ ] Verify shared parameters

### 7.2 Clash Detection

**Standard Clash Matrix**:
| Element 1 | Element 2 | Tolerance |
|-----------|-----------|-----------|
| Structural | Architectural | 50mm |
| Structural | MEP | 25mm |
| Architectural | MEP | 25mm |
| MEP | MEP | 25mm |

**Resolution Priority**:
1. Structural (cannot move)
2. Architectural (hard to move)
3. MEP (easiest to reroute)
