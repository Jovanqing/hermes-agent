/**
 * useWorkflowStream — React hook for SSE streaming of workflow events.
 *
 * Connects to the backend SSE endpoint and dispatches events
 * to the workflow store for real-time UI updates.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useWorkflowStore } from '@/components/workflow';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type StreamEventType =
  | 'workflow.started'
  | 'workflow.completed'
  | 'workflow.failed'
  | 'workflow.paused'
  | 'workflow.resumed'
  | 'workflow.cancelled'
  | 'node.started'
  | 'node.completed'
  | 'node.failed'
  | 'node.skipped'
  | 'token'
  | 'token.complete'
  | 'state.changed'
  | 'breakpoint.hit'
  | 'error'
  | 'keepalive';

export interface StreamEvent {
  type: StreamEventType;
  execution_id: string;
  data: Record<string, unknown>;
  timestamp: string;
  sequence: number;
}

export interface UseWorkflowStreamOptions {
  /** Base URL for the API (defaults to current origin) */
  apiBaseUrl?: string;
  /** Whether to automatically reconnect on disconnect */
  autoReconnect?: boolean;
  /** Maximum reconnection attempts */
  maxReconnectAttempts?: number;
  /** Delay between reconnection attempts (ms) */
  reconnectDelay?: number;
  /** Callback for each event */
  onEvent?: (event: StreamEvent) => void;
  /** Callback for errors */
  onError?: (error: Error) => void;
  /** Callback when connection state changes */
  onConnectionChange?: (connected: boolean) => void;
}

export interface UseWorkflowStreamResult {
  /** Whether currently connected to the stream */
  isConnected: boolean;
  /** Whether currently connecting */
  isConnecting: boolean;
  /** Last error that occurred */
  error: Error | null;
  /** Number of reconnection attempts */
  reconnectAttempts: number;
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect from the stream */
  disconnect: () => void;
}

// ---------------------------------------------------------------------------
// Connection state
// ---------------------------------------------------------------------------

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWorkflowStream(
  executionId: string | null,
  options: UseWorkflowStreamOptions = {}
): UseWorkflowStreamResult {
  const {
    apiBaseUrl = '',
    autoReconnect = true,
    maxReconnectAttempts = 5,
    reconnectDelay = 2000,
    onError,
    onConnectionChange,
  } = options;

  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  // Get store actions
  const store = useWorkflowStore;

  // -----------------------------------------------------------------------
  // Event handlers
  // -----------------------------------------------------------------------

  const handleEvent = useCallback((event: StreamEvent) => {
    const state = store.getState();

    switch (event.type) {
      // Workflow lifecycle
      case 'workflow.started':
        state.setExecutionState('running');
        break;

      case 'workflow.completed':
        state.setExecutionState('completed');
        if (event.data.statistics) {
          state.setExecutionStats(event.data.statistics as any);
        }
        break;

      case 'workflow.failed':
        state.setExecutionState('failed');
        if (event.data.error) {
          state.setExecutionError(event.data.error as string);
        }
        break;

      case 'workflow.paused':
        state.setExecutionState('paused');
        break;

      case 'workflow.resumed':
        state.setExecutionState('running');
        break;

      case 'workflow.cancelled':
        state.setExecutionState('cancelled');
        break;

      // Node lifecycle
      case 'node.started':
        if (event.data.node_id) {
          state.setNodeStatus(event.data.node_id as string, 'running');
          state.clearStreamBuffer(event.data.node_id as string);
        }
        break;

      case 'node.completed':
        if (event.data.node_id) {
          const nodeId = event.data.node_id as string;
          state.setNodeStatus(nodeId, 'completed');
          if (event.data.output !== undefined) {
            state.setNodeOutput(nodeId, event.data.output);
          }
          if (event.data.duration !== undefined) {
            state.setNodeExecutionTime(nodeId, event.data.duration as number);
          }
        }
        break;

      case 'node.failed':
        if (event.data.node_id) {
          const nodeId = event.data.node_id as string;
          state.setNodeStatus(nodeId, 'error');
          if (event.data.error) {
            state.setNodeError(nodeId, event.data.error as string);
          }
        }
        break;

      case 'node.skipped':
        if (event.data.node_id) {
          state.setNodeStatus(event.data.node_id as string, 'skipped');
        }
        break;

      // Token streaming
      case 'token':
        if (event.data.node_id && event.data.token) {
          state.appendStreamToken(
            event.data.node_id as string,
            event.data.token as string
          );
        }
        break;

      case 'token.complete':
        if (event.data.node_id && event.data.full_output) {
          state.setNodeOutput(
            event.data.node_id as string,
            event.data.full_output
          );
        }
        break;

      // State changes
      case 'state.changed':
        // Already handled by specific workflow events
        break;

      // Breakpoints
      case 'breakpoint.hit':
        state.setExecutionState('paused');
        break;

      // Errors
      case 'error':
        if (event.data.error) {
          state.setExecutionError(event.data.error as string);
        }
        break;

      // Keepalive - no action needed
      case 'keepalive':
        break;
    }

    // Call custom handler
    optionsRef.current.onEvent?.(event);
  }, [store]);

  // -----------------------------------------------------------------------
  // Connection management
  // -----------------------------------------------------------------------

  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setConnectionState('disconnected');
    onConnectionChange?.(false);
  }, [onConnectionChange]);

  const connect = useCallback(() => {
    if (!executionId) return;

    // Clean up existing connection
    disconnect();

    setConnectionState('connecting');

    const url = `${apiBaseUrl}/api/workflow/executions/${executionId}/stream`;

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      // Connection opened
      eventSource.onopen = () => {
        setConnectionState('connected');
        setError(null);
        setReconnectAttempts(0);
        onConnectionChange?.(true);
      };

      // Handle all event types
      const eventTypes: StreamEventType[] = [
        'workflow.started',
        'workflow.completed',
        'workflow.failed',
        'workflow.paused',
        'workflow.resumed',
        'workflow.cancelled',
        'node.started',
        'node.completed',
        'node.failed',
        'node.skipped',
        'token',
        'token.complete',
        'state.changed',
        'breakpoint.hit',
        'error',
        'keepalive',
      ];

      for (const eventType of eventTypes) {
        eventSource.addEventListener(eventType, (e: MessageEvent) => {
          try {
            const event: StreamEvent = JSON.parse(e.data);
            handleEvent(event);
          } catch (err) {
            console.error('Failed to parse SSE event:', err);
          }
        });
      }

      // Error handling
      eventSource.onerror = () => {
        const err = new Error('SSE connection error');
        setError(err);
        setConnectionState('error');
        onConnectionChange?.(false);
        onError?.(err);

        // Close the errored connection
        eventSource.close();
        eventSourceRef.current = null;

        // Attempt reconnection
        if (autoReconnect && reconnectAttempts < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(1.5, reconnectAttempts);
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts((prev) => prev + 1);
            connect();
          }, delay);
        }
      };
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      setConnectionState('error');
      onError?.(error);
    }
  }, [
    executionId,
    apiBaseUrl,
    autoReconnect,
    maxReconnectAttempts,
    reconnectDelay,
    reconnectAttempts,
    disconnect,
    handleEvent,
    onConnectionChange,
    onError,
  ]);

  // -----------------------------------------------------------------------
  // Auto-connect on execution ID change
  // -----------------------------------------------------------------------

  useEffect(() => {
    if (executionId) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [executionId, connect, disconnect]);

  // -----------------------------------------------------------------------
  // Return value
  // -----------------------------------------------------------------------

  return {
    isConnected: connectionState === 'connected',
    isConnecting: connectionState === 'connecting',
    error,
    reconnectAttempts,
    reconnect: connect,
    disconnect,
  };
}

// ---------------------------------------------------------------------------
// Utility: create execution and start streaming
// ---------------------------------------------------------------------------

export async function startWorkflowExecution(
  workflowId: string,
  inputVariables?: Record<string, unknown>,
  apiBaseUrl = ''
): Promise<{ executionId: string }> {
  const response = await fetch(`${apiBaseUrl}/api/workflow/${workflowId}/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ input_variables: inputVariables }),
  });

  if (!response.ok) {
    throw new Error(`Failed to start execution: ${response.statusText}`);
  }

  const data = await response.json();
  return { executionId: data.execution_id };
}
