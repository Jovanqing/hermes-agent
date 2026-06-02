# Vibe Building — 技术设计文档

> **版本**: v0.2  
> **最后更新**: 2026-06-02  
> **状态**: 草案 (待审阅和修改)

---

## 1. 项目愿景

**"Vibe Coding" for Architecture** — 用户通过自然语言描述建筑意图，Claude Code 作为 AI 大脑协调多级流程，自动在 Revit 中创建和修改 BIM 模型。

### 核心理念

```
"建一个类似 Snowdon Towers 的 19 层塔楼，场地 50m x 50m"
                        │
                        ▼
            Claude Code (AI 大脑)
            ┌──────────────────────────┐
            │  需求分析 → 建筑设计     │
            │      ↓                   │
            │  结构设计 → 施工文档     │
            │      ↓                   │
            │  Revit 建模 → 验证优化   │
            └──────────────────────────┘
                        │
                        ▼
              Revit 中的完整建筑模型
```

---

## 2. 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户界面层                                   │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────┐  │
│  │  Web 聊天界面       │  │  Revit 内嵌面板     │  │  语音输入      │  │
│  │  (React + Vite)    │  │  (pyRevit WPF)     │  │  (可选)        │  │
│  └────────┬───────────┘  └────────┬───────────┘  └──────┬────────┘  │
│           │                       │                      │           │
│           └───────────────────────┼──────────────────────┘           │
│                                   │ 自然语言                          │
└───────────────────────────────────┼─────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR (Claude Code)                          │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  负责: 分解任务、协调各阶段、处理错误、迭代优化              │     │
│  └────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────┼─────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Stage 1-2    │  │  Stage 3-4    │  │  Stage 5-6    │
│  需求 + 设计   │  │  结构 + 文档   │  │  建模 + 验证   │
│  (Claude)     │  │  (Claude+工具) │  │  (Claude+工具) │
└───────────────┘  └───────────────┘  └───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Revit API (pyRevit Routes)                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐  │
│  │ /walls       │ │ /floors      │ │ /columns     │ │ /beams   │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 角色分工

```
Claude Code (我) = 大脑
├── 理解用户意图
├── 生成设计方案
├── 做出决策（结构体系、布局等）
├── 调用工具执行
├── 解释结果
└── 迭代优化

工具 = 手和脚
├── Revit API → 创建建筑元素
├── ETABS/SAP2000 → 结构计算
├── 文档生成器 → 生成 PDF/DWG
└── 碰撞检测器 → 检测碰撞
```

---

## 3. 六级流水线详细设计

### Stage 1: 需求分析

**Claude Code 角色**: ✅ 核心（理解 + 决策）  
**工具需求**: 部分（PDF 解析器可选）

#### 输入
```
用户: "建一个类似 Snowdon Towers 的 19 层塔楼，场地 50m x 50m"
参考图纸: Snowdon Towers Sample Structural.rvt (如果有 PDF 配套)
```

#### Claude Code 处理流程
```python
# 1. 解析用户自然语言意图
user_input = "建一个类似 Snowdon Towers 的 19 层塔楼"
→ 提取: floors=19, building_type="tower", reference="Snowdon Towers"

# 2. 解析参考图纸 (如果有 PDF)
pdf_parser.parse("snowdon_towers.pdf")
→ 提取: 楼层布局、建筑外观、结构体系

# 3. 查询建筑规范
norm_db.query("GB 50009", building_type="tower", floors=19)
→ 返回: 荷载要求、抗震要求、防火要求

# 4. 分析约束条件
constraints = {
    "site": {"width": 50, "depth": 50},
    "floors": 19,
    "building_type": "tower",
    "reference": "Snowdon Towers"
}
```

#### 输出
```python
requirements = {
    "building_type": "tower",
    "floors": 19,
    "site": {"width": 50, "depth": 50},
    "norms": ["GB 50009", "GB 50010", "GB 50011"],
    "constraints": {
        "max_height": 60,       # 米
        "floor_area": 2500,     # 每层面积 (㎡)
        "structural_system": "frame-shear_wall"
    }
}
```

---

### Stage 2: 建筑设计生成

**Claude Code 角色**: ✅ 核心（生成 + 决策）  
**工具需求**: 部分（规范检查器）

#### 输入
Stage 1 输出的 `requirements`

#### Claude Code 处理流程
```python
# 1. 生成每层楼的平面布局
for floor in range(19):
    floor_plan = claude.generate_floor_plan(
        floor_number=floor,
        constraints=requirements["constraints"],
        norms=requirements["norms"]
    )
    → 生成: 每层楼的房间布局、面积、功能

# 2. 生成建筑立面
elevation = claude.generate_elevation(
    building_type="tower",
    floors=19,
    style="modern"
)

# 3. 生成门窗表
door_schedule = claude.generate_door_schedule()
window_schedule = claude.generate_window_schedule()

# 4. 验证规范合规性
violations = norm_checker.check(floor_plans, requirements["norms"])
if violations:
    → 迭代优化
```

#### 输出
```python
architectural_design = {
    "floor_plans": [
        {
            "floor": 1,
            "rooms": [
                {"name": "大堂", "area": 200, "function": "lobby"},
                {"name": "餐厅", "area": 150, "function": "dining"},
                {"name": "会议室", "area": 100, "function": "meeting"}
            ]
        },
        # ... 19 层
    ],
    "elevation": {...},
    "door_schedule": {...},
    "window_schedule": {...},
    "areas": {...},
    "norms_compliance": True
}
```

---

### Stage 3: 结构设计生成

**Claude Code 角色**: ✅ 助手（选择 + 解释）  
**工具需求**: ✅ 是（ETABS/SAP2000）

#### 输入
Stage 2 输出的 `architectural_design`

#### Claude Code 处理流程
```python
# 1. 选择结构体系
structural_system = claude.select_system(
    building_type="tower",
    floors=19,
    norms=requirements["norms"]
)
→ Claude 决策: "选择框架-剪力墙体系，因为 19 层需要抗侧力"

# 2. 荷载计算
loads = claude.calculate_loads(
    architectural_design,
    norms=requirements["norms"]
)
→ 计算: 恒载、活载、风载、地震作用

# 3. 结构计算 (调用 ETABS/SAP2000)
structural_model = etabs.create_model(
    architectural_design,
    structural_system,
    loads
)

# 4. 构件尺寸计算
member_sizes = etabs.calculate_members(
    structural_model,
    loads
)
→ 计算: 梁截面、柱截面、板厚

# 5. 验证结构安全
safety_check = etabs.verify_safety(structural_model)
if not safety_check.safe:
    → 迭代优化
```

#### 输出
```python
structural_design = {
    "structural_system": "frame-shear_wall",
    "members": {
        "beams": [
            {"position": (0, 0, 0), "size": "300x600", "level": 1}
        ],
        "columns": [
            {"position": (0, 0), "size": "600x600", "level": 1}
        ],
        "slabs": [
            {"position": (0, 0), "thickness": 200, "level": 1}
        ],
        "shear_walls": [...]
    },
    "loads": {...},
    "safety_check": {...}
}
```

---

### Stage 4: 施工文档生成

**Claude Code 角色**: ✅ 助手（生成 + 解释）  
**工具需求**: ✅ 部分是（文档生成器, BOM 生成器）

#### 输入
Stage 3 输出的 `structural_design`

#### Claude Code 处理流程
```python
# 1. 生成施工说明
construction_notes = claude.generate_notes(structural_design)
→ 生成: "1. 先施工基础，2. 施工柱子，3. 施工梁板..."

# 2. 生成材料清单 (BOM)
bom = bom_generator.generate(structural_design)
→ 生成: "需要 C40 混凝土 500m³，HRB400 钢筋 200t"

# 3. 生成施工顺序
construction_sequence = claude.generate_sequence(
    structural_design
)

# 4. 生成质量检查点
quality_checks = claude.generate_quality_checks(
    structural_design
)
```

#### 输出
```python
construction_docs = {
    "drawings": {
        "floor_plans": [...],
        "structural_details": [...],
        "connections": [...]
    },
    "bom": {
        "concrete": {"grade": "C40", "volume": 500, "unit": "m³"},
        "rebar": {"grade": "HRB400", "weight": 200, "unit": "t"}
    },
    "sequence": [
        "1. 施工基础",
        "2. 施工柱子",
        "3. 施工梁板"
    ],
    "quality_checks": [...]
}
```

---

### Stage 5: Revit 建模

**Claude Code 角色**: ✅ 监控器（生成序列 + 解释错误）  
**工具需求**: ✅ 是（Revit API）

#### 输入
所有前序阶段的输出

#### Claude Code 处理流程
```python
# 1. 生成建模序列
modeling_sequence = claude.generate_sequence(
    architectural_design,
    structural_design
)
→ 生成: "1. 创建楼层，2. 创建柱子，3. 创建梁，4. 创建板"

# 2. 创建楼层
for floor in architectural_design["floor_plans"]:
    revit_api.create_level(
        name=floor["name"],
        elevation=floor["elevation"]
    )

# 3. 创建结构
for column in structural_design["members"]["columns"]:
    revit_api.create_column(
        position=column["position"],
        size=column["size"],
        level=column["level"]
    )

for beam in structural_design["members"]["beams"]:
    revit_api.create_beam(...)

# 4. 创建建筑元素
for wall in architectural_design["walls"]:
    revit_api.create_wall(...)

for door in architectural_design["door_schedule"]:
    revit_api.create_door(...)
```

#### 输出
```
Revit 模型已创建:
- 19 层楼层
- 200+ 根柱子
- 500+ 根梁
- 19 块楼板
- 100+ 面墙
- 50+ 扇门
- 100+ 扇窗
```

---

### Stage 6: 验证和优化

**Claude Code 角色**: ✅ 监控器（解释 + 优化）  
**工具需求**: ✅ 是（碰撞检测器, 规范验证器）

#### 输入
Revit 模型

#### Claude Code 处理流程
```python
# 1. 碰撞检测
clashes = clash_detector.detect(revit_model)
if clashes:
    → Claude 解释: "发现 3 处碰撞：1. 梁与管道，2. 柱与管道..."
    → 修复并重新建模

# 2. 规范验证
violations = norm_checker.check(revit_model, norms)
if violations:
    → Claude 解释: "餐厅面积 150㎡ 不符合规范，需要 ≥ 200㎡"
    → 修复并重新建模

# 3. 优化建议
optimizations = optimizer.suggest(revit_model)
→ Claude 建议: "可以减少 3 根柱子，节省材料 10%"

# 4. 生成报告
report = verifier.generate_report(revit_model)
```

#### 输出
```python
verification_report = {
    "clashes": [],
    "norm_violations": [],
    "optimizations": [
        {"type": "material", "suggestion": "减少 3 根柱子", "savings": "10%"}
    ],
    "overall_score": 95/100,
    "grade": "A"
}
```

---

## 4. 工具需求汇总

### 按 Stage 分类

| Stage | 工具需求 | Claude Code 角色 | 关键工具 |
|-------|---------|-----------------|---------|
| **Stage 1** | 部分 | ✅ 核心 | PDF 解析器, 规范数据库 |
| **Stage 2** | 部分 | ✅ 核心 | 规范检查器 |
| **Stage 3** | ✅ 是 | ✅ 助手 | ETABS/SAP2000 |
| **Stage 4** | 部分是 | ✅ 助手 | 文档生成器, BOM 生成器 |
| **Stage 5** | ✅ 是 | ✅ 监控器 | Revit API |
| **Stage 6** | ✅ 是 | ✅ 监控器 | 碰撞检测器, 规范验证器 |

### 工具清单

#### 已有工具
- ✅ Revit API (pyRevit Routes) — 创建建筑元素
- ✅ Claude Code — 理解、决策、解释、优化

#### 需要开发的工具
- ⚠️ ETABS/SAP2000 集成 — 结构计算
- ⚠️ 文档生成器 — 生成 PDF/DWG
- ⚠️ BOM 生成器 — 生成材料清单
- ⚠️ 碰撞检测器 — 检测碰撞
- ⚠️ 规范验证器 — 验证规范合规性

---

## 5. 当前状态评估

### 已有能力

| 能力 | 状态 | 说明 |
|------|------|------|
| **Revit API** | ✅ 可用 | 可以创建墙、楼板、房间 |
| **Claude Code** | ✅ 可用 | 可以理解意图、生成设计 |
| **Stage 1: 需求分析** | ✅ 可用 | 只需要 Claude Code |
| **Stage 2: 建筑设计** | ✅ 可用 | 只需要 Claude Code |
| **Stage 5: Revit 建模** | ⚠️ 部分可用 | 有 API，但功能有限 |

### 缺失能力

| 能力 | 状态 | 需要什么 |
|------|------|---------|
| **Stage 3: 结构设计** | ❌ 缺失 | ETABS/SAP2000 集成 |
| **Stage 4: 施工文档** | ❌ 缺失 | 文档生成器 |
| **Stage 6: 验证优化** | ❌ 缺失 | 碰撞检测器, 规范验证器 |

---

## 6. 实施计划

### Phase 1: 基础框架 (2 周)

**目标**: 创建 Orchestrator Agent，实现 Stage 1-2

**任务**:
1. 创建 Orchestrator Agent 框架
2. 实现 Stage 1 (需求分析) — 只需要 Claude Code
3. 实现简单的 Stage 2 (建筑设计) — 只需要 Claude Code
4. 创建基础测试用例

**输出**:
- 可以从自然语言生成建筑设计方案
- 可以生成简单的楼层布局

### Phase 2: 结构集成 (2 周)

**目标**: 集成 ETABS/SAP2000，实现 Stage 3-4

**任务**:
1. 开发 ETABS/SAP2000 集成工具
2. 实现 Stage 3 (结构设计)
3. 实现 Stage 4 (施工文档)
4. 创建结构计算测试用例

**输出**:
- 可以生成结构设计方案
- 可以生成施工文档

### Phase 3: Revit 集成 (2 周)

**目标**: 完善 Revit API 工具，实现 Stage 5-6

**任务**:
1. 完善 Revit API 工具（添加更多构件类型）
2. 实现 Stage 5 (Revit 建模)
3. 实现 Stage 6 (验证和优化)
4. 创建端到端测试用例

**输出**:
- 可以在 Revit 中创建完整建筑
- 可以验证和优化设计

### Phase 4: 测试和优化 (2 周)

**目标**: 端到端测试和优化

**任务**:
1. 端到端测试（从自然语言到 Revit 模型）
2. 错误处理和优化
3. 文档和部署
4. 创建示例项目

**输出**:
- 完整的端到端流程
- 示例项目（Snowdon Towers 简化版）

**总时间: 8 周**

---

## 7. 关键挑战

### 1. 多 Agent 协调
**挑战**: 需要一个 Orchestrator Agent 来协调各阶段  
**解决方案**: 使用 Claude Code 作为 Orchestrator，通过状态机管理各阶段

### 2. 工具集成
**挑战**: 需要开发 Revit API 工具、结构计算工具等  
**解决方案**: 分阶段开发，优先开发核心工具

### 3. 错误处理
**挑战**: 每个阶段都可能失败，需要重试和回退  
**解决方案**: 使用状态机管理状态，支持重试和回退

### 4. 数据传递
**挑战**: 各阶段之间的数据格式需要统一  
**解决方案**: 使用 JSON 格式，定义统一的数据 schema

### 5. 真实建筑复杂度
**挑战**: Snowdon Towers 这样的复杂建筑需要结构计算  
**解决方案**: 集成 ETABS/SAP2000，或者先从简单建筑开始

---

## 8. 成功案例参考

### Snowdon Towers Sample Structural

**当前状态**:
- ✅ Revit 模型已存在 (19 层, 58 面墙, 27 块楼板)
- ❌ 没有配套的 PDF 建筑图纸
- ❌ 没有结构计算书
- ❌ 没有施工文档

**需要的参考资料**:
1. ✅ PDF 建筑图纸 (平面图、立面图、剖面图)
2. ✅ CAD 图纸 (.dwg)
3. ✅ 结构计算书
4. ✅ 施工图纸
5. ✅ 材料清单
6. ✅ 结构图纸

**如果没有配套图纸**:
- 可以从 .rvt 文件提取结构信息
- 但不知道设计意图和约束条件
- 建议先从简单建筑开始，生成完整文档

---

## 9. 下一步行动

### 选项 A: 立即开始 Phase 1 (推荐)
- 创建 Orchestrator Agent
- 实现 Stage 1-2
- 从简单建筑开始

### 选项 B: 先获取参考资料
- 获取 Snowdon Towers 的配套图纸
- 基于真实案例开发

### 选项 C: 混合方法
- 先从简单建筑开始
- 逐步增加复杂度
- 同时收集参考资料

---

## 10. 参考资料

### 建筑规范
- GB 50009-2012: 建筑结构荷载规范
- GB 50010-2010: 混凝土结构设计规范
- GB 50011-2010: 建筑抗震设计规范

### 技术文档
- Revit API 文档: https://www.revitapidocs.com/
- pyRevit 文档: https://pyrevit.readthedocs.io/
- ETABS API: https://www.csiamerica.com/products/etabs

### 示例项目
- Snowdon Towers Sample Structural.rvt
- VibeVilla 系列 (VibeVilla.0001.rvt ~ VibeVilla.0004.rvt)

---

## 附录: Claude Code 在各阶段的具体工作

### Stage 1: 需求分析
```
你: "建一个类似 Snowdon Towers 的 19 层塔楼"
    │
    ▼
Claude Code:
1. 理解意图 → "19 层，塔楼，参考 Snowdon Towers"
2. 查询规范 → "需要 GB 50009, GB 50010, GB 50011"
3. 生成需求规格 → floors=19, area=2500㎡/层, ...
```

### Stage 2: 建筑设计
```
Claude Code:
1. 生成楼层布局 → "1楼包含大堂(200㎡)、餐厅(150㎡)..."
2. 设计决策 → "选择框架-剪力墙体系"
3. 规范检查 → "餐厅面积符合规范"
```

### Stage 3: 结构设计
```
Claude Code:
1. 选择体系 → "框架-剪力墙，因为 19 层需要抗侧力"
2. 调用 ETABS → 结构计算
3. 解释结果 → "最大位移 45mm，符合规范"
```

### Stage 4: 施工文档
```
Claude Code:
1. 生成说明 → "1. 先施工基础，2. 施工柱子..."
2. 生成 BOM → "需要 C40 混凝土 500m³"
3. 生成质量检查点
```

### Stage 5: Revit 建模
```
Claude Code:
1. 生成序列 → "1. 创建楼层，2. 创建柱子..."
2. 调用 Revit API → 创建建筑元素
3. 监控 → "柱子创建成功，继续下一个"
```

### Stage 6: 验证优化
```
Claude Code:
1. 碰撞检测 → "发现 3 处碰撞"
2. 解释结果 → "梁与管道碰撞，建议调整管道位置"
3. 优化建议 → "可以减少 3 根柱子，节省 10%"
```

---

## 总结

### 核心思想
**Claude Code 是决策者，工具是执行者**

- **Claude Code** 负责: 理解、决策、解释、优化
- **工具** 负责: 调用 API、计算、生成文档

### 关键优势
1. **持续对话** — 可以理解用户反馈并迭代
2. **上下文记忆** — 记住之前的讨论
3. **多工具调用** — 可以调用 Revit API、ETABS 等
4. **解释能力** — 可以解释为什么这样设计

### 现实期望
- **简单建筑**: 可以立即开始
- **复杂建筑**: 需要 8 周开发
- **Snowdon Towers**: 需要配套图纸

---

**文档状态**: 草案 v0.2  
**下一步**: 等待审阅和修改，然后开始 Phase 1
