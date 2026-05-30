/**
 * Workflow Store — Zustand state management for the workflow canvas.
 *
 * Manages:
 * - Workflow definition (nodes, edges)
 * - Execution state (running, paused, completed)
 * - Node outputs and streaming data
 * - Selected node for configuration
 */

import { create } from 'zustand';
import {
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type Connection,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from '@xyflow/react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type NodeStatus = 'idle' | 'running' | 'completed' | 'error' | 'skipped';

export type NodeType = 'agent' | 'branch' | 'input' | 'output' | 'transform';

export interface AgentNodeData {
  type: 'agent';
  name: string;
  prompt: string;
  model: string;
  temperature?: number;
  maxTokens?: number;
  tools?: string[];
  inputMapping?: Record<string, string>;
  status?: NodeStatus;
  streamBuffer?: string;
  output?: string;
  executionTime?: number;
  error?: string;
  [key: string]: unknown;
}

export interface BranchNodeData {
  type: 'branch';
  name: string;
  conditions: Array<{
    id: string;
    outputPort: string;
    evaluatorType: 'prompt' | 'regex' | 'json_path';
    evaluatorConfig: Record<string, unknown>;
  }>;
  defaultOutput?: string;
  status?: NodeStatus;
  selectedPort?: string;
  [key: string]: unknown;
}

export interface InputNodeData {
  type: 'input';
  name: string;
  variables: Record<string, unknown>;
  required?: string[];
  status?: NodeStatus;
  [key: string]: unknown;
}

export interface OutputNodeData {
  type: 'output';
  name: string;
  outputMapping: Record<string, string>;
  format?: 'json' | 'text' | 'markdown';
  status?: NodeStatus;
  output?: unknown;
  [key: string]: unknown;
}

export interface TransformNodeData {
  type: 'transform';
  name: string;
  transformType: 'template' | 'json_path' | 'script';
  transformConfig: Record<string, unknown>;
  status?: NodeStatus;
  output?: unknown;
  [key: string]: unknown;
}

export type WorkflowNodeData =
  | AgentNodeData
  | BranchNodeData
  | InputNodeData
  | OutputNodeData
  | TransformNodeData;

export type WorkflowNode = Node<WorkflowNodeData>;
export type WorkflowEdge = Edge;

export type ExecutionState =
  | 'idle'
  | 'running'
  | 'paused'
  | 'waiting_input'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ExecutionStats {
  nodesExecuted: number;
  nodesSuccessful: number;
  nodesFailed: number;
  nodesSkipped: number;
  totalDuration: number;
}

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

interface WorkflowState {
  // Workflow metadata
  workflowId: string | null;
  workflowName: string;
  workflowDescription: string;

  // Canvas state
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];

  // Selection
  selectedNodeId: string | null;

  // Execution state
  executionId: string | null;
  executionState: ExecutionState;
  executionStats: ExecutionStats | null;
  executionError: string | null;

  // Actions — Canvas
  setNodes: (nodes: WorkflowNode[]) => void;
  setEdges: (edges: WorkflowEdge[]) => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;

  // Actions — Nodes
  addNode: (node: WorkflowNode) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: <T extends WorkflowNodeData>(
    nodeId: string,
    data: Partial<T>
  ) => void;
  selectNode: (nodeId: string | null) => void;

  // Actions — Workflow
  setWorkflow: (
    id: string,
    name: string,
    description: string,
    nodes: WorkflowNode[],
    edges: WorkflowEdge[]
  ) => void;
  setWorkflowName: (name: string) => void;
  setWorkflowDescription: (description: string) => void;
  resetWorkflow: () => void;

  // Actions — Execution
  setExecutionState: (state: ExecutionState) => void;
  setExecutionId: (id: string | null) => void;
  setExecutionStats: (stats: ExecutionStats | null) => void;
  setExecutionError: (error: string | null) => void;

  // Actions — Streaming
  appendStreamToken: (nodeId: string, token: string) => void;
  clearStreamBuffer: (nodeId: string) => void;
  setNodeOutput: (nodeId: string, output: unknown) => void;
  setNodeStatus: (nodeId: string, status: NodeStatus) => void;
  setNodeError: (nodeId: string, error: string) => void;
  setNodeExecutionTime: (nodeId: string, time: number) => void;

  // Reset all node statuses (e.g., before re-running)
  resetNodeStatuses: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  // Initial state
  workflowId: null,
  workflowName: 'Untitled Workflow',
  workflowDescription: '',
  nodes: [],
  edges: [],
  selectedNodeId: null,
  executionId: null,
  executionState: 'idle',
  executionStats: null,
  executionError: null,

  // --- Canvas actions ---

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes) as WorkflowNode[],
    });
  },

  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
    });
  },

  onConnect: (connection: Connection) => {
    set({
      edges: addEdge(
        {
          ...connection,
          id: `e-${connection.source}-${connection.target}-${Date.now()}`,
          animated: true,
        },
        get().edges
      ),
    });
  },

  // --- Node actions ---

  addNode: (node) =>
    set((state) => ({
      nodes: [...state.nodes, node],
    })),

  removeNode: (nodeId) =>
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter(
        (e) => e.source !== nodeId && e.target !== nodeId
      ),
      selectedNodeId:
        state.selectedNodeId === nodeId ? null : state.selectedNodeId,
    })),

  updateNodeData: (nodeId, data) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
    })),

  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  // --- Workflow actions ---

  setWorkflow: (id, name, description, nodes, edges) =>
    set({
      workflowId: id,
      workflowName: name,
      workflowDescription: description,
      nodes,
      edges,
      selectedNodeId: null,
      executionId: null,
      executionState: 'idle',
      executionStats: null,
      executionError: null,
    }),

  setWorkflowName: (name) => set({ workflowName: name }),
  setWorkflowDescription: (description) => set({ workflowDescription: description }),

  resetWorkflow: () =>
    set({
      workflowId: null,
      workflowName: 'Untitled Workflow',
      workflowDescription: '',
      nodes: [],
      edges: [],
      selectedNodeId: null,
      executionId: null,
      executionState: 'idle',
      executionStats: null,
      executionError: null,
    }),

  // --- Execution actions ---

  setExecutionState: (state) => set({ executionState: state }),
  setExecutionId: (id) => set({ executionId: id }),
  setExecutionStats: (stats) => set({ executionStats: stats }),
  setExecutionError: (error) => set({ executionError: error }),

  // --- Streaming actions ---

  appendStreamToken: (nodeId, token) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId && node.data.type === 'agent'
          ? {
              ...node,
              data: {
                ...node.data,
                streamBuffer: (node.data.streamBuffer ?? '') + token,
              },
            }
          : node
      ),
    })),

  clearStreamBuffer: (nodeId) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId && node.data.type === 'agent'
          ? { ...node, data: { ...node.data, streamBuffer: '' } }
          : node
      ),
    })),

  setNodeOutput: (nodeId, output) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, output } as WorkflowNodeData }
          : node
      ),
    })),

  setNodeStatus: (nodeId, status) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, status } as WorkflowNodeData }
          : node
      ),
    })),

  setNodeError: (nodeId, error) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, error } as WorkflowNodeData }
          : node
      ),
    })),

  setNodeExecutionTime: (nodeId, time) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: { ...node.data, executionTime: time } as WorkflowNodeData,
            }
          : node
      ),
    })),

  resetNodeStatuses: () =>
    set((state) => ({
      nodes: state.nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          status: 'idle',
          streamBuffer: '',
          output: undefined,
          error: undefined,
          executionTime: undefined,
        } as WorkflowNodeData,
      })),
    })),
}));

// ---------------------------------------------------------------------------
// Selectors (for optimized re-renders)
// ---------------------------------------------------------------------------

export const selectNode = (nodeId: string) => (state: WorkflowState) =>
  state.nodes.find((n) => n.id === nodeId);

export const selectSelectedNode = (state: WorkflowState) =>
  state.selectedNodeId
    ? state.nodes.find((n) => n.id === state.selectedNodeId) ?? null
    : null;

export const selectIsRunning = (state: WorkflowState) =>
  state.executionState === 'running' || state.executionState === 'paused';

export const selectCanExecute = (state: WorkflowState) =>
  state.executionState === 'idle' ||
  state.executionState === 'completed' ||
  state.executionState === 'failed' ||
  state.executionState === 'cancelled';
