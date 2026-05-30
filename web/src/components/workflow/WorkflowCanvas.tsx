/**
 * WorkflowCanvas — the main React Flow canvas for building workflows.
 *
 * Provides:
 * - Drag-and-drop node placement
 * - Edge connections between nodes
 * - Node selection and configuration
 * - Toolbar with actions (add node, execute, reset)
 */

import { useCallback, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type ReactFlowInstance,
  type NodeTypes,
  BackgroundVariant,
  Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  useWorkflowStore,
  selectIsRunning,
  selectCanExecute,
  type NodeType,
  type WorkflowNode,
  type WorkflowEdge,
} from './WorkflowStore';

import {
  AgentNode,
  InputNode,
  OutputNode,
  BranchNode,
  TransformNode,
} from './nodes';

import {
  Bot,
  LogIn,
  LogOut,
  GitBranch,
  ArrowRightLeft,
  Play,
  Square,
  RotateCcw,
  Plus,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Node type registry
// ---------------------------------------------------------------------------

const nodeTypes: NodeTypes = {
  agent: AgentNode,
  input: InputNode,
  output: OutputNode,
  branch: BranchNode,
  transform: TransformNode,
};

// ---------------------------------------------------------------------------
// Node creation templates
// ---------------------------------------------------------------------------

interface NodeTemplate {
  type: NodeType;
  label: string;
  icon: React.ReactNode;
  defaultData: Record<string, unknown>;
  color: string;
}

const NODE_TEMPLATES: NodeTemplate[] = [
  {
    type: 'agent',
    label: 'Agent',
    icon: <Bot className="w-4 h-4" />,
    color: 'text-primary',
    defaultData: {
      type: 'agent',
      name: 'Agent',
      prompt: '',
      model: 'gpt-4',
      temperature: 0.7,
      maxTokens: 4096,
      status: 'idle',
    },
  },
  {
    type: 'input',
    label: 'Input',
    icon: <LogIn className="w-4 h-4" />,
    color: 'text-blue-500',
    defaultData: {
      type: 'input',
      name: 'Input',
      variables: {},
      status: 'idle',
    },
  },
  {
    type: 'output',
    label: 'Output',
    icon: <LogOut className="w-4 h-4" />,
    color: 'text-purple-500',
    defaultData: {
      type: 'output',
      name: 'Output',
      outputMapping: {},
      format: 'json',
      status: 'idle',
    },
  },
  {
    type: 'branch',
    label: 'Branch',
    icon: <GitBranch className="w-4 h-4" />,
    color: 'text-amber-500',
    defaultData: {
      type: 'branch',
      name: 'Branch',
      conditions: [],
      defaultOutput: 'default',
      status: 'idle',
    },
  },
  {
    type: 'transform',
    label: 'Transform',
    icon: <ArrowRightLeft className="w-4 h-4" />,
    color: 'text-teal-500',
    defaultData: {
      type: 'transform',
      name: 'Transform',
      transformType: 'template',
      transformConfig: {},
      status: 'idle',
    },
  },
];

// ---------------------------------------------------------------------------
// WorkflowCanvas component
// ---------------------------------------------------------------------------

interface WorkflowCanvasProps {
  onExecute?: () => void;
  onStop?: () => void;
  onNodeSelect?: (nodeId: string | null) => void;
  readOnly?: boolean;
}

export function WorkflowCanvas({
  onExecute,
  onStop,
  onNodeSelect,
  readOnly = false,
}: WorkflowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useRef<ReactFlowInstance<WorkflowNode, WorkflowEdge> | null>(null);

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    selectNode,
    executionState,
    resetNodeStatuses,
  } = useWorkflowStore();

  const isRunning = useWorkflowStore(selectIsRunning);
  const canExecute = useWorkflowStore(selectCanExecute);

  // Handle node click for selection
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: WorkflowNode) => {
      selectNode(node.id);
      onNodeSelect?.(node.id);
    },
    [selectNode, onNodeSelect]
  );

  // Handle pane click to deselect
  const handlePaneClick = useCallback(() => {
    selectNode(null);
    onNodeSelect?.(null);
  }, [selectNode, onNodeSelect]);

  // Handle adding a new node
  const handleAddNode = useCallback(
    (template: NodeTemplate) => {
      const id = `${template.type}-${Date.now()}`;
      const position = reactFlowInstance.current
        ? reactFlowInstance.current.screenToFlowPosition({
            x: (reactFlowWrapper.current?.clientWidth ?? 400) / 2,
            y: (reactFlowWrapper.current?.clientHeight ?? 300) / 2,
          })
        : { x: 250 + Math.random() * 100, y: 150 + Math.random() * 100 };

      const newNode: WorkflowNode = {
        id,
        type: template.type,
        position,
        data: { ...template.defaultData } as WorkflowNode['data'],
      };

      addNode(newNode);
    },
    [addNode]
  );

  // Handle reset
  const handleReset = useCallback(() => {
    resetNodeStatuses();
  }, [resetNodeStatuses]);

  // MiniMap node color
  const miniMapNodeColor = useCallback((node: WorkflowNode) => {
    const status = 'status' in node.data ? node.data.status : 'idle';
    switch (status) {
      case 'running':
        return 'var(--color-primary)';
      case 'completed':
        return '#22c55e';
      case 'error':
        return '#ef4444';
      default:
        return 'var(--color-muted-foreground)';
    }
  }, []);

  return (
    <div ref={reactFlowWrapper} className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={readOnly ? undefined : onNodesChange}
        onEdgesChange={readOnly ? undefined : onEdgesChange}
        onConnect={readOnly ? undefined : onConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        onInit={(instance) => {
          reactFlowInstance.current = instance;
        }}
        nodeTypes={nodeTypes}
        fitView
        className="bg-background"
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="var(--color-muted-foreground)"
        />
        <Controls className="!bg-card !border-border" />
        <MiniMap
          nodeColor={miniMapNodeColor}
          className="!bg-card !border-border"
          maskColor="rgba(0, 0, 0, 0.1)"
        />

        {/* Add Node Panel */}
        {!readOnly && (
          <Panel position="top-left" className="!m-3">
            <div className="flex flex-wrap gap-1 bg-card border border-border rounded-lg p-1.5 shadow-md">
              {NODE_TEMPLATES.map((template) => (
                <button
                  key={template.type}
                  onClick={() => handleAddNode(template)}
                  disabled={isRunning}
                  className={`
                    flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs
                    hover:bg-muted transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${template.color}
                  `}
                  title={`Add ${template.label} node`}
                >
                  {template.icon}
                  <span className="text-foreground">{template.label}</span>
                </button>
              ))}
            </div>
          </Panel>
        )}

        {/* Execution Controls Panel */}
        <Panel position="top-right" className="!m-3">
          <div className="flex gap-2 bg-card border border-border rounded-lg p-1.5 shadow-md">
            {/* Execute button */}
            {canExecute && onExecute && (
              <button
                onClick={onExecute}
                disabled={nodes.length === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-medium transition-colors disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                Execute
              </button>
            )}

            {/* Stop button */}
            {isRunning && onStop && (
              <button
                onClick={onStop}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-medium transition-colors"
              >
                <Square className="w-3.5 h-3.5" />
                Stop
              </button>
            )}

            {/* Reset button */}
            {!canExecute && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-muted text-foreground hover:bg-muted/80 text-xs font-medium transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset
              </button>
            )}

            {/* Execution state badge */}
            {executionState !== 'idle' && (
              <span
                className={`
                  flex items-center px-2 py-1 rounded text-xs font-medium
                  ${executionState === 'running' ? 'bg-primary/10 text-primary' : ''}
                  ${executionState === 'completed' ? 'bg-green-500/10 text-green-500' : ''}
                  ${executionState === 'failed' ? 'bg-destructive/10 text-destructive' : ''}
                  ${executionState === 'paused' ? 'bg-amber-500/10 text-amber-500' : ''}
                  ${executionState === 'cancelled' ? 'bg-muted text-muted-foreground' : ''}
                  ${executionState === 'waiting_input' ? 'bg-blue-500/10 text-blue-500' : ''}
                `}
              >
                {executionState === 'running' && (
                  <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse mr-1.5" />
                )}
                {executionState}
              </span>
            )}
          </div>
        </Panel>

        {/* Empty state */}
        {nodes.length === 0 && (
          <Panel position="top-center" className="!mt-20">
            <div className="text-center bg-card border border-border rounded-lg p-6 shadow-md max-w-sm">
              <Plus className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
              <h3 className="font-medium mb-1">No nodes yet</h3>
              <p className="text-sm text-muted-foreground">
                Add nodes using the toolbar above, or load an existing workflow.
              </p>
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}
