---
name: design-optimization
description: Optimization strategies for residential design. Covers space efficiency, cost optimization, energy performance, and multi-objective trade-offs.
version: 1.0.0
metadata:
  hermes:
    tags: [architecture, optimization, efficiency, cost, energy]
---

# Design Optimization for Residential Architecture

## 1. Space Efficiency Optimization

### Metric 1.1: Circulation Ratio (交通面积比)

**Definition**: Corridor + stair area / Total floor area

**Benchmarks**:
| Quality | Ratio | Description |
|---------|-------|-------------|
| Excellent | < 10% | Minimal corridors, open plan |
| Good | 10-15% | Efficient layout |
| Acceptable | 15-20% | Standard residential |
| Poor | > 20% | Wasted circulation space |

**Optimization Strategies**:
```
IF circulation_ratio > 20%:
    TRY:
    1. Convert corridor to multi-use (gallery, storage)
    2. Eliminate corridor by direct room access
    3. Combine adjacent corridors
    4. Use open plan for living/dining
```

**Example Optimization**:
```
BEFORE:
Living (20㎡) + Corridor (8㎡) + Dining (12㎡) = 40㎡
Circulation ratio: 8/40 = 20%

AFTER:
Living-Dining open plan (32㎡) = 32㎡
Circulation ratio: 0/32 = 0%
Space saved: 8㎡ (20%)
```

### Metric 1.2: Net-to-Gross Ratio (使用面积系数)

**Definition**: Net usable area / Gross floor area

**Benchmarks**:
| Type | Target Ratio |
|------|-------------|
| High-rise residential | ≥ 75% |
| Multi-story residential | ≥ 80% |
| Villa/townhouse | ≥ 85% |

**Optimization**:
```
IF net_to_gross < target:
    ANALYZE:
    - Wall thickness (reduce from 240mm to 200mm)
    - Structural efficiency (fewer columns)
    - Shaft size (compact MEP)
    - Balcony ratio (not counted in net area)
```

## 2. Cost Optimization

### Metric 2.1: Cost per Square Meter (单方造价)

**Residential Benchmarks (China, 2024)**:
| Standard | Cost (RMB/㎡) | Description |
|----------|--------------|-------------|
| Basic | 2,000-3,000 | Standard finishes |
| Mid-range | 3,000-5,000 | Better materials |
| High-end | 5,000-8,000 | Premium finishes |
| Luxury | > 8,000 | Custom design |

**Cost Drivers**:
| Element | % of Total | Optimization |
|---------|-----------|--------------|
| Structure | 25-30% | Optimize spans, reduce concrete |
| Envelope | 15-20% | Standardize windows, simplify facade |
| MEP | 20-25% | Efficient routing, standard fixtures |
| Finishes | 20-25% | Material selection, standard sizes |
| Site work | 5-10% | Minimize excavation, grading |

### Metric 2.2: Structural Efficiency Index

**Definition**: Structural cost / Floor area

**Optimization Strategies**:
```
1. Optimize grid (regular spacing = cheaper)
   IF column_spacing varies > 1.0m:
       SUGGEST: Regularize to 3.6m or 4.2m grid

2. Reduce spans (shorter = cheaper)
   IF max_span > 6.0m:
       SUGGEST: Add intermediate beam or reduce to 4.8m

3. Standardize elements
   IF unique_beam_types > 5:
       SUGGEST: Consolidate to 3 standard sizes

4. Optimize foundation
   IF soil_bearing > 200 kPa:
       SUGGEST: Use strip footing instead of raft
```

### Metric 2.3: Material Optimization

**Concrete Optimization**:
```
Slab thickness optimization:
  FOR each room:
    required_thickness = span / 30  # one-way
    required_thickness = span / 40  # two-way
    
    IF current_thickness > required_thickness × 1.2:
        SUGGEST: Reduce to {required_thickness}mm
        Savings: {volume_difference} cubic meters
```

**Rebar Optimization**:
```
Typical reinforcement ratios:
- Slab: 0.5-1.0%
- Beam: 1.0-2.0%
- Column: 1.5-3.0%

IF calculated_ratio < 0.8 × minimum:
    WARNING: Under-reinforced (ductile failure OK, but check deflection)
    
IF calculated_ratio > 2.5 × minimum:
    WARNING: Over-reinforced (brittle failure risk)
    SUGGEST: Increase section size or use higher grade concrete
```

## 3. Energy Optimization

### Metric 3.1: Energy Use Intensity (EUI)

**Definition**: Annual energy consumption / Floor area (kWh/㎡·year)

**Benchmarks (China)**:
| Climate Zone | Target EUI |
|--------------|-----------|
| Severe cold | 40-50 kWh/㎡ |
| Cold | 35-45 kWh/㎡ |
| Hot summer/cold winter | 45-55 kWh/㎡ |
| Hot summer/warm winter | 50-60 kWh/㎡ |

### Metric 3.2: Passive Design Strategies

**Strategy 1: Building Orientation**
```
Optimal orientation for energy:
- Long axis: East-West (maximize south facade)
- Window-to-wall ratio:
  * North: 30% (minimize heat loss)
  * South: 50% (maximize solar gain)
  * East/West: 30% (avoid overheating)

IF building_aspect_ratio < 1.5:
    SUGGEST: Elongate east-west axis
    Energy savings: 5-10%
```

**Strategy 2: Thermal Mass**
```
Thermal mass optimization:
- Expose concrete slab in living areas (daytime heat storage)
- Use masonry walls in south-facing rooms
- Insulate exterior of thermal mass (not interior)

IF thermal_mass_ratio < 0.3:
    SUGGEST: Increase exposed mass surfaces
    Benefit: Reduce temperature swing by 3-5°C
```

**Strategy 3: Natural Ventilation**
```
Cross-ventilation optimization:
FOR each room:
  inlet_area = sum(windows on windward side)
  outlet_area = sum(windows on leeward side)
  
  IF min(inlet_area, outlet_area) < 0.05 × floor_area:
      WARNING: Insufficient ventilation
      SUGGEST: Increase opening to {0.05 × floor_area}㎡
  
  IF inlet_area / outlet_area > 2.0 OR < 0.5:
      WARNING: Unbalanced ventilation
      SUGGEST: Balance openings (ratio 1.0-1.5)
```

**Strategy 4: Shading**
```
Shading optimization:
FOR each south-facing window:
  shading_depth = window_height × 0.6  # blocks summer sun
  
  IF no_shading_device:
      SUGGEST: Add horizontal overhang {shading_depth}m deep
      Energy savings: 10-15% cooling load
  
FOR each west-facing window:
  IF no_shading_device:
      SUGGEST: Add vertical fins or vegetation
      Energy savings: 15-20% cooling load
```

### Metric 3.3: Daylight Autonomy

**Definition**: % of occupied hours with sufficient daylight (≥300 lux)

**Targets**:
| Space | Target DA |
|-------|-----------|
| Living room | ≥ 60% |
| Bedroom | ≥ 50% |
| Kitchen | ≥ 50% |
| Office | ≥ 70% |

**Optimization**:
```
FOR each room:
  daylight_factor = (window_area × 0.8 × 0.3) / floor_area
  
  IF daylight_factor < 0.02:
      SUGGEST: Increase window area by {required_increase}㎡
      OR: Add skylight (2× more effective than vertical window)
      OR: Use light shelf to redirect light deeper
```

## 4. Multi-Objective Optimization

### Trade-off Matrix

| Objective | Conflicts With | Synergies |
|-----------|---------------|-----------|
| **Space efficiency** | Circulation, privacy | Cost, energy |
| **Cost reduction** | Quality, flexibility | Space efficiency |
| **Energy performance** | Glazing area, views | Thermal comfort |
| **Natural light** | Heat gain, privacy | Wellbeing, energy |
| **Structural efficiency** | Architectural freedom | Cost, constructability |

### Pareto Optimization Approach

**Concept**: Find solutions where no objective can improve without worsening another

**Example Trade-offs**:
```
Option A: Maximize space
- Net-to-gross: 85%
- Circulation: 8%
- Cost: +5% (complex layout)
- Energy: -10% (poor orientation)

Option B: Balance
- Net-to-gross: 80%
- Circulation: 12%
- Cost: Baseline
- Energy: Baseline

Option C: Maximize energy
- Net-to-gross: 78%
- Circulation: 14%
- Cost: +8% (better insulation, shading)
- Energy: -25% (optimized orientation)
```

**Decision Framework**:
```
IF client_priority == "cost":
    RECOMMEND: Option B (balance)
    
IF client_priority == "sustainability":
    RECOMMEND: Option C (energy)
    
IF client_priority == "space":
    RECOMMEND: Option A (efficiency)
    
DEFAULT: Option B (balanced approach)
```

## 5. Optimization Algorithms

### Algorithm 5.1: Grid Search (网格搜索)

**Use Case**: Small design space (< 100 options)

```python
best_score = -infinity
best_design = None

FOR column_spacing IN [3.0, 3.6, 4.2, 4.8]:
    FOR slab_thickness IN [120, 150, 180]:
        FOR orientation IN [0, 15, 30, 45]:
            design = generate(column_spacing, slab_thickness, orientation)
            score = evaluate(design)
            
            IF score > best_score:
                best_score = score
                best_design = design

RETURN best_design
```

### Algorithm 5.2: Gradient Descent (梯度下降)

**Use Case**: Continuous parameters, smooth objective function

```python
design = initial_design
learning_rate = 0.1

FOR iteration IN range(100):
    gradient = compute_gradient(design)
    design = design - learning_rate × gradient
    
    IF converged(gradient):
        BREAK

RETURN design
```

### Algorithm 5.3: Genetic Algorithm (遗传算法)

**Use Case**: Complex, multi-modal design space

```python
population = [random_design() for _ in range(50)]

FOR generation IN range(100):
    # Evaluate fitness
    fitness = [evaluate(d) for d in population]
    
    # Select parents (tournament)
    parents = tournament_select(population, fitness)
    
    # Crossover
    children = [crossover(p1, p2) for p1, p2 in parent_pairs]
    
    # Mutate
    children = [mutate(c, rate=0.05) for c in children]
    
    # Replace
    population = children

RETURN best(population)
```

## 6. Optimization Checklist

### Pre-Design Optimization
- [ ] Site orientation optimized (solar, wind, views)
- [ ] Building footprint minimized (compact form)
- [ ] Structural grid regularized (3.6m or 4.2m)
- [ ] Program adjacency optimized (bubble diagram)

### Schematic Design Optimization
- [ ] Circulation ratio < 15%
- [ ] Net-to-gross ratio > target
- [ ] Cross-ventilation achieved in all habitable rooms
- [ ] Daylight factor > minimum in all spaces

### Design Development Optimization
- [ ] Structural spans optimized (no excessive spans)
- [ ] MEP routing optimized (short, direct)
- [ ] Material quantities minimized
- [ ] Construction sequence optimized

### Construction Document Optimization
- [ ] Detail standardization (fewer unique details)
- [ ] Specification optimization (performance-based)
- [ ] Bid packaging optimized (trade coordination)
