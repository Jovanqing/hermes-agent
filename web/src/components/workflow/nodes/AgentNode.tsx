/**
 * AgentNode — custom React Flow node for LLM agent execution.
 *
 * Displays:
 * - Node name and model badge
 * - Prompt preview
 * - Streaming output (while running)
 * - Final output (when completed)
 * - Status indicators (idle, running, completed, error)
 */

import { memo, useEffect, useRef, useState } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Bot, Clock, Zap, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import type { AgentNodeData, NodeStatus } from '../WorkflowStore';

// ---------------------------------------------------------------------------
// Status styling
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<NodeStatus, string> = {
  idle: 'border-border bg-card',
  running: 'border-primary/60 bg-primary/[0.04] shadow-primary/10 shadow-md',
  completed: 'border-green-500/60 bg-green-500/[0.04]',
  error: 'border-destructive/60 bg-destructive/[0.04]',
  skipped: 'border-muted bg-muted/40 opacity-60',
};

const STATUS_ICON: Record<NodeStatus, React.ReactNode> = {
  idle: null,
  running: <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />,
  completed: <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />,
  error: <XCircle className="w-3.5 h-3.5 text-destructive" />,
  skipped: null,
};

// ---------------------------------------------------------------------------
// AgentNode component
// ---------------------------------------------------------------------------

function AgentNodeComponent({ data, selected }: NodeProps) {
  const agentData = data as unknown as AgentNodeData;
  const status = agentData.status ?? 'idle';
  const streamRef = useRef<HTMLDivElement>(null);

  // Tick for live elapsed time while running (triggers re-render)
  const [, setNow] = useState(Date.now());
  useEffect(() => {
    if (status !== 'running') return;
    const id = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(id);
  }, [status]);

  // Auto-scroll streaming output
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [agentData.streamBuffer]);

  const promptPreview = agentData.prompt
    ? agentData.prompt.length > 80
      ? agentData.prompt.slice(0, 80) + '...'
      : agentData.prompt
    : 'No prompt configured';

  return (
    <div
      className={`
        rounded-lg border-2 min-w-[260px] max-w-[320px]
        transition-all duration-200
        ${STATUS_STYLES[status]}
        ${selected ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50">
        <Bot className="w-4 h-4 text-primary shrink-0" />
        <span className="font-medium text-sm truncate flex-1">
          {agentData.name || 'Agent'}
        </span>
        {STATUS_ICON[status]}
      </div>

      {/* Body */}
      <div className="px-3 py-2 space-y-2">
        {/* Prompt preview */}
        <div className="text-xs text-muted-foreground line-clamp-2 font-mono">
          {promptPreview}
        </div>

        {/* Streaming output */}
        {status === 'running' && agentData.streamBuffer && (
          <div
            ref={streamRef}
            className="text-xs bg-background/80 rounded p-2 max-h-24 overflow-y-auto font-mono whitespace-pre-wrap"
          >
            {agentData.streamBuffer}
            <span className="inline-block w-1.5 h-3.5 bg-primary/70 animate-pulse ml-0.5" />
          </div>
        )}

        {/* Completed output preview */}
        {status === 'completed' && agentData.output && (
          <div className="text-xs bg-green-500/10 rounded p-2 max-h-24 overflow-y-auto font-mono whitespace-pre-wrap">
            {typeof agentData.output === 'string'
              ? agentData.output.length > 200
                ? agentData.output.slice(0, 200) + '...'
                : agentData.output
              : JSON.stringify(agentData.output, null, 2).slice(0, 200)}
          </div>
        )}

        {/* Error display */}
        {status === 'error' && agentData.error && (
          <div className="text-xs bg-destructive/10 text-destructive rounded p-2 font-mono">
            {agentData.error}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-3 px-3 py-1.5 border-t border-border/50 text-xs text-muted-foreground">
        <Zap className="w-3 h-3" />
        <span className="truncate">{agentData.model || 'no model'}</span>
        {agentData.executionTime != null && (
          <span className="flex items-center gap-1 ml-auto">
            <Clock className="w-3 h-3" />
            {agentData.executionTime.toFixed(1)}s
          </span>
        )}
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-primary !border-2 !border-background"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-primary !border-2 !border-background"
      />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
