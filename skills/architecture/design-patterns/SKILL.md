---
name: design-patterns
description: Common architectural design patterns for residential buildings. Covers spatial organization, circulation, privacy gradients, and functional zoning.
version: 1.0.0
metadata:
  hermes:
    tags: [architecture, design-patterns, residential, planning]
---

# Architectural Design Patterns for Residential Buildings

## 1. Spatial Organization Patterns

### Pattern 1.1: Public-Private Gradient (公私分区)

**Concept**: Arrange spaces from most public (entrance) to most private (bedrooms)

**Typical Sequence**:
```
Entry → Living/Dining → Kitchen → Corridor → Bedrooms
(most public)                              (most private)
```

**Application**:
- Ground floor: public spaces (living, dining, kitchen, guest bath)
- Upper floor: private spaces (bedrooms, master bath)
- Buffer zones: corridors, stairs, storage

**Validation Rule**:
```
IF bedroom_door visible from living_room:
    SUGGEST: Add corridor or vestibule for privacy
```

### Pattern 1.2: Functional Zoning (功能分区)

**Zones**:
| Zone | Spaces | Characteristics |
|------|--------|-----------------|
| **Social** | Living, dining, kitchen | Large, open, south-facing |
| **Private** | Bedrooms, bathrooms | Quiet, enclosed, away from entry |
| **Service** | Kitchen, laundry, storage | Efficient, near service entrance |
| **Circulation** | Corridors, stairs, entry | Minimal, efficient flow |

**Validation Rule**:
```
IF kitchen adjacent to bedroom WITHOUT buffer:
    WARNING: Noise/smell transfer likely
    SUGGEST: Add corridor or closet as buffer
```

### Pattern 1.3: Day-Night Separation (动静分区)

**Day Spaces**: Living, dining, kitchen, study (active hours)
**Night Spaces**: Bedrooms, bathrooms (sleep hours)

**Rule**: Minimize acoustic transmission between zones
- Separate by corridor or storage
- Avoid shared walls between living room and bedroom
- Use double-wall construction if unavoidable

## 2. Circulation Patterns

### Pattern 2.1: Hub-and-Spoke (中心辐射)

**Concept**: Central hub (living room) with spokes to other spaces

**Advantages**:
- Efficient circulation (short distances)
- Clear hierarchy
- Flexible expansion

**Disadvantages**:
- Hub becomes congested
- Limited privacy

**Typical Layout**:
```
        Bedroom 1
            |
Bedroom 2 - Living - Kitchen
            |
        Entry/Dining
```

### Pattern 2.2: Linear Sequence (线性序列)

**Concept**: Spaces arranged in a line, connected by corridor

**Advantages**:
- Clear progression
- Good for narrow sites
- Easy expansion

**Disadvantages**:
- Long corridors (wasted space)
- Poor cross-ventilation

**Typical Layout**:
```
Entry → Corridor → Living → Dining → Kitchen
          |
          └→ Bedrooms
```

### Pattern 2.3: Cluster (群组式)

**Concept**: Group related spaces together, connect clusters

**Example**:
```
┌─────────────┐    ┌─────────────┐
│ Living Zone │    │ Bedroom Zone│
│ - Living    │    │ - Master    │
│ - Dining    │◄──►│ - Bed 2     │
│ - Kitchen   │    │ - Bed 3     │
└─────────────┘    │ - Bath      │
                   └─────────────┘
```

## 3. Proportion & Scale Patterns

### Pattern 3.1: Golden Ratio (黄金比例)

**Ratio**: 1:1.618

**Applications**:
- Room proportions (3.0m × 4.85m)
- Window-to-wall ratio
- Building facade composition

**Example**:
```
Living room: 4.0m × 6.5m (ratio 1:1.625)
Master bedroom: 3.5m × 5.6m (ratio 1:1.6)
```

### Pattern 3.2: Modular Grid (模数网格)

**Basic Module**: 300mm (GB 50002-2013)

**Common Increments**:
| Element | Module (mm) |
|---------|-------------|
| Column spacing | 3000, 3600, 4200 |
| Room width | 2400, 2700, 3000, 3300, 3600 |
| Room depth | 3600, 4200, 4800, 5400, 6000 |
| Floor height | 2800, 3000, 3300, 3600 |

**Validation Rule**:
```
IF room_dimension % 300 != 0:
    SUGGEST: Round to nearest 300mm module
    Example: 4.15m → 4.2m or 3.9m
```

## 4. Environmental Patterns

### Pattern 4.1: Cross-Ventilation (穿堂风)

**Concept**: Openings on opposite walls for natural airflow

**Rules**:
- Window area ≥ 5% of floor area (each side)
- Opening height difference improves stack effect
- Avoid dead-end rooms (no cross-ventilation)

**Validation Rule**:
```
IF room has windows on ONLY ONE wall:
    WARNING: Poor ventilation
    SUGGEST: Add transom window or operable partition
```

### Pattern 4.2: Solar Orientation (日照朝向)

**China Climate Zones**:
| Zone | Winter Priority | Summer Priority |
|------|----------------|-----------------|
| Severe cold (严寒) | Maximize south glazing | Minimize west |
| Cold (寒冷) | South + east glazing | Shade west |
| Hot summer/cold winter | Balanced, shade south | Maximize ventilation |
| Hot summer/warm winter | Minimize all glazing | Maximize shading |

**Optimal Orientation**:
- **Living/Bedrooms**: South (±30°) for winter sun
- **Kitchen**: North or east (avoid afternoon heat)
- **Bathrooms**: North (privacy, consistent light)

**Validation Rule**:
```
IF bedroom facing WEST AND window_area > 2.0 sqm:
    WARNING: Afternoon heat gain
    SUGGEST: Reduce window or add external shading
```

### Pattern 4.3: Daylight Factor (采光系数)

**Minimum Daylight Factor (DF)**:
| Space | DF (%) |
|-------|--------|
| Living room | 2.0 |
| Bedroom | 1.5 |
| Kitchen | 2.0 |
| Bathroom | 1.0 |
| Corridor | 0.5 |

**Calculation**:
```
DF = (Window area × Transmittance × Sky component) / Floor area

Example:
- Room: 4m × 5m = 20 sqm
- Window: 2m × 1.5m = 3 sqm
- Transmittance: 0.8 (double glazing)
- Sky component: 0.3 (obstruction factor)
- DF = (3 × 0.8 × 0.3) / 20 = 3.6% ✓
```

## 5. Privacy Patterns

### Pattern 5.1: Acoustic Privacy Gradient

**STC Ratings (Sound Transmission Class)**:
| Partition | STC | Application |
|-----------|-----|-------------|
| 100mm brick + plaster | 45 | Interior walls |
| 200mm concrete | 55 | Between apartments |
| Double wall (staggered studs) | 60 | Recording studios |
| 150mm concrete + insulation | 65 | Hotel rooms |

**Rules**:
- Bedroom-to-bedroom: STC ≥ 45
- Bedroom-to-living: STC ≥ 50
- Bathroom-to-bedroom: STC ≥ 50
- Between units: STC ≥ 55

### Pattern 5.2: Visual Privacy

**Sight Line Analysis**:
```
FROM entry TO living_room: ACCEPTABLE (public)
FROM entry TO bedroom: UNACCEPTABLE
FROM living_room TO bathroom: UNACCEPTABLE
FROM kitchen TO dining: ACCEPTABLE (open plan)
```

**Mitigation**:
- Offset doorways (not directly opposite)
- Use frosted glass for bathroom windows
- Screen walls or vegetation for ground floor

## 6. Flexibility Patterns

### Pattern 6.1: Universal Design (通用设计)

**Principles**:
1. Equitable use (all users)
2. Flexibility in use (left/right handed)
3. Simple and intuitive
4. Perceptible information
5. Tolerance for error
6. Low physical effort
7. Size and space for approach/use

**Applications**:
- Door width ≥ 850mm (wheelchair)
- Corridor width ≥ 1200mm (wheelchair turning)
- Lever handles (not knobs)
- Non-slip flooring
- Contrasting colors for visibility

### Pattern 6.2: Adaptable Spaces (可变空间)

**Concept**: Design spaces that can change function over time

**Examples**:
- Study → Bedroom (add closet, larger window)
- Nursery → Child's room → Teen room (same footprint, different furniture)
- Home office → Guest room (sofa bed, fold-down desk)

**Design Strategy**:
- Use non-load-bearing partitions
- Pre-wire for multiple layouts
- Oversized electrical/plumbing capacity
