---
name: structural-analysis
description: Structural engineering rules for residential architecture. Load calculations, span limits, column/beam sizing, and structural validation checks.
version: 1.0.0
metadata:
  hermes:
    tags: [architecture, structural, engineering, validation]
---

# Structural Analysis for Residential Architecture

## Load Types

### Dead Loads (恒载)
- **Concrete slab (150mm)**: 3.75 kN/㎡
- **Floor finish (tiles + mortar)**: 1.20 kN/㎡
- **Partition wall (200mm brick)**: 4.20 kN/m (per meter height)
- **Self-weight of beam (250×500mm)**: 3.13 kN/m

### Live Loads (活载) - GB 50009
| Use | Load (kN/㎡) |
|-----|-------------|
| Residential rooms | 2.0 |
| Kitchen | 2.0 |
| Bathroom | 2.5 |
| Balcony | 2.5 |
| Stairs/corridors | 3.5 |
| Roof (accessible) | 2.0 |
| Roof (inaccessible) | 0.5 |

### Wind Load (风载)
- Basic wind pressure: 0.35-0.75 kN/㎡ (varies by region)
- Height factor: increases with building height
- Shape factor: depends on building geometry

### Seismic Load (地震作用)
- Design intensity: 6-9度 (China seismic zones)
- Site class: I-IV (soil conditions)
- Damping ratio: 0.05 (concrete structures)

## Span Limits (跨度限制)

### Concrete Slabs
| Type | Max Span (m) | Min Thickness (mm) |
|------|-------------|-------------------|
| One-way slab | 4.0 | L/30 (≥100mm) |
| Two-way slab | 6.0 | L/40 (≥100mm) |
| Ribbed slab | 8.0 | 80mm (rib 200mm) |
| Waffle slab | 12.0 | 100mm (rib 300mm) |

### Beams
| Type | Max Span (m) | Depth/Span Ratio |
|------|-------------|------------------|
| Simply supported | 8.0 | 1/12 |
| Continuous | 10.0 | 1/15 |
| Cantilever | 3.0 | 1/6 |

### Columns
| Type | Min Size (mm) | Max Load (kN) |
|------|--------------|---------------|
| Residential column | 300×300 | 2000 |
| Corner column | 350×350 | 2500 |
| Core column | 400×400 | 3500 |

## Structural Validation Rules

### Rule 1: Slab Thickness Check
```
IF span > 4.0m AND thickness < span/30:
    WARNING: Slab too thin for span
    SUGGEST: Increase thickness to {span/30}mm
```

### Rule 2: Beam Depth Check
```
IF span > 6.0m AND depth < span/12:
    WARNING: Beam too shallow for span
    SUGGEST: Increase depth to {span/12}mm
```

### Rule 3: Column Load Check
```
IF axial_load > 0.6 × f_c × A_g:
    WARNING: Column overloaded
    SUGGEST: Increase column size to {next_size}mm
```

### Rule 4: Cantilever Limit
```
IF cantilever_length > 2.0m:
    WARNING: Cantilever exceeds recommended limit
    SUGGEST: Add support or reduce to 2.0m
```

### Rule 5: Opening in Load-Bearing Wall
```
IF opening_width > 1.5m AND wall_type == "load_bearing":
    WARNING: Large opening in load-bearing wall
    REQUIRE: Lintel beam (depth ≥ span/12)
```

## Quick Sizing Guide

### For 3m × 4m Room (Typical Bedroom)
- **Slab**: 120mm thick (one-way)
- **Beams**: 250×400mm (perimeter)
- **Columns**: 300×300mm (corners)
- **Load per column**: ~150 kN

### For 5m × 6m Room (Living Room)
- **Slab**: 150mm thick (two-way)
- **Beams**: 300×500mm (perimeter)
- **Columns**: 350×350mm (corners)
- **Load per column**: ~300 kN

### For 8m × 10m Open Space
- **Slab**: 200mm thick (waffle) OR add intermediate beams
- **Main beams**: 400×700mm (8m span)
- **Secondary beams**: 300×500mm (5m span)
- **Columns**: 500×500mm (corners), 450×450mm (interior)

## Deflection Limits (挠度限制)

| Element | Limit | Example (6m span) |
|---------|-------|-------------------|
| Floor beam | L/250 | 24mm max |
| Roof beam | L/200 | 30mm max |
| Cantilever | L/100 | 20mm (2m span) |
| Slab | L/250 | 24mm max |

## Foundation Types

| Type | Soil Condition | Max Load (kN/m²) |
|------|---------------|------------------|
| Strip footing | Good soil | 150-200 |
| Raft foundation | Poor soil | 100-150 |
| Pile foundation | Very poor soil | 500-1000 per pile |

## Common Structural Issues

### Issue 1: Long Span Without Support
**Problem**: 8m+ spans cause excessive deflection
**Solution**: Add intermediate beam or use deeper section

### Issue 2: Soft Story (薄弱层)
**Problem**: Ground floor with large openings (parking, lobby)
**Solution**: Increase column size, add shear walls

### Issue 3: Torsion (扭转)
**Problem**: Asymmetric mass/stiffness distribution
**Solution**: Symmetrize layout or add lateral bracing

### Issue 4: Short Column (短柱)
**Problem**: Column height/width ratio < 4
**Solution**: Increase height or add confinement reinforcement
