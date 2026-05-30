/**
 * BranchNode — custom React Flow node for conditional routing.
 *
 * Evaluates conditions and routes execution to different output ports.
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { GitBranch } from 'lucide-react';
import type { BranchNodeData, NodeStatus } from '../WorkflowStore';

const STATUS_STYLES: Record<NodeStatus, string> = {
  idle: 'border-border bg-card',
  running: 'border-primary/60 bg-primary/[0.04]',
  completed: 'border-green-500/60 bg-green-500/[0.04]',
  error: 'border-destructive/60 bg-destructive/[0.04]',
  skipped: 'border-muted bg-muted/40 opacity-60',
};

const EVALUATOR_LABEL: Record<string, string> = {
  prompt: 'AI',
  regex: 'Regex',
  json_path: 'JSON',
};

function BranchNodeComponent({ data, selected }: NodeProps) {
  const branchData = data as unknown as BranchNodeData;
  const status = branchData.status ?? 'idle';
  const conditions = branchData.conditions ?? [];

  return (
    <div
      className={`
        rounded-lg border-2 min-w-[220px] max-w-[280px]
        transition-all duration-200
        ${STATUS_STYLES[status]}
        ${selected ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50">
        <GitBranch className="w-4 h-4 text-amber-500 shrink-0" />
        <span className="font-medium text-sm truncate flex-1">
          {branchData.name || 'Branch'}
        </span>
        <span className="text-xs text-muted-foreground">
          {conditions.length} condition{conditions.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Body - conditions list */}
      <div className="px-3 py-2 space-y-1">
        {conditions.length > 0 ? (
          conditions.slice(0, 4).map((cond) => (
            <div
              key={cond.id}
              className={`
                flex items-center gap-2 text-xs px-2 py-1 rounded
                ${branchData.selectedPort === cond.outputPort
                  ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400'
                  : 'bg-muted/50 text-muted-foreground'}
              `}
            >
              <span className="bg-amber-500/10 text-amber-600 dark:text-amber-400 px-1 rounded text-[10px]">
                {EVALUATOR_LABEL[cond.evaluatorType] ?? cond.evaluatorType}
              </span>
              <span className="truncate">→ {cond.outputPort}</span>
            </div>
          ))
        ) : (
          <span className="text-xs text-muted-foreground italic">
            No conditions
          </span>
        )}
        {conditions.length > 4 && (
          <span className="text-xs text-muted-foreground">
            +{conditions.length - 4} more
          </span>
        )}
        {branchData.defaultOutput && (
          <div className="text-xs text-muted-foreground mt-1">
            Default: <span className="font-mono">{branchData.defaultOutput}</span>
          </div>
        )}
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-amber-500 !border-2 !border-background"
      />
      {/* Multiple source handles for output ports */}
      {conditions.length > 0 ? (
        conditions.slice(0, 3).map((cond, i) => {
          const total = Math.min(conditions.length, 3);
          const offset = total === 1 ? 50 : 25 + (50 / (total - 1)) * i;
          return (
            <Handle
              key={cond.id}
              id={cond.outputPort}
              type="source"
              position={Position.Right}
              style={{ top: `${offset}%` }}
              className={`!w-3 !h-3 !border-2 !border-background
                ${branchData.selectedPort === cond.outputPort
                  ? '!bg-amber-400'
                  : '!bg-amber-500'}`}
            />
          );
        })
      ) : (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-amber-500 !border-2 !border-background"
        />
      )}
    </div>
  );
}

export const BranchNode = memo(BranchNodeComponent);
