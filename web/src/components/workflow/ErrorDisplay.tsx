/**
 * ErrorDisplay — component for displaying workflow execution errors.
 *
 * Shows:
 * - Error category and type
 * - Error message with details
 * - Retry recommendation
 * - Suggested user action
 */

import { useState } from 'react';
import {
  AlertTriangle,
  XCircle,
  Info,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ErrorCategory =
  | 'rate_limit'
  | 'timeout'
  | 'network'
  | 'temporary_unavailable'
  | 'authentication'
  | 'permission'
  | 'not_found'
  | 'invalid_input'
  | 'quota_exceeded'
  | 'validation'
  | 'syntax'
  | 'configuration'
  | 'internal'
  | 'resource_exhausted'
  | 'unknown';

export interface ErrorInfo {
  category: ErrorCategory;
  errorType: string;
  message: string;
  retryRecommended: boolean;
  userAction: string;
  isTransient: boolean;
  isUserError: boolean;
  details?: Record<string, unknown>;
  stack?: string;
}

// ---------------------------------------------------------------------------
// Category styling
// ---------------------------------------------------------------------------

const CATEGORY_STYLES: Record<ErrorCategory, { bg: string; text: string; icon: string }> = {
  rate_limit: { bg: 'bg-amber-500/10', text: 'text-amber-500', icon: '⏱️' },
  timeout: { bg: 'bg-amber-500/10', text: 'text-amber-500', icon: '⏰' },
  network: { bg: 'bg-blue-500/10', text: 'text-blue-500', icon: '🌐' },
  temporary_unavailable: { bg: 'bg-blue-500/10', text: 'text-blue-500', icon: '🔄' },
  authentication: { bg: 'bg-red-500/10', text: 'text-red-500', icon: '🔐' },
  permission: { bg: 'bg-red-500/10', text: 'text-red-500', icon: '🚫' },
  not_found: { bg: 'bg-gray-500/10', text: 'text-gray-500', icon: '🔍' },
  invalid_input: { bg: 'bg-orange-500/10', text: 'text-orange-500', icon: '❌' },
  quota_exceeded: { bg: 'bg-red-500/10', text: 'text-red-500', icon: '📊' },
  validation: { bg: 'bg-orange-500/10', text: 'text-orange-500', icon: '⚠️' },
  syntax: { bg: 'bg-orange-500/10', text: 'text-orange-500', icon: '📝' },
  configuration: { bg: 'bg-purple-500/10', text: 'text-purple-500', icon: '⚙️' },
  internal: { bg: 'bg-red-500/10', text: 'text-red-500', icon: '💥' },
  resource_exhausted: { bg: 'bg-red-500/10', text: 'text-red-500', icon: '🔥' },
  unknown: { bg: 'bg-gray-500/10', text: 'text-gray-500', icon: '❓' },
};

const CATEGORY_LABELS: Record<ErrorCategory, string> = {
  rate_limit: 'Rate Limited',
  timeout: 'Timeout',
  network: 'Network Error',
  temporary_unavailable: 'Service Unavailable',
  authentication: 'Authentication Failed',
  permission: 'Permission Denied',
  not_found: 'Not Found',
  invalid_input: 'Invalid Input',
  quota_exceeded: 'Quota Exceeded',
  validation: 'Validation Error',
  syntax: 'Syntax Error',
  configuration: 'Configuration Error',
  internal: 'Internal Error',
  resource_exhausted: 'Resource Exhausted',
  unknown: 'Unknown Error',
};

// ---------------------------------------------------------------------------
// Error display component
// ---------------------------------------------------------------------------

interface ErrorDisplayProps {
  error: ErrorInfo;
  onRetry?: () => void;
  onDismiss?: () => void;
  compact?: boolean;
  className?: string;
}

export function ErrorDisplay({
  error,
  onRetry,
  onDismiss,
  compact = false,
  className = '',
}: ErrorDisplayProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(false);

  const style = CATEGORY_STYLES[error.category];
  const label = CATEGORY_LABELS[error.category];

  const handleCopy = async () => {
    const text = JSON.stringify(error, null, 2);
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 rounded ${style.bg} ${className}`}>
        <span className="text-sm">{style.icon}</span>
        <span className={`text-sm font-medium ${style.text}`}>{label}</span>
        <span className="text-xs text-muted-foreground truncate flex-1">
          {error.message.slice(0, 50)}
          {error.message.length > 50 ? '...' : ''}
        </span>
        {error.retryRecommended && onRetry && (
          <button
            onClick={onRetry}
            className="p-1 hover:bg-background/50 rounded"
            title="Retry"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`rounded-lg border border-border overflow-hidden ${className}`}>
      {/* Header */}
      <div className={`flex items-start gap-3 px-4 py-3 ${style.bg}`}>
        <span className="text-xl">{style.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className={`font-medium ${style.text}`}>{label}</h4>
            <span className="text-xs text-muted-foreground bg-background/50 px-1.5 py-0.5 rounded">
              {error.errorType}
            </span>
          </div>
          <p className="text-sm text-foreground mt-1 break-words">{error.message}</p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 text-muted-foreground hover:text-foreground rounded"
          >
            <XCircle className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* User action suggestion */}
      {error.userAction && (
        <div className="flex items-start gap-2 px-4 py-2 bg-muted/30 border-t border-border/50">
          <Info className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground">{error.userAction}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 px-4 py-2 border-t border-border/50">
        {error.retryRecommended && onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        )}

        {error.isTransient && (
          <span className="text-xs text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded">
            Transient - may resolve on retry
          </span>
        )}

        {error.isUserError && (
          <span className="text-xs text-orange-500 bg-orange-500/10 px-2 py-0.5 rounded">
            User error - check input
          </span>
        )}

        <div className="flex-1" />

        <button
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          {showDetails ? (
            <ChevronDown className="w-3 h-3" />
          ) : (
            <ChevronRight className="w-3 h-3" />
          )}
          Details
        </button>

        <button
          onClick={handleCopy}
          className="p-1 text-muted-foreground hover:text-foreground rounded"
          title="Copy error details"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-green-500" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* Details panel */}
      {showDetails && (
        <div className="border-t border-border bg-muted/20 p-3">
          <pre className="text-xs font-mono whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
            {JSON.stringify(error.details || error, null, 2)}
          </pre>
          {error.stack && (
            <>
              <h5 className="text-xs font-medium text-muted-foreground mt-3 mb-1">
                Stack Trace
              </h5>
              <pre className="text-xs font-mono whitespace-pre-wrap break-all max-h-32 overflow-y-auto text-muted-foreground">
                {error.stack}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error list component
// ---------------------------------------------------------------------------

interface ErrorListProps {
  errors: ErrorInfo[];
  onRetry?: (index: number) => void;
  onDismiss?: (index: number) => void;
  className?: string;
}

export function ErrorList({ errors, onRetry, onDismiss, className = '' }: ErrorListProps) {
  if (errors.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {errors.map((error, index) => (
        <ErrorDisplay
          key={index}
          error={error}
          onRetry={onRetry ? () => onRetry(index) : undefined}
          onDismiss={onDismiss ? () => onDismiss(index) : undefined}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline error badge
// ---------------------------------------------------------------------------

interface ErrorBadgeProps {
  message: string;
  category?: ErrorCategory;
  onClick?: () => void;
}

export function ErrorBadge({ message, category = 'unknown', onClick }: ErrorBadgeProps) {
  const style = CATEGORY_STYLES[category];

  return (
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs
        ${style.bg} ${style.text}
        hover:opacity-80 transition-opacity
      `}
      title={message}
    >
      <AlertTriangle className="w-3 h-3" />
      <span className="truncate max-w-[150px]">{message}</span>
    </button>
  );
}
