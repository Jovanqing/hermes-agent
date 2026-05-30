/**
 * TransformNode — custom React Flow node for data transformation.
 *
 * Applies transformations to context data without invoking an LLM.
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { ArrowRightLeft } from 'lucide-react';
import type { TransformNodeData, NodeStatus } from '../WorkflowStore';

const STATUS_STYLES: Record<NodeStatus, string> = {
  idle: 'border-border bg-card',
  running: 'border-primary/60 bg-primary/[0.04]',
  completed: 'border-green-500/60 bg-green-500/[0.04]',
  error: 'border-destructive/60 bg-destructive/[0.04]',
  skipped: 'border-muted bg-muted/40 opacity-60',
};

const TRANSFORM_LABEL: Record<string, string> = {
  template: 'Template',
  json_path: 'JSON Path',
  script: 'Script',
};

function TransformNodeComponent({ data, selected }: NodeProps) {
  const transformData = data as unknown as TransformNodeData;
  const status = transformData.status ?? 'idle';

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
        <ArrowRightLeft className="w-4 h-4 text-teal-500 shrink-0" />
        <span className="font-medium text-sm truncate flex-1">
          {transformData.name || 'Transform'}
        </span>
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-xs bg-teal-500/10 text-teal-600 dark:text-teal-400 px-2 py-0.5 rounded">
            {TRANSFORM_LABEL[transformData.transformType] ?? transformData.transformType}
          </span>
        </div>
        {transformData.output != null && status === 'completed' && (
          <div className="mt-2 text-xs bg-green-500/10 rounded p-1.5 font-mono truncate">
            {typeof transformData.output === 'string'
              ? transformData.output.slice(0, 50)
              : JSON.stringify(transformData.output).slice(0, 50)}
          </div>
        )}
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-teal-500 !border-2 !border-background"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-teal-500 !border-2 !border-background"
      />
    </div>
  );
}

export const TransformNode = memo(TransformNodeComponent);
