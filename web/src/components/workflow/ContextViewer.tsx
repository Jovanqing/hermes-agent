/**
 * ContextViewer — component for inspecting workflow execution context.
 *
 * Displays:
 * - Current variables
 * - Node outputs
 * - Execution statistics
 * - Context snapshots (for debugging)
 */

import { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Variable,
  Box,
  BarChart3,
  Camera,
  Copy,
  Check,
} from 'lucide-react';
import {
  useWorkflowStore,
  type ExecutionStats,
  type NodeStatus,
} from './WorkflowStore';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NodeOutput {
  nodeId: string;
  output: unknown;
  status: NodeStatus;
  duration?: number;
  tokens?: { prompt: number; completion: number };
  error?: string;
}

interface ContextData {
  variables: Record<string, unknown>;
  inputVariables: Record<string, unknown>;
  nodeOutputs: Record<string, NodeOutput>;
  executionHistory: string[];
  stats?: ExecutionStats;
}

// ---------------------------------------------------------------------------
// Collapsible section
// ---------------------------------------------------------------------------

function CollapsibleSection({
  title,
  icon,
  defaultOpen = false,
  count,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  count?: number;
  children: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full px-3 py-2 bg-muted/50 hover:bg-muted transition-colors text-left"
      >
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        )}
        {icon}
        <span className="font-medium text-sm flex-1">{title}</span>
        {count !== undefined && (
          <span className="text-xs text-muted-foreground bg-background px-1.5 py-0.5 rounded">
            {count}
          </span>
        )}
      </button>
      {isOpen && <div className="p-3 bg-background">{children}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Value display
// ---------------------------------------------------------------------------

function ValueDisplay({ value, truncate = true }: { value: unknown; truncate?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const formatted = useMemo(() => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'string') return value;
    return JSON.stringify(value, null, 2);
  }, [value]);

  const isLong = formatted.length > 100;
  const displayValue = truncate && isLong && !expanded
    ? formatted.slice(0, 100) + '...'
    : formatted;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(formatted);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <pre className="text-xs font-mono whitespace-pre-wrap break-all bg-muted/30 p-2 rounded">
        {displayValue}
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-primary hover:underline mt-1"
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
      <button
        onClick={handleCopy}
        className="absolute top-1 right-1 p-1 opacity-0 group-hover:opacity-100 transition-opacity bg-background rounded"
      >
        {copied ? (
          <Check className="w-3 h-3 text-green-500" />
        ) : (
          <Copy className="w-3 h-3 text-muted-foreground" />
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variables list
// ---------------------------------------------------------------------------

function VariablesList({
  variables,
  emptyMessage,
}: {
  variables: Record<string, unknown>;
  emptyMessage: string;
}) {
  const keys = Object.keys(variables);

  if (keys.length === 0) {
    return (
      <p className="text-xs text-muted-foreground italic">{emptyMessage}</p>
    );
  }

  return (
    <div className="space-y-2">
      {keys.map((key) => (
        <div key={key} className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded">
              {key}
            </span>
            <span className="text-xs text-muted-foreground">
              {typeof variables[key]}
            </span>
          </div>
          <ValueDisplay value={variables[key]} />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Node outputs list
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<NodeStatus, string> = {
  idle: 'text-muted-foreground',
  running: 'text-primary',
  completed: 'text-green-500',
  error: 'text-destructive',
  skipped: 'text-muted-foreground',
};

function NodeOutputsList({ outputs }: { outputs: Record<string, NodeOutput> }) {
  const nodeIds = Object.keys(outputs);

  if (nodeIds.length === 0) {
    return (
      <p className="text-xs text-muted-foreground italic">No node outputs yet</p>
    );
  }

  return (
    <div className="space-y-3">
      {nodeIds.map((nodeId) => {
        const output = outputs[nodeId];
        return (
          <div key={nodeId} className="space-y-1 border-l-2 border-border pl-3">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium ${STATUS_COLORS[output.status]}`}>
                {output.status}
              </span>
              <span className="text-xs font-mono text-foreground">{nodeId}</span>
              {output.duration !== undefined && (
                <span className="text-xs text-muted-foreground">
                  {output.duration.toFixed(2)}s
                </span>
              )}
              {output.tokens && (
                <span className="text-xs text-muted-foreground">
                  {output.tokens.prompt + output.tokens.completion} tokens
                </span>
              )}
            </div>
            {output.error ? (
              <pre className="text-xs font-mono text-destructive bg-destructive/10 p-2 rounded">
                {output.error}
              </pre>
            ) : (
              <ValueDisplay value={output.output} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Statistics display
// ---------------------------------------------------------------------------

function StatisticsDisplay({ stats }: { stats?: ExecutionStats }) {
  if (!stats) {
    return (
      <p className="text-xs text-muted-foreground italic">No statistics available</p>
    );
  }

  const items = [
    { label: 'Nodes Executed', value: stats.nodesExecuted },
    { label: 'Successful', value: stats.nodesSuccessful, color: 'text-green-500' },
    { label: 'Failed', value: stats.nodesFailed, color: 'text-destructive' },
    { label: 'Skipped', value: stats.nodesSkipped },
    { label: 'Duration', value: `${stats.totalDuration.toFixed(2)}s` },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex justify-between items-center bg-muted/30 px-2 py-1.5 rounded"
        >
          <span className="text-xs text-muted-foreground">{item.label}</span>
          <span className={`text-xs font-medium ${item.color ?? ''}`}>
            {item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface ContextViewerProps {
  className?: string;
}

export function ContextViewer({ className = '' }: ContextViewerProps) {
  const { nodes, executionState, executionStats } = useWorkflowStore();

  // Build context data from store
  const contextData = useMemo<ContextData>(() => {
    const variables: Record<string, unknown> = {};
    const inputVariables: Record<string, unknown> = {};
    const nodeOutputs: Record<string, NodeOutput> = {};
    const executionHistory: string[] = [];

    for (const node of nodes) {
      const data = node.data as Record<string, unknown>;
      const status = (data.status as NodeStatus) ?? 'idle';

      // Collect variables from input nodes
      if (data.type === 'input' && data.variables) {
        Object.assign(inputVariables, data.variables as Record<string, unknown>);
      }

      // Collect outputs from completed nodes
      if (status === 'completed' || status === 'error') {
        nodeOutputs[node.id] = {
          nodeId: node.id,
          output: data.output,
          status,
          duration: data.executionTime as number | undefined,
          error: data.error as string | undefined,
        };
        executionHistory.push(node.id);
      }
    }

    return {
      variables,
      inputVariables,
      nodeOutputs,
      executionHistory,
      stats: executionStats ?? undefined,
    };
  }, [nodes, executionStats]);

  const hasExecution = executionState !== 'idle';

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-sm">Context Inspector</h3>
        <span
          className={`text-xs px-2 py-0.5 rounded ${
            hasExecution
              ? 'bg-primary/10 text-primary'
              : 'bg-muted text-muted-foreground'
          }`}
        >
          {executionState}
        </span>
      </div>

      {/* Input Variables */}
      <CollapsibleSection
        title="Input Variables"
        icon={<Variable className="w-4 h-4 text-blue-500" />}
        defaultOpen={Object.keys(contextData.inputVariables).length > 0}
        count={Object.keys(contextData.inputVariables).length}
      >
        <VariablesList
          variables={contextData.inputVariables}
          emptyMessage="No input variables defined"
        />
      </CollapsibleSection>

      {/* Context Variables */}
      <CollapsibleSection
        title="Variables"
        icon={<Variable className="w-4 h-4 text-primary" />}
        count={Object.keys(contextData.variables).length}
      >
        <VariablesList
          variables={contextData.variables}
          emptyMessage="No variables set during execution"
        />
      </CollapsibleSection>

      {/* Node Outputs */}
      <CollapsibleSection
        title="Node Outputs"
        icon={<Box className="w-4 h-4 text-amber-500" />}
        defaultOpen={Object.keys(contextData.nodeOutputs).length > 0}
        count={Object.keys(contextData.nodeOutputs).length}
      >
        <NodeOutputsList outputs={contextData.nodeOutputs} />
      </CollapsibleSection>

      {/* Statistics */}
      <CollapsibleSection
        title="Statistics"
        icon={<BarChart3 className="w-4 h-4 text-green-500" />}
      >
        <StatisticsDisplay stats={contextData.stats} />
      </CollapsibleSection>

      {/* Snapshots (placeholder) */}
      <CollapsibleSection
        title="Snapshots"
        icon={<Camera className="w-4 h-4 text-purple-500" />}
        count={0}
      >
        <p className="text-xs text-muted-foreground italic">
          Snapshots allow you to save and restore context state for debugging.
          Coming soon.
        </p>
      </CollapsibleSection>
    </div>
  );
}
