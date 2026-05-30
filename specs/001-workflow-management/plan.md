# AI-Powered Workflow Management System - Implementation Plan

## Executive Summary

Build a visual workflow management system that enables users to create, execute, and monitor AI-powered workflows on an interactive canvas. Each node in the workflow represents a discrete AI agent execution, and edges define the flow of data and control between agents.

**Codebase**: [hermes-agent](https://github.com/NousResearch/hermes-agent) by Nous Research
- **Backend**: Python (agent runtime, tool execution, context management)
- **Frontend**: React 19 + TypeScript + Vite + TailwindCSS

---

## Architecture Overview

### Integration Points

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WEB FRONTEND (React + Vite)                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    WORKFLOW CANVAS                              │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │ │
│  │  │  Agent   │───▶│  Agent   │───▶│  Agent   │                  │ │
│  │  │  Node 1  │    │  Node 2  │    │  Node 3  │                  │ │
│  │  └──────────┘    └──────────┘    └──────────┘                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │ WebSocket/SSE                        │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW ENGINE (Python)                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │
│  │  State Machine │  │ Node Scheduler │  │Context Manager │         │
│  └────────────────┘  └────────────────┘  └────────────────┘         │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     HERMES AGENT CORE                                │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │
│  │  Agent Runtime │  │ Tool Executor  │  │ Stream Handler │         │
│  │ (agent/*.py)   │  │(agent/tool_*.py)│  │                │         │
│  └────────────────┘  └────────────────┘  └────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Node = Agent Execution**: Each node encapsulates a single AI agent invocation with its own prompt, model, and configuration
2. **Edge = Data Flow**: Edges carry context and results between nodes
3. **Streaming First**: Real-time token streaming from LLM to UI via WebSocket
4. **Stateful Execution**: Workflow state persisted for pause/resume/retry
5. **Conditional Branching**: Nodes can have multiple output ports based on AI-evaluated conditions
6. **Context Accumulation**: Workflow context grows as nodes complete

---

## Data Models

### Workflow Schema (Python dataclasses)

```python
from dataclasses import dataclass, field
from typing import Any, Literal
from datetime import datetime
from enum import Enum

class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class NodeType(Enum):
    AGENT = "agent"
    BRANCH = "branch"
    INPUT = "input"
    OUTPUT = "output"
    TRANSFORM = "transform"

@dataclass
class Position:
    x: float
    y: float

@dataclass
class AgentNodeData:
    prompt: str
    model: str  # e.g., 'claude-3-opus', 'gpt-4', 'hermes-3'
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[str] = field(default_factory=list)  # Tool names
    input_mapping: dict[str, str] = field(default_factory=dict)  # var -> source

@dataclass
class BranchCondition:
    id: str
    output_port: str
    evaluator_type: Literal["prompt", "regex", "json_path"]
    evaluator_config: dict[str, Any]

@dataclass
class BranchNodeData:
    conditions: list[BranchCondition]
    default_output: str = "default"

@dataclass
class NodeConfig:
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout: float = 300.0  # seconds
    parallel: bool = False
    breakpoint: bool = False

@dataclass
class WorkflowNode:
    id: str
    type: NodeType
    position: Position
    data: AgentNodeData | BranchNodeData | dict
    config: NodeConfig = field(default_factory=NodeConfig)

@dataclass
class WorkflowEdge:
    id: str
    source: str  # Node ID
    source_port: str = "default"
    target: str  # Node ID
    target_port: str = "input"

@dataclass
class NodeOutput:
    node_id: str
    output: Any
    tokens: dict[str, int]  # {"prompt": N, "completion": M}
    duration: float
    status: Literal["success", "error", "skipped"]
    error: str | None = None

@dataclass
class WorkflowContext:
    variables: dict[str, Any] = field(default_factory=dict)
    node_outputs: dict[str, NodeOutput] = field(default_factory=dict)
    execution_history: list[str] = field(default_factory=list)  # Node IDs

@dataclass
class Workflow:
    id: str
    name: str
    description: str = ""
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)
    context: WorkflowContext = field(default_factory=WorkflowContext)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
```

---

## Workflow Execution Engine

### State Machine

```python
from enum import Enum
from typing import Set

class ExecutionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowExecution:
    def __init__(self, workflow: Workflow):
        self.id = generate_execution_id()
        self.workflow = workflow
        self.state = ExecutionState.IDLE
        self.current_nodes: Set[str] = set()
        self.context = WorkflowContext()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.error: str | None = None
```

### Execution Flow

```python
async def execute_workflow(self, execution: WorkflowExecution):
    """Main execution loop for workflow."""
    execution.state = ExecutionState.RUNNING
    execution.started_at = datetime.now()
    
    try:
        while True:
            # Find executable nodes (dependencies satisfied)
            executable = self._get_executable_nodes(execution)
            
            if not executable:
                # No more nodes to execute
                break
            
            # Execute nodes (parallel if configured)
            parallel_nodes = [n for n in executable if n.config.parallel]
            sequential_nodes = [n for n in executable if not n.config.parallel]
            
            # Run parallel nodes concurrently
            if parallel_nodes:
                await asyncio.gather(*[
                    self._execute_node(execution, node) 
                    for node in parallel_nodes
                ])
            
            # Run sequential nodes one at a time
            for node in sequential_nodes:
                await self._execute_node(execution, node)
        
        execution.state = ExecutionState.COMPLETED
        execution.completed_at = datetime.now()
        
    except Exception as e:
        execution.state = ExecutionState.FAILED
        execution.error = str(e)
        raise
```

### Node Execution with Streaming

```python
async def _execute_node(
    self, 
    execution: WorkflowExecution, 
    node: WorkflowNode
):
    """Execute a single workflow node."""
    execution.current_nodes.add(node.id)
    
    try:
        # Check for breakpoint
        if node.config.breakpoint:
            execution.state = ExecutionState.PAUSED
            await self._notify_breakpoint(node.id)
            await self._wait_for_resume()
            execution.state = ExecutionState.RUNNING
        
        # Resolve input context
        resolved_prompt = self._resolve_input(node, execution.context)
        
        # Execute agent with streaming
        start_time = time.time()
        output_buffer = []
        
        async for token in self.agent_runtime.execute_stream(
            prompt=resolved_prompt,
            model=node.data.model,
            temperature=node.data.temperature,
            max_tokens=node.data.max_tokens,
            tools=node.data.tools,
        ):
            output_buffer.append(token)
            await self._broadcast_token(execution.id, node.id, token)
        
        duration = time.time() - start_time
        full_output = "".join(output_buffer)
        
        # Store output in context
        execution.context.node_outputs[node.id] = NodeOutput(
            node_id=node.id,
            output=full_output,
            tokens={"prompt": 0, "completion": len(output_buffer)},
            duration=duration,
            status="success",
        )
        execution.context.execution_history.append(node.id)
        
        await self._broadcast_node_complete(execution.id, node.id, full_output)
        
    except Exception as e:
        execution.context.node_outputs[node.id] = NodeOutput(
            node_id=node.id,
            output=None,
            tokens={"prompt": 0, "completion": 0},
            duration=0,
            status="error",
            error=str(e),
        )
        raise
    
    finally:
        execution.current_nodes.discard(node.id)
```

---

## Frontend Implementation

### New Dependencies Required

```json
{
  "dependencies": {
    "@xyflow/react": "^12.0.0",  // React Flow for canvas
    "zustand": "^4.5.0"          // State management (lightweight)
  }
}
```

### Workflow Canvas Component

```tsx
// web/src/components/workflow/WorkflowCanvas.tsx
import { 
  ReactFlow, 
  Controls, 
  Background,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { AgentNode } from './nodes/AgentNode';
import { BranchNode } from './nodes/BranchNode';
import { useWorkflowExecution } from '@/hooks/useWorkflowExecution';

const nodeTypes = {
  agent: AgentNode,
  branch: BranchNode,
};

interface WorkflowCanvasProps {
  workflowId: string;
}

export function WorkflowCanvas({ workflowId }: WorkflowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { executeWorkflow, execution, isConnected } = useWorkflowExecution();
  
  // Load workflow from API
  useEffect(() => {
    fetchWorkflow(workflowId).then(wf => {
      setNodes(wf.nodes.map(toReactFlowNode));
      setEdges(wf.edges.map(toReactFlowEdge));
    });
  }, [workflowId]);
  
  // Connect to WebSocket for streaming
  useEffect(() => {
    if (!execution?.id) return;
    
    const ws = new WebSocket(`/api/workflow/${execution.id}/stream`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'token':
          updateNodeData(data.nodeId, { 
            streamBuffer: prev => prev + data.token 
          });
          break;
        case 'node_complete':
          updateNodeData(data.nodeId, { 
            status: 'completed', 
            output: data.output 
          });
          break;
        case 'workflow_complete':
          toast.success('Workflow completed');
          break;
      }
    };
    
    return () => ws.close();
  }, [execution?.id]);
  
  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
      >
        <Controls />
        <Background />
        <WorkflowToolbar 
          onExecute={() => executeWorkflow(workflowId)}
          isRunning={execution?.state === 'running'}
        />
      </ReactFlow>
    </div>
  );
}
```

### Agent Node Component

```tsx
// web/src/components/workflow/nodes/AgentNode.tsx
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Bot, Clock, Zap, Loader2, CheckCircle2 } from 'lucide-react';

interface AgentNodeData {
  name: string;
  prompt: string;
  model: string;
  status?: 'idle' | 'running' | 'completed' | 'error';
  streamBuffer?: string;
  output?: string;
  executionTime?: number;
}

export function AgentNode({ data, selected }: NodeProps) {
  const { name, prompt, model, status, streamBuffer, output, executionTime } = data;
  
  return (
    <div className={cn(
      'bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 min-w-[250px]',
      selected && 'border-blue-500',
      status === 'running' && 'border-yellow-500 animate-pulse',
      status === 'completed' && 'border-green-500',
      status === 'error' && 'border-red-500',
    )}>
      {/* Header */}
      <div className="flex items-center gap-2 p-3 border-b">
        <Bot className="w-4 h-4" />
        <span className="font-medium truncate">{name || 'Agent'}</span>
        {status === 'running' && <Loader2 className="w-4 h-4 animate-spin ml-auto" />}
        {status === 'completed' && <CheckCircle2 className="w-4 h-4 text-green-500 ml-auto" />}
      </div>
      
      {/* Body */}
      <div className="p-3 space-y-2">
        {/* Prompt preview */}
        <div className="text-xs text-gray-500 line-clamp-2">
          {prompt.slice(0, 100)}...
        </div>
        
        {/* Streaming output */}
        {status === 'running' && streamBuffer && (
          <div className="text-xs bg-gray-100 dark:bg-gray-900 p-2 rounded max-h-32 overflow-auto">
            {streamBuffer}
          </div>
        )}
        
        {/* Completed output */}
        {status === 'completed' && output && (
          <div className="text-xs bg-green-50 dark:bg-green-900/20 p-2 rounded max-h-32 overflow-auto">
            {output.slice(0, 200)}...
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="flex items-center gap-2 px-3 py-2 border-t text-xs text-gray-500">
        <Zap className="w-3 h-3" />
        <span>{model}</span>
        {executionTime && (
          <>
            <Clock className="w-3 h-3 ml-auto" />
            <span>{executionTime.toFixed(1)}s</span>
          </>
        )}
      </div>
      
      {/* Handles */}
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
```

---

## Backend API Endpoints

### Workflow Management (FastAPI)

```python
# workflow/api.py

from fastapi import APIRouter, WebSocket
from typing import AsyncGenerator

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

@router.get("/")
async def list_workflows() -> list[Workflow]:
    """List all workflows."""
    return await workflow_repo.list_all()

@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> Workflow:
    """Get a workflow by ID."""
    return await workflow_repo.get(workflow_id)

@router.post("/")
async def create_workflow(data: CreateWorkflowRequest) -> Workflow:
    """Create a new workflow."""
    workflow = Workflow(
        id=generate_id(),
        name=data.name,
        description=data.description,
        nodes=data.nodes,
        edges=data.edges,
    )
    await workflow_repo.save(workflow)
    return workflow

@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, data: UpdateWorkflowRequest) -> Workflow:
    """Update a workflow."""
    workflow = await workflow_repo.get(workflow_id)
    workflow.nodes = data.nodes
    workflow.edges = data.edges
    workflow.updated_at = datetime.now()
    await workflow_repo.save(workflow)
    return workflow

@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow."""
    await workflow_repo.delete(workflow_id)

@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str) -> dict:
    """Start workflow execution."""
    workflow = await workflow_repo.get(workflow_id)
    execution = WorkflowExecution(workflow)
    await execution_repo.save(execution)
    
    # Start execution in background
    asyncio.create_task(workflow_engine.execute(execution))
    
    return {"execution_id": execution.id}

@router.websocket("/{execution_id}/stream")
async def stream_execution(websocket: WebSocket, execution_id: str):
    """WebSocket stream for execution events."""
    await websocket.accept()
    
    async for event in workflow_engine.subscribe(execution_id):
        await websocket.send_json(event)
    
    await websocket.close()
```

---

## Implementation Phases

### Phase 1: Foundation & Data Models (Week 1-2)

**Tasks:**
- [ ] Create `workflow/` module with data models
- [ ] Set up SQLite schema for workflows and executions
- [ ] Create workflow repository (CRUD operations)
- [ ] Implement basic workflow validation

**Files to create:**
```
workflow/
├── __init__.py
├── models.py          # Dataclasses for Workflow, Node, Edge, etc.
├── repository.py      # Database operations
├── validation.py      # Workflow graph validation
└── exceptions.py      # Custom exceptions
```

### Phase 2: Agent Node Integration (Week 2-3)

**Tasks:**
- [ ] Create AgentNode executor that wraps agent runtime
- [ ] Implement input mapping/resolution from context
- [ ] Add tool execution support
- [ ] Integrate with existing streaming infrastructure

**Files to create:**
```
workflow/
├── nodes/
│   ├── __init__.py
│   ├── base.py        # Base node executor
│   ├── agent_node.py  # Agent execution wrapper
│   └── input_resolver.py  # Context resolution
```

### Phase 3: Workflow Execution Engine (Week 3-5)

**Tasks:**
- [ ] Build state machine for workflow execution
- [ ] Implement node scheduler with parallel execution support
- [ ] Create execution context manager
- [ ] Add execution persistence and recovery

**Files to create:**
```
workflow/
├── engine/
│   ├── __init__.py
│   ├── executor.py    # Main execution loop
│   ├── scheduler.py   # Node scheduling
│   ├── state_machine.py  # Execution states
│   └── context.py     # Context management
```

### Phase 4: Frontend Canvas & Nodes (Week 4-6)

**Tasks:**
- [ ] Install `@xyflow/react` and `zustand`
- [ ] Create WorkflowCanvas component with React Flow
- [ ] Create AgentNode component with streaming display
- [ ] Create BranchNode component
- [ ] Add node configuration panel

**Files to create:**
```
web/src/
├── components/workflow/
│   ├── WorkflowCanvas.tsx
│   ├── WorkflowToolbar.tsx
│   ├── nodes/
│   │   ├── AgentNode.tsx
│   │   ├── BranchNode.tsx
│   │   └── NodeConfigPanel.tsx
│   └── panels/
│       └── NodeEditor.tsx
├── hooks/
│   └── useWorkflowExecution.ts
├── pages/
│   └── WorkflowPage.tsx
```

### Phase 5: Streaming Integration (Week 6-7)

**Tasks:**
- [ ] Create WebSocket endpoint for execution events
- [ ] Implement stream buffer management
- [ ] Add real-time UI updates in frontend
- [ ] Create execution monitoring dashboard

**Files to create:**
```
workflow/
├── streaming/
│   ├── __init__.py
│   ├── handler.py     # Stream event handler
│   └── broadcast.py   # Event broadcasting
```

### Phase 6: Context Management (Week 7-8)

**Tasks:**
- [ ] Implement context accumulation logic
- [ ] Create variable interpolation in prompts (e.g., `{{node_1.output}}`)
- [ ] Add context visualization in UI
- [ ] Implement context debugging tools

**Files to create:**
```
workflow/
├── context/
│   ├── __init__.py
│   ├── accumulator.py   # Context building
│   └── interpolator.py  # Variable substitution
```

### Phase 7: Conditional Branching (Week 8-9)

**Tasks:**
- [ ] Implement BranchNode executor
- [ ] Create prompt-based condition evaluator
- [ ] Add regex and JSON-path evaluators
- [ ] Build branch configuration UI

**Files to create:**
```
workflow/
├── nodes/
│   ├── branch_node.py
│   └── condition_evaluator.py
```

### Phase 8: Error Handling & Recovery (Week 9-10)

**Tasks:**
- [ ] Implement retry policies
- [ ] Add breakpoint support (pause before node)
- [ ] Create error visualization
- [ ] Implement execution replay/history

**Files to create:**
```
workflow/
├── engine/
│   ├── retry.py       # Retry logic
│   └── breakpoints.py # Breakpoint handling
```

---

## Open Questions

1. **Persistence**: SQLite (simple, file-based) vs PostgreSQL (production-ready)?
2. **Execution model**: In-process async vs Celery worker queue?
3. **Scheduling**: Support for scheduled/recurring workflow execution (integrate with existing `cron/`)?
4. **Versioning**: How to handle running executions when workflow definition changes?

---

## References

- [React Flow Documentation](https://reactflow.dev/)
- [Hermes Agent Architecture](./AGENTS.md)
- [Existing Streaming Infrastructure](./agent/stream_diag.py)
