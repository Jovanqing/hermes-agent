/**
 * WorkflowPage — page for building and executing workflows.
 *
 * Provides:
 * - Visual canvas for creating workflows
 * - Node configuration panel
 * - Context inspector for debugging
 * - Workflow execution and monitoring with real-time streaming
 */

import { useEffect, useCallback, useState } from 'react';
import { usePageHeader } from '@/contexts/usePageHeader';
import { Save, FolderOpen, Plus, Wifi, WifiOff, Eye } from 'lucide-react';
import { Button } from '@nous-research/ui/ui/components/button';

import {
  WorkflowCanvas,
  NodeConfigPanel,
  ContextViewer,
  useWorkflowStore,
  selectSelectedNode,
} from '@/components/workflow';
import {
  useWorkflowStream,
  startWorkflowExecution,
} from '@/hooks/useWorkflowStream';

// ---------------------------------------------------------------------------
// WorkflowPage
// ---------------------------------------------------------------------------

export default function WorkflowPage() {
  const { setTitle } = usePageHeader();
  const [streamError, setStreamError] = useState<string | null>(null);
  const [showContextViewer, setShowContextViewer] = useState(false);

  const {
    workflowId,
    workflowName,
    setWorkflowName,
    nodes,
    edges,
    executionId,
  } = useWorkflowStore();

  const selectedNode = useWorkflowStore(selectSelectedNode);

  // Connect to SSE stream when execution is active
  const { isConnected, isConnecting, error: streamErr } = useWorkflowStream(
    executionId,
    {
      onEvent: (event) => {
        console.debug('Stream event:', event.type, event.data);
      },
      onError: (err) => {
        setStreamError(err.message);
      },
    }
  );

  // Update stream error display
  useEffect(() => {
    if (streamErr) {
      setStreamError(streamErr.message);
    }
  }, [streamErr]);

  // Set page title
  useEffect(() => {
    setTitle(workflowName || 'Workflows');
  }, [setTitle, workflowName]);

  // Handle execute - uses real API when workflow is saved, falls back to simulation
  const handleExecute = useCallback(async () => {
    const store = useWorkflowStore.getState();
    setStreamError(null);

    // Reset node statuses before execution
    store.resetNodeStatuses();

    // If we have a saved workflow, use the real API
    if (workflowId) {
      try {
        const { executionId: newExecId } = await startWorkflowExecution(
          workflowId,
          {} // TODO: Add input variables UI
        );
        store.setExecutionId(newExecId);
      } catch (err) {
        setStreamError(err instanceof Error ? err.message : String(err));
        store.setExecutionState('failed');
        store.setExecutionError('Failed to start execution');
      }
    } else {
      // Simulate execution for unsaved workflows (demo mode)
      console.log('Simulating execution for unsaved workflow:', { nodes, edges });

      store.setExecutionState('running');
      store.setExecutionId(`sim-${Date.now()}`);

      // Simulate node execution with streaming effect
      for (const node of nodes) {
        if (store.executionState === 'cancelled') break;

        store.setNodeStatus(node.id, 'running');

        // Simulate streaming tokens
        const tokens = ['Processing', ' ', 'node', ' ', `"${node.data.name || node.id}"`, '...'];
        for (const token of tokens) {
          await new Promise((resolve) => setTimeout(resolve, 100));
          store.appendStreamToken(node.id, token);
        }

        await new Promise((resolve) => setTimeout(resolve, 300));
        store.setNodeStatus(node.id, 'completed');
        store.setNodeOutput(node.id, `Output from ${node.data.name || node.id}`);
        store.setNodeExecutionTime(node.id, 0.5 + Math.random() * 2);
      }

      store.setExecutionState('completed');
    }
  }, [workflowId, nodes, edges]);

  // Handle stop
  const handleStop = useCallback(async () => {
    const store = useWorkflowStore.getState();
    const currentExecId = store.executionId;

    if (workflowId && currentExecId && !currentExecId.startsWith('sim-')) {
      // Call API to cancel real execution
      try {
        await fetch(`/api/workflow/executions/${currentExecId}/cancel`, {
          method: 'POST',
        });
      } catch (err) {
        console.error('Failed to cancel execution:', err);
      }
    }

    store.setExecutionState('cancelled');
  }, [workflowId]);

  // Handle new workflow
  const handleNew = useCallback(() => {
    const store = useWorkflowStore.getState();
    store.resetWorkflow();
    setStreamError(null);
  }, []);

  // Determine which side panel to show
  const showSidePanel = selectedNode || showContextViewer;

  return (
    <div className="flex h-full">
      {/* Main canvas area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-card">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="px-2 py-1 text-sm font-medium bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-primary rounded"
            placeholder="Workflow name"
          />

          {/* Connection indicator */}
          {executionId && (
            <div
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                isConnected
                  ? 'bg-green-500/10 text-green-500'
                  : isConnecting
                  ? 'bg-amber-500/10 text-amber-500'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {isConnected ? (
                <Wifi className="w-3 h-3" />
              ) : (
                <WifiOff className="w-3 h-3" />
              )}
              {isConnected ? 'Live' : isConnecting ? 'Connecting...' : 'Disconnected'}
            </div>
          )}

          <div className="flex-1" />

          {/* Context viewer toggle */}
          <Button
            ghost
            size="sm"
            onClick={() => setShowContextViewer(!showContextViewer)}
            className={showContextViewer ? 'bg-primary/10 text-primary' : ''}
          >
            <Eye className="w-4 h-4 mr-1" />
            Context
          </Button>

          <Button ghost size="sm" onClick={handleNew}>
            <Plus className="w-4 h-4 mr-1" />
            New
          </Button>

          <Button ghost size="sm" disabled>
            <FolderOpen className="w-4 h-4 mr-1" />
            Open
          </Button>

          <Button ghost size="sm" disabled>
            <Save className="w-4 h-4 mr-1" />
            Save
          </Button>

          <span className="text-xs text-muted-foreground">
            {nodes.length} node{nodes.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Error banner */}
        {streamError && (
          <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm border-b border-destructive/20">
            {streamError}
          </div>
        )}

        {/* Canvas */}
        <div className="flex-1 min-h-0">
          <WorkflowCanvas
            onExecute={handleExecute}
            onStop={handleStop}
          />
        </div>
      </div>

      {/* Side panel: Node config or Context viewer */}
      {showSidePanel && (
        <div className="w-80 border-l border-border bg-card overflow-y-auto">
          {selectedNode ? (
            <NodeConfigPanel />
          ) : showContextViewer ? (
            <div className="p-4">
              <ContextViewer />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
