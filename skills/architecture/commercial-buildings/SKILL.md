---
name: commercial-buildings
description: 商业建筑设计规范和最佳实践（商店、商场、餐厅）
version: 1.0.0
category: architecture
tags: [commercial, retail, mall, restaurant, design]
---

# 商业建筑设计技能

本技能涵盖商业建筑（商店、商场、餐厅）的设计规范、最佳实践和验证规则。

## 适用建筑类型

- **零售商店** (Retail Shops)
- **购物中心** (Shopping Malls)
- **餐厅/餐饮** (Restaurants)
- **超市** (Supermarkets)
- **商业综合体** (Commercial Complexes)

## 建筑规范

### 中国标准

#### GB 50352-2019 民用建筑设计统一标准

**层高要求：**
- 商业营业厅：≥ 4.5m（净高 ≥ 3.0m）
- 超市：≥ 4.2m（净高 ≥ 2.8m）
- 餐厅：≥ 3.6m（净高 ≥ 2.6m）
- 商店后台：≥ 2.8m（净高 ≥ 2.4m）

**疏散宽度：**
- 商店营业厅：疏散人数 × 0.85m/100人
- 地上一层：0.65m/100人
- 地上二层：0.75m/100人
- 地上三层及以上：0.85m/100人
- 地下层：1.00m/100人

**疏散距离：**
- 一、二级耐火等级：40m（有喷淋可增至 50m）
- 三级耐火等级：30m
- 四级耐火等级：25m

#### GB 50016-2014 建筑设计防火规范（商业部分）

**防火分区面积：**
- 地上商业：
  - 一、二级耐火：2500㎡（有喷淋可翻倍至 5000㎡）
  - 三级耐火：1200㎡
- 地下商业：
  - 500㎡（有喷淋可翻倍至 1000㎡）
  - 总建筑面积 > 20000㎡ 时，必须采用防火墙分隔

**安全出口：**
- 每个防火分区：≥ 2 个安全出口
- 建筑面积 ≤ 50㎡：可设 1 个
- 疏散门净宽：≥ 1.4m（主要出口）

#### GB 50763-2012 无障碍设计规范

**商业建筑无障碍要求：**
- 入口：至少 1 个无障碍入口
- 通道宽度：≥ 1.5m
- 坡道坡度：≤ 1:12
- 无障碍卫生间：每层至少 1 间
- 电梯：≥ 1 部无障碍电梯

### 国际标准

#### IBC (International Building Code)

**Occupant Load Factor (商业):**
- Retail (ground floor): 30 sq ft/person (2.79 ㎡/人)
- Retail (upper floors): 60 sq ft/person (5.57 ㎡/人)
- Mall (covered): 30 sq ft/person
- Restaurant (dining): 15 sq ft/person (1.39 ㎡/人)
- Restaurant (kitchen): 100 sq ft/person (9.29 ㎡/人)

**Egress Width:**
- 0.2 inches per occupant (stairs)
- 0.15 inches per occupant (other egress)

## 设计模式

### 1. 零售商店布局模式

#### 模式 1.1: 线性动线 (Linear Flow)
```
入口 → 主通道 → 商品区 → 收银台 → 出口
```

**适用场景：** 小型专卖店、便利店
**优点：** 动线清晰，顾客容易导航
**缺点：** 灵活性低

**验证规则：**
```
IF store_area < 200 sqm:
    REQUIRE: 主通道宽度 ≥ 2.0m
    REQUIRE: 次通道宽度 ≥ 1.2m
```

#### 模式 1.2: 环形动线 (Loop Flow)
```
入口 → 环形主通道 → 各商品区 → 返回入口 → 收银台
```

**适用场景：** 中型商店、超市
**优点：** 顾客可浏览所有商品
**缺点：** 需要较大面积

**验证规则：**
```
IF store_area > 200 sqm AND store_area < 2000 sqm:
    REQUIRE: 环形通道宽度 ≥ 2.5m
    REQUIRE: 商品岛之间通道 ≥ 1.8m
```

#### 模式 1.3: 自由流动 (Free Flow)
```
入口 → 开放式布局 → 多个商品岛 → 收银台分散
```

**适用场景：** 大型商场、百货
**优点：** 灵活性高，可创造探索感
**缺点：** 顾客可能迷路

**验证规则：**
```
IF store_area > 2000 sqm:
    REQUIRE: 主通道宽度 ≥ 3.0m
    REQUIRE: 次通道宽度 ≥ 2.0m
    REQUIRE: 视线通透（从入口可见主要区域）
```

### 2. 购物中心布局模式

#### 模式 2.1: 哑铃形布局 (Dumbbell Layout)
```
主力店A ←→ 商业街 ←→ 主力店B
```

**适用场景：** 中型购物中心
**优点：** 两个主力店互相引流
**验证规则：**
```
REQUIRE: 商业街宽度 ≥ 8m
REQUIRE: 商业街长度 ≤ 300m（避免疲劳）
REQUIRE: 主力店面积 ≥ 商业街总面积的 40%
```

#### 模式 2.2: 环形布局 (Loop Layout)
```
    主力店A
   ↗        ↘
商业街       商业街
   ↖        ↙
    主力店B
```

**适用场景：** 大型购物中心
**优点：** 均匀分布客流
**验证规则：**
```
REQUIRE: 环形通道宽度 ≥ 10m
REQUIRE: 中庭面积 ≥ 500㎡
REQUIRE: 每 100m 设休息区
```

#### 模式 2.3: 网格布局 (Grid Layout)
```
商业街1
  ↓
商业街2
  ↓
商业街3
```

**适用场景：** 超大型购物中心
**优点：** 可扩展性强
**验证规则：**
```
REQUIRE: 商业街间距 ≤ 80m
REQUIRE: 每条商业街宽度 ≥ 8m
REQUIRE: 交叉节点设中庭或广场
```

### 3. 餐厅布局模式

#### 模式 3.1: 传统餐厅 (Traditional Restaurant)
```
入口 → 等候区 → 就餐区 → 厨房 → 后勤区
```

**面积分配：**
- 就餐区：60-70%
- 厨房：20-25%
- 后勤/储藏：5-10%
- 入口/等候：5%

**验证规则：**
```
REQUIRE: 就餐区人均面积 ≥ 1.5㎡
REQUIRE: 厨房面积 ≥ 就餐区面积的 30%
REQUIRE: 厨房与就餐区间设缓冲区
REQUIRE: 后勤通道独立，不穿越就餐区
```

#### 模式 3.2: 快餐店 (Fast Food)
```
入口 → 点餐区 → 取餐区 → 就餐区 → 回收区
```

**面积分配：**
- 就餐区：50-60%
- 厨房/备餐：30-35%
- 点餐/取餐：10-15%

**验证规则：**
```
REQUIRE: 就餐区人均面积 ≥ 1.2㎡
REQUIRE: 点餐队列空间 ≥ 10㎡
REQUIRE: 座位周转率高（硬座椅）
```

#### 模式 3.3: 美食广场 (Food Court)
```
中央就餐区 ← 多个餐饮档口环绕
```

**面积分配：**
- 中央就餐区：50%
- 餐饮档口：35%
- 公共通道：15%

**验证规则：**
```
REQUIRE: 中央就餐区面积 ≥ 300㎡
REQUIRE: 每个档口面积 20-40㎡
REQUIRE: 档口数量 8-15 个
REQUIRE: 公共餐具回收区
```

## 优化策略

### 1. 客流优化

**目标：** 最大化顾客流动，提高商品曝光率

**策略：**
```python
def optimize_customer_flow(layout):
    # 1. 入口位置优化
    if store_area > 500:
        require_entrance_count(2)  # 至少2个入口
    
    # 2. 主通道宽度
    main_aisle_width = calculate_optimal_aisle_width(
        expected_customers=layout.expected_daily_customers,
        peak_hour_ratio=0.15  # 15% 客流集中在高峰小时
    )
    
    # 3. 商品布局
    high_margin_products = place_near_entrance()
    daily_necessities = place_at_back()  # 引导顾客深入
    impulse_items = place_near_checkout()
    
    return optimized_layout
```

**验证指标：**
- 客流密度：≤ 0.5 人/㎡（舒适）
- 通道利用率：60-80%（过高会拥堵）
- 死角率：< 10%（几乎无死角）

### 2. 能效优化

**目标：** 降低能耗，提高舒适度

**策略：**
```python
def optimize_energy_efficiency(building):
    # 1. 自然采光
    if orientation in ['south', 'north']:
        maximize_skylight_area(ratio=0.15)  # 天窗面积占屋顶 15%
    
    # 2. HVAC 分区
    zone_by_function()  # 按功能分区控制
    zone_by_orientation()  # 按朝向分区
    
    # 3. 照明控制
    daylight_sensors()  # 自然光传感器
    occupancy_sensors()  # 人体感应
    
    return energy_model
```

**验证指标：**
- 照明功率密度：≤ 12 W/㎡（商店）
- 空调能耗：≤ 150 kWh/㎡·年
- 自然采光系数：≥ 2%（主要区域）

### 3. 消防安全优化

**目标：** 确保快速疏散，符合消防规范

**策略：**
```python
def optimize_fire_safety(floor_plan):
    # 1. 疏散距离
    max_travel_distance = 40  # 米
    ensure_all_points_within_distance(max_travel_distance)
    
    # 2. 疏散宽度
    occupant_load = calculate_occupant_load(floor_plan)
    required_exit_width = occupant_load * 0.85 / 100  # 米
    ensure_exit_width(required_exit_width)
    
    # 3. 防火分区
    if floor_area > 2500:
        divide_into_fire_compartments(max_size=2500)
    
    return fire_safety_plan
```

**验证指标：**
- 疏散时间：≤ 5 分钟
- 疏散宽度：符合规范要求
- 防火分区：≤ 2500㎡（地上）

## 验证规则

### 商业建筑验证清单

```python
def validate_commercial_building(model_data, building_type):
    issues = []
    
    # 1. 层高验证
    if building_type == 'retail':
        min_height = 4.5 if is_sales_area() else 2.8
    elif building_type == 'restaurant':
        min_height = 3.6 if is_dining_area() else 2.6
    elif building_type == 'supermarket':
        min_height = 4.2
    
    if ceiling_height < min_height:
        issues.append(ValidationIssue(
            category="Building Code",
            severity=Severity.ERROR,
            message=f"层高 {ceiling_height:.2f}m 低于最小值 {min_height}m",
            suggestion=f"增加层高至至少 {min_height}m"
        ))
    
    # 2. 疏散宽度验证
    occupant_load = calculate_occupant_load(model_data)
    required_width = occupant_load * width_factor / 100
    if exit_width < required_width:
        issues.append(ValidationIssue(
            category="Fire Safety",
            severity=Severity.ERROR,
            message=f"疏散宽度 {exit_width:.2f}m 不足，需要 {required_width:.2f}m",
            suggestion=f"增加疏散门或加宽现有门"
        ))
    
    # 3. 无障碍验证
    if not has_accessible_entrance():
        issues.append(ValidationIssue(
            category="Accessibility",
            severity=Severity.ERROR,
            message="缺少无障碍入口",
            suggestion="至少设置1个无障碍入口"
        ))
    
    # 4. 防火分区验证
    if floor_area > 2500 and not has_fire_compartment():
        issues.append(ValidationIssue(
            category="Fire Safety",
            severity=Severity.ERROR,
            message=f"楼层面积 {floor_area}㎡ 超过防火分区限制 2500㎡",
            suggestion="设置防火墙分隔为多个防火分区"
        ))
    
    # 5. 卫生间验证
    required_toilets = calculate_required_toilets(occupant_load)
    if actual_toilets < required_toilets:
        issues.append(ValidationIssue(
            category="Building Code",
            severity=Severity.WARNING,
            message=f"卫生间数量 {actual_toilets} 不足，建议 {required_toilets}",
            suggestion=f"增加 {required_toilets - actual_toilets} 个卫生间"
        ))
    
    return issues
```

## 参考资源

### 中国规范
- GB 50352-2019 民用建筑设计统一标准
- GB 50016-2014 建筑设计防火规范
- GB 50763-2012 无障碍设计规范
- GB 50034-2013 建筑照明设计标准

### 国际标准
- IBC (International Building Code)
- NFPA 101 Life Safety Code
- ASHRAE 90.1 Energy Standard
- ADA (Americans with Disabilities Act)

### 设计指南
- 《商店建筑设计规范》JGJ 48-2014
- 《饮食建筑设计规范》JGJ 64-2017
- 《购物中心设计规范》（行业指南）

## 更新日志

- **2024-01-15**: 初始版本，包含零售、商场、餐厅设计规范
- **待添加**: 超市、商业综合体专项设计
