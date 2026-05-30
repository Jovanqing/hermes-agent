/**
 * WorkflowPage — page for building and executing workflows.
 *
 * Provides:
 * - Visual canvas for creating workflows
 * - Node configuration panel
 * - Workflow execution and monitoring
 */

import { useEffect, useCallback } from 'react';
import { usePageHeader } from '@/contexts/usePageHeader';
import { Save, FolderOpen, Plus } from 'lucide-react';
import { Button } from '@nous-research/ui/ui/components/button';

import {
  WorkflowCanvas,
  NodeConfigPanel,
  useWorkflowStore,
  selectSelectedNode,
} from '@/components/workflow';

// ---------------------------------------------------------------------------
// WorkflowPage
// ---------------------------------------------------------------------------

export default function WorkflowPage() {
  const { setTitle } = usePageHeader();

  const {
    workflowName,
    setWorkflowName,
    nodes,
    edges,
  } = useWorkflowStore();

  const selectedNode = useWorkflowStore(selectSelectedNode);

  // Set page title
  useEffect(() => {
    setTitle(workflowName || 'Workflows');
  }, [setTitle, workflowName]);

  // Handle execute
  const handleExecute = useCallback(async () => {
    // TODO: Call backend API to execute workflow
    console.log('Executing workflow:', { nodes, edges });

    // Simulate execution for now
    const store = useWorkflowStore.getState();
    store.setExecutionState('running');
    store.setExecutionId(`exec-${Date.now()}`);

    // Simulate node execution
    for (const node of nodes) {
      if (store.executionState === 'cancelled') break;

      store.setNodeStatus(node.id, 'running');
      await new Promise((resolve) => setTimeout(resolve, 500));
      store.setNodeStatus(node.id, 'completed');
      store.setNodeExecutionTime(node.id, 0.5 + Math.random() * 2);
    }

    store.setExecutionState('completed');
  }, [nodes, edges]);

  // Handle stop
  const handleStop = useCallback(() => {
    const store = useWorkflowStore.getState();
    store.setExecutionState('cancelled');
  }, []);

  // Handle new workflow
  const handleNew = useCallback(() => {
    const store = useWorkflowStore.getState();
    store.resetWorkflow();
  }, []);

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

          <div className="flex-1" />

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

        {/* Canvas */}
        <div className="flex-1 min-h-0">
          <WorkflowCanvas
            onExecute={handleExecute}
            onStop={handleStop}
          />
        </div>
      </div>

      {/* Config panel */}
      {selectedNode && <NodeConfigPanel />}
    </div>
  );
}
