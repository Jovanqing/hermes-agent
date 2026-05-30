/**
 * InputNode — custom React Flow node for workflow entry points.
 *
 * Defines the initial variables available to the workflow.
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { LogIn } from 'lucide-react';
import type { InputNodeData, NodeStatus } from '../WorkflowStore';

const STATUS_STYLES: Record<NodeStatus, string> = {
  idle: 'border-border bg-card',
  running: 'border-primary/60 bg-primary/[0.04]',
  completed: 'border-green-500/60 bg-green-500/[0.04]',
  error: 'border-destructive/60 bg-destructive/[0.04]',
  skipped: 'border-muted bg-muted/40 opacity-60',
};

function InputNodeComponent({ data, selected }: NodeProps) {
  const inputData = data as unknown as InputNodeData;
  const status = inputData.status ?? 'idle';
  const varKeys = Object.keys(inputData.variables ?? {});

  return (
    <div
      className={`
        rounded-lg border-2 min-w-[200px] max-w-[260px]
        transition-all duration-200
        ${STATUS_STYLES[status]}
        ${selected ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50">
        <LogIn className="w-4 h-4 text-blue-500 shrink-0" />
        <span className="font-medium text-sm truncate flex-1">
          {inputData.name || 'Input'}
        </span>
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        {varKeys.length > 0 ? (
          <div className="space-y-1">
            <span className="text-xs text-muted-foreground">Variables:</span>
            <div className="flex flex-wrap gap-1">
              {varKeys.slice(0, 5).map((key) => (
                <span
                  key={key}
                  className="text-xs bg-blue-500/10 text-blue-500 px-1.5 py-0.5 rounded font-mono"
                >
                  {key}
                </span>
              ))}
              {varKeys.length > 5 && (
                <span className="text-xs text-muted-foreground">
                  +{varKeys.length - 5} more
                </span>
              )}
            </div>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground italic">
            No variables defined
          </span>
        )}
      </div>

      {/* Source handle only (input nodes have no incoming edges) */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-background"
      />
    </div>
  );
}

export const InputNode = memo(InputNodeComponent);
