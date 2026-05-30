/**
 * ExecutionHistory — component for viewing past workflow executions.
 *
 * Displays:
 * - List of past executions
 * - Status, duration, and statistics
 * - Ability to view details and replay
 */

import { useState, useCallback } from 'react';
import {
  Clock,
  CheckCircle2,
  XCircle,
  Play,
  ChevronRight,
  RefreshCw,
  Calendar,
  BarChart3,
  Trash2,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExecutionRecord {
  id: string;
  workflowId: string;
  workflowName: string;
  status: 'completed' | 'failed' | 'cancelled' | 'running';
  startedAt: string;
  completedAt?: string;
  duration: number;
  nodesExecuted: number;
  nodesSuccessful: number;
  nodesFailed: number;
  error?: string;
  inputVariables?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Status styling
// ---------------------------------------------------------------------------

const STATUS_CONFIG = {
  completed: {
    icon: CheckCircle2,
    color: 'text-green-500',
    bg: 'bg-green-500/10',
    label: 'Completed',
  },
  failed: {
    icon: XCircle,
    color: 'text-destructive',
    bg: 'bg-destructive/10',
    label: 'Failed',
  },
  cancelled: {
    icon: XCircle,
    color: 'text-muted-foreground',
    bg: 'bg-muted',
    label: 'Cancelled',
  },
  running: {
    icon: RefreshCw,
    color: 'text-primary',
    bg: 'bg-primary/10',
    label: 'Running',
  },
};

// ---------------------------------------------------------------------------
// Time formatting
// ---------------------------------------------------------------------------

function formatDuration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);

  if (diffSecs < 60) return 'just now';
  if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
  if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
  if (diffSecs < 604800) return `${Math.floor(diffSecs / 86400)}d ago`;

  return date.toLocaleDateString();
}

// ---------------------------------------------------------------------------
// Execution item
// ---------------------------------------------------------------------------

interface ExecutionItemProps {
  execution: ExecutionRecord;
  onSelect: (execution: ExecutionRecord) => void;
  onReplay?: (execution: ExecutionRecord) => void;
  selected?: boolean;
}

function ExecutionItem({ execution, onSelect, onReplay, selected }: ExecutionItemProps) {
  const config = STATUS_CONFIG[execution.status];
  const Icon = config.icon;

  return (
    <div
      className={`
        flex items-center gap-3 px-3 py-2 rounded cursor-pointer
        transition-colors border
        ${selected ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-muted/50'}
      `}
      onClick={() => onSelect(execution)}
    >
      {/* Status icon */}
      <div className={`p-1.5 rounded ${config.bg}`}>
        <Icon className={`w-4 h-4 ${config.color} ${execution.status === 'running' ? 'animate-spin' : ''}`} />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">
            {execution.workflowName || 'Untitled'}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}>
            {config.label}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {formatRelativeTime(execution.startedAt)}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDuration(execution.duration)}
          </span>
          <span className="flex items-center gap-1">
            <BarChart3 className="w-3 h-3" />
            {execution.nodesSuccessful}/{execution.nodesExecuted}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {onReplay && execution.status !== 'running' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onReplay(execution);
            }}
            className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded"
            title="Replay execution"
          >
            <Play className="w-3.5 h-3.5" />
          </button>
        )}
        <ChevronRight className="w-4 h-4 text-muted-foreground" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Execution details
// ---------------------------------------------------------------------------

interface ExecutionDetailsProps {
  execution: ExecutionRecord;
  onReplay?: (execution: ExecutionRecord) => void;
  onDelete?: (execution: ExecutionRecord) => void;
  onClose: () => void;
}

function ExecutionDetails({ execution, onReplay, onDelete, onClose }: ExecutionDetailsProps) {
  const config = STATUS_CONFIG[execution.status];
  const Icon = config.icon;

  return (
    <div className="border-l border-border h-full overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${config.color}`} />
          <h3 className="font-medium">{execution.workflowName}</h3>
        </div>
        <p className="text-xs text-muted-foreground mt-1 font-mono">{execution.id}</p>
      </div>

      {/* Stats */}
      <div className="p-4 border-b border-border">
        <h4 className="text-xs font-medium text-muted-foreground uppercase mb-2">Statistics</h4>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-muted/30 rounded p-2">
            <div className="text-xs text-muted-foreground">Duration</div>
            <div className="text-sm font-medium">{formatDuration(execution.duration)}</div>
          </div>
          <div className="bg-muted/30 rounded p-2">
            <div className="text-xs text-muted-foreground">Status</div>
            <div className={`text-sm font-medium ${config.color}`}>{config.label}</div>
          </div>
          <div className="bg-muted/30 rounded p-2">
            <div className="text-xs text-muted-foreground">Nodes</div>
            <div className="text-sm font-medium">
              {execution.nodesSuccessful}/{execution.nodesExecuted} succeeded
            </div>
          </div>
          <div className="bg-muted/30 rounded p-2">
            <div className="text-xs text-muted-foreground">Failed</div>
            <div className={`text-sm font-medium ${execution.nodesFailed > 0 ? 'text-destructive' : ''}`}>
              {execution.nodesFailed}
            </div>
          </div>
        </div>
      </div>

      {/* Error */}
      {execution.error && (
        <div className="p-4 border-b border-border">
          <h4 className="text-xs font-medium text-muted-foreground uppercase mb-2">Error</h4>
          <pre className="text-xs font-mono bg-destructive/10 text-destructive p-2 rounded whitespace-pre-wrap break-all">
            {execution.error}
          </pre>
        </div>
      )}

      {/* Input variables */}
      {execution.inputVariables && Object.keys(execution.inputVariables).length > 0 && (
        <div className="p-4 border-b border-border">
          <h4 className="text-xs font-medium text-muted-foreground uppercase mb-2">Input Variables</h4>
          <pre className="text-xs font-mono bg-muted/30 p-2 rounded whitespace-pre-wrap break-all">
            {JSON.stringify(execution.inputVariables, null, 2)}
          </pre>
        </div>
      )}

      {/* Actions */}
      <div className="p-4 flex gap-2">
        {onReplay && execution.status !== 'running' && (
          <button
            onClick={() => onReplay(execution)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90"
          >
            <Play className="w-3 h-3" />
            Replay
          </button>
        )}
        {onDelete && (
          <button
            onClick={() => onDelete(execution)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
          >
            <Trash2 className="w-3 h-3" />
            Delete
          </button>
        )}
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-muted text-foreground rounded hover:bg-muted/80 ml-auto"
        >
          Close
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface ExecutionHistoryProps {
  executions: ExecutionRecord[];
  onSelect?: (execution: ExecutionRecord) => void;
  onReplay?: (execution: ExecutionRecord) => void;
  onDelete?: (execution: ExecutionRecord) => void;
  onRefresh?: () => void;
  loading?: boolean;
  className?: string;
}

export function ExecutionHistory({
  executions,
  onSelect,
  onReplay,
  onDelete,
  onRefresh,
  loading = false,
  className = '',
}: ExecutionHistoryProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedExecution = executions.find((e) => e.id === selectedId);

  const handleSelect = useCallback(
    (execution: ExecutionRecord) => {
      setSelectedId(execution.id);
      onSelect?.(execution);
    },
    [onSelect]
  );

  const handleClose = useCallback(() => {
    setSelectedId(null);
  }, []);

  return (
    <div className={`flex h-full ${className}`}>
      {/* List */}
      <div className={`flex-1 flex flex-col min-w-0 ${selectedExecution ? 'w-1/2' : 'w-full'}`}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <h3 className="text-sm font-medium">Execution History</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {executions.length} execution{executions.length !== 1 ? 's' : ''}
            </span>
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={loading}
                className="p-1 text-muted-foreground hover:text-foreground rounded disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loading && executions.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
              Loading...
            </div>
          ) : executions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <Clock className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">No executions yet</p>
            </div>
          ) : (
            executions.map((execution) => (
              <ExecutionItem
                key={execution.id}
                execution={execution}
                onSelect={handleSelect}
                onReplay={onReplay}
                selected={execution.id === selectedId}
              />
            ))
          )}
        </div>
      </div>

      {/* Details panel */}
      {selectedExecution && (
        <div className="w-1/2">
          <ExecutionDetails
            execution={selectedExecution}
            onReplay={onReplay}
            onDelete={onDelete}
            onClose={handleClose}
          />
        </div>
      )}
    </div>
  );
}
