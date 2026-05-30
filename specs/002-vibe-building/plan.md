# Vibe Building - 自然语言驱动 Revit 自动建模

## 项目愿景

**"Vibe Coding" for Architecture** — 用户通过自然语言描述建筑意图，AI 自动在 Revit 中创建和修改 BIM 模型。

```
"在三楼加一个 3x4 米的会议室"  ──→  🏢 自动生成墙体、门、窗
"把走廊拓宽到 2 米"            ──→  📐 实时修改模型
"添加消防通道"                 ──→  🚪 自动放置构件并检查规范
```

---

## 架构总览

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
│                        AI 推理层 (hermes-agent)                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  意图理解引擎                                                 │   │
│  │  "在三楼加一个3x4米的会议室"                                   │   │
│  │    → action: create_room                                     │   │
│  │    → params: {floor: 3, width: 3, depth: 4, type: "meeting"} │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  工作流引擎 (已有)                                            │   │
│  │  验证 → 规划 → 生成构件 → 放置 → 碰撞检测 → 确认              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │ HTTP API
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Revit 集成层 (pyRevit Routes)                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  pyRevit HTTP API Server (Flask-like)                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │   │
│  │  │ /walls   │ │ /doors   │ │ /rooms   │ │ /floors  │        │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Revit API (DB/UIApplication)                                │   │
│  │  创建/修改/删除 BIM 构件                                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Revit 2025 (F:\Revit)                        │
│  3D BIM 模型实时更新                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **用户界面** | React + Vite (已有) | Web 聊天 + 工作流画布 |
| **AI 引擎** | hermes-agent (已有) | LLM 意图理解 + 工具调用 |
| **工作流引擎** | Python workflow/ (已有) | 多步骤编排 + 流式传输 |
| **Revit 桥接** | pyRevit v6.4 Routes | HTTP API → Revit API |
| **建模引擎** | Revit 2025 | BIM 模型创建和修改 |
| **通信协议** | HTTP REST + SSE | AI ↔ Revit 双向通信 |

---

## 实现阶段

### Phase 1: pyRevit 扩展基础 (1-2 周)

创建 `VibeBuilding.extension`，建立 HTTP API 基础设施。

**目标**: 能通过 HTTP 在 Revit 中创建一个简单的墙体。

```
F:\pyRevit-Master\extensions\
└── VibeBuilding.extension/
    ├── extension.json           # 扩展清单
    ├── startup.py               # 启动 HTTP 服务器
    ├── lib/
    │   └── revit_ops.py         # Revit 操作封装
    ├── VibeBuilding.tab/
    │   └── Tools.panel/
    │       └── CreateWall.pushbutton/
    │           └── script.py
    └── api/
        ├── __init__.py          # API 路由注册
        ├── walls.py             # /api/vb/walls
        ├── rooms.py             # /api/vb/rooms
        └── model.py             # /api/vb/model (查询)
```

**核心文件**:

```python
# startup.py - 启动 pyRevit HTTP 服务器
from pyrevit import routes
api = routes.API("vibe-building")

@api.route('/health', methods=['GET'])
def health(uiapp):
    return {"status": "ok", "revit_version": uiapp.Application.VersionNumber}

@api.route('/walls', methods=['POST'])
def create_wall(uiapp, request):
    """创建墙体"""
    data = request.data
    # ... Revit API 调用
    return {"wall_id": new_wall.Id.IntegerValue}
```

**任务**:
- [ ] 创建 VibeBuilding.extension 骨架
- [ ] 实现 startup.py 启动 HTTP 服务器
- [ ] 实现 `/api/vb/health` 端点
- [ ] 实现 `/api/vb/walls` POST (创建墙体)
- [ ] 实现 `/api/vb/walls` GET (查询墙体列表)
- [ ] 测试: curl 创建墙体 → Revit 中出现墙体

### Phase 2: 构件 API 扩展 (2-3 周)

扩展 API 支持所有主要 BIM 构件类型。

**API 端点**:

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/vb/walls` | POST/GET | 创建/查询墙体 |
| `/api/vb/doors` | POST/GET | 创建/查询门 |
| `/api/vb/windows` | POST/GET | 创建/查询窗 |
| `/api/vb/floors` | POST/GET | 创建/查询楼板 |
| `/api/vb/rooms` | POST/GET | 创建/查询房间 |
| `/api/vb/columns` | POST/GET | 创建/查询柱子 |
| `/api/vb/stairs` | POST/GET | 创建/查询楼梯 |
| `/api/vb/model` | GET | 获取模型概况 |
| `/api/vb/model/elements` | GET | 查询所有构件 |
| `/api/vb/model/levels` | GET | 获取楼层信息 |
| `/api/vb/model/export` | GET | 导出模型数据 |

**数据结构示例**:

```json
POST /api/vb/walls
{
  "start_point": {"x": 0, "y": 0, "z": 0},
  "end_point": {"x": 5000, "y": 0, "z": 0},
  "height": 3000,
  "wall_type": "Basic Wall - 200mm",
  "level": "Level 1"
}

Response:
{
  "id": 12345,
  "element_type": "wall",
  "parameters": {...}
}
```

### Phase 3: AI 意图理解 (2-3 周)

为 hermes-agent 创建建筑领域的工具和提示词。

**自定义工具**:

```python
# tools/revit_create_wall.py
"""创建墙体构件"""
tool_name = "revit_create_wall"
description = "在 Revit 模型中创建一面墙体"
parameters = {
    "start_point": "起点坐标 (x, y, z) 单位:毫米",
    "end_point": "终点坐标 (x, y, z) 单位:毫米",
    "height": "墙体高度 (毫米)",
    "wall_type": "墙体类型名称",
    "level": "所在楼层"
}
```

**系统提示词**:

```markdown
你是一个建筑信息模型(BIM)助手。用户会用自然语言描述建筑需求，
你需要将其转换为 Revit API 调用。

你的能力:
- 创建/修改/删除建筑构件 (墙、门、窗、楼板、柱子等)
- 查询当前模型状态
- 验证建筑规范合规性
- 估算材料用量

工作原则:
1. 先理解用户意图，确认关键参数
2. 缺失参数时使用合理默认值并告知用户
3. 复杂操作分步执行，每步确认
4. 始终考虑建筑规范和安全性

坐标系说明:
- X/Y 为水平面坐标，单位毫米
- Z 为垂直方向，单位毫米
- 原点在项目基点
```

**任务**:
- [ ] 创建 hermes-agent 建筑工具集
- [ ] 设计建筑领域系统提示词
- [ ] 实现 Revit HTTP 客户端 (从 hermes 调用 pyRevit)
- [ ] 测试: 自然语言 → 工具调用 → Revit 建模

### Phase 4: 工作流集成 (1-2 周)

将工作流引擎与 Revit 集成，支持复杂多步骤操作。

**工作流示例**: "创建一个三居室公寓"

```
[用户输入] → [意图解析] → [空间规划] → [生成墙体] → [添加门窗]
                                              ↓
                                        [碰撞检测] → [材料统计]
                                              ↓
                                        [用户确认] → [应用修改]
```

**利用已有的**:
- ✅ WorkflowExecutor 编排多步骤
- ✅ StreamHandler 实时反馈
- ✅ ContextAccumulator 传递中间结果
- ✅ ErrorClassifier 处理建模错误

### Phase 5: 实时预览与反馈 (2-3 周)

实现 Revit → Web 的实时反馈。

- 模型截图/缩略图
- 构件列表实时更新
- 操作历史/撤销
- 3D 视图嵌入 (使用 Revit 的导出功能)

### Phase 6: 智能建筑规范 (2-3 周)

- 自动检查建筑规范
- 防火通道验证
- 无障碍设计检查
- 结构合理性分析

---

## 核心文件结构

```
f:\VibeBuilding\
├── workflow/                    # ✅ 已有: 工作流引擎
├── web/src/components/workflow/ # ✅ 已有: 前端画布
├── specs/001-workflow-management/plan.md
│
├── vibe_building/               # 🆕 AI 建筑模块
│   ├── __init__.py
│   ├── intent_parser.py         # 自然语言意图解析
│   ├── building_tools/          # hermes-agent 工具
│   │   ├── revit_wall.py
│   │   ├── revit_door.py
│   │   ├── revit_room.py
│   │   └── revit_query.py
│   ├── prompts/                 # 建筑领域提示词
│   │   ├── system_prompt.md
│   │   └── examples.md
│   └── revit_client.py          # HTTP 客户端 → pyRevit
│
└── extensions/                  # 🆕 pyRevit 扩展 (或放在 F:\pyRevit-Master)
    └── VibeBuilding.extension/
        ├── extension.json
        ├── startup.py
        ├── lib/
        └── api/
```

---

## 最小可行原型 (MVP)

**目标**: 用户说 "建一面5米长的墙" → Revit 中出现一面墙

**需要的最少组件**:

1. **pyRevit 扩展** — 一个 HTTP 端点 `/api/vb/walls`
2. **hermes 工具** — 一个 `revit_create_wall` 工具
3. **系统提示词** — 告诉 AI 如何理解"建一面墙"
4. **连接** — hermes → HTTP → pyRevit → Revit API

**预估**: 500-800 行代码, 2-3 天可完成

---

## 风险与解决方案

| 风险 | 影响 | 解决方案 |
|------|------|---------|
| pyRevit HTTP 服务器不稳定 | 高 | 备选: Revit Journal 文件驱动 |
| AI 理解建筑术语不准确 | 中 | 建筑领域微调 + 示例库 |
| Revit API 操作失败 | 中 | 事务回滚 + 错误分类 |
| 坐标系混乱 | 高 | 提供网格参考 + 可视化预览 |
| 建筑规范复杂 | 低 | MVP 阶段忽略, 后续添加 |

---

## 参考资源

- [pyRevit 文档](https://docs.pyrevitlabs.io/)
- [pyRevit Routes API](https://docs.pyrevitlabs.io/reference/pyrevit/routes/)
- [Revit API 文档](https://www.revitapidocs.com/)
- [Dynamo Python](https://dynamoprimer.com/)
- [hermes-agent 工具开发](./AGENTS.md)

---

## 成功标准

1. ✅ 用户能用自然语言创建基本构件 (墙、门、窗)
2. ✅ 用户能查询当前模型状态
3. ✅ 用户能修改已有构件
4. ✅ 操作结果在 Revit 中实时可见
5. ✅ AI 能处理模糊指令并合理推断参数
