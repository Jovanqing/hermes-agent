/**
 * OutputNode — custom React Flow node for workflow results.
 *
 * Collects and formats the final output of a workflow.
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { LogOut, CheckCircle2 } from 'lucide-react';
import type { OutputNodeData, NodeStatus } from '../WorkflowStore';

const STATUS_STYLES: Record<NodeStatus, string> = {
  idle: 'border-border bg-card',
  running: 'border-primary/60 bg-primary/[0.04]',
  completed: 'border-green-500/60 bg-green-500/[0.04]',
  error: 'border-destructive/60 bg-destructive/[0.04]',
  skipped: 'border-muted bg-muted/40 opacity-60',
};

function OutputNodeComponent({ data, selected }: NodeProps) {
  const outputData = data as unknown as OutputNodeData;
  const status = outputData.status ?? 'idle';
  const mappingKeys = Object.keys(outputData.outputMapping ?? {});

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
        <LogOut className="w-4 h-4 text-purple-500 shrink-0" />
        <span className="font-medium text-sm truncate flex-1">
          {outputData.name || 'Output'}
        </span>
        {status === 'completed' && (
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        {mappingKeys.length > 0 ? (
          <div className="space-y-1">
            <span className="text-xs text-muted-foreground">Outputs:</span>
            <div className="flex flex-wrap gap-1">
              {mappingKeys.map((key) => (
                <span
                  key={key}
                  className="text-xs bg-purple-500/10 text-purple-500 px-1.5 py-0.5 rounded font-mono"
                >
                  {key}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground italic">
            No output mapping
          </span>
        )}

        {/* Format badge */}
        {outputData.format && (
          <div className="mt-2">
            <span className="text-xs bg-muted px-1.5 py-0.5 rounded">
              {outputData.format}
            </span>
          </div>
        )}
      </div>

      {/* Target handle only (output nodes have no outgoing edges) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-purple-500 !border-2 !border-background"
      />
    </div>
  );
}

export const OutputNode = memo(OutputNodeComponent);
