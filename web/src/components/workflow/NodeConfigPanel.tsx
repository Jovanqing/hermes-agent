/**
 * NodeConfigPanel — sidebar panel for editing node configuration.
 *
 * Shows different fields based on node type:
 * - Agent: prompt, model, temperature, tools
 * - Input: variables
 * - Output: output mapping
 * - Branch: conditions
 * - Transform: transform type and config
 */

import { useCallback } from 'react';
import { X, Trash2, Bot, LogIn, LogOut, GitBranch, ArrowRightLeft } from 'lucide-react';
import {
  useWorkflowStore,
  selectSelectedNode,
  type AgentNodeData,
  type InputNodeData,
  type OutputNodeData,
  type BranchNodeData,
  type TransformNodeData,
  type WorkflowNodeData,
} from './WorkflowStore';

// ---------------------------------------------------------------------------
// Common components
// ---------------------------------------------------------------------------

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mt-4 mb-2">
      {children}
    </h4>
  );
}

function InputField({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-muted-foreground">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-2.5 py-1.5 text-sm bg-background border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary"
      />
    </div>
  );
}

function TextArea({
  label,
  value,
  onChange,
  placeholder,
  rows = 4,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-muted-foreground">{label}</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="w-full px-2.5 py-1.5 text-sm bg-background border border-border rounded font-mono focus:outline-none focus:ring-1 focus:ring-primary resize-none"
      />
    </div>
  );
}

function SliderField({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <label className="text-xs text-muted-foreground">{label}</label>
        <span className="text-xs font-mono text-foreground">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-muted rounded appearance-none cursor-pointer"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Agent config
// ---------------------------------------------------------------------------

function AgentConfig({ data, onUpdate }: { data: AgentNodeData; onUpdate: (d: Partial<AgentNodeData>) => void }) {
  return (
    <>
      <InputField label="Name" value={data.name} onChange={(v) => onUpdate({ name: v })} placeholder="Agent name" />

      <SectionTitle>Prompt</SectionTitle>
      <TextArea
        label="System/User Prompt"
        value={data.prompt}
        onChange={(v) => onUpdate({ prompt: v })}
        placeholder="Enter your prompt here. Use {{variable}} for context variables."
        rows={6}
      />

      <SectionTitle>Model</SectionTitle>
      <InputField label="Model" value={data.model} onChange={(v) => onUpdate({ model: v })} placeholder="gpt-4" />

      <div className="grid grid-cols-2 gap-3 mt-3">
        <SliderField
          label="Temperature"
          value={data.temperature ?? 0.7}
          onChange={(v) => onUpdate({ temperature: v })}
          min={0}
          max={2}
          step={0.1}
        />
        <InputField
          label="Max Tokens"
          type="number"
          value={data.maxTokens ?? 4096}
          onChange={(v) => onUpdate({ maxTokens: parseInt(v) || 4096 })}
        />
      </div>

      <SectionTitle>Input Mapping</SectionTitle>
      <TextArea
        label="Mapping (JSON)"
        value={JSON.stringify(data.inputMapping ?? {}, null, 2)}
        onChange={(v) => {
          try {
            onUpdate({ inputMapping: JSON.parse(v) });
          } catch {
            // Invalid JSON, ignore
          }
        }}
        placeholder='{"variable": "source.path"}'
        rows={3}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Input config
// ---------------------------------------------------------------------------

function InputConfig({ data, onUpdate }: { data: InputNodeData; onUpdate: (d: Partial<InputNodeData>) => void }) {
  return (
    <>
      <InputField label="Name" value={data.name} onChange={(v) => onUpdate({ name: v })} placeholder="Input name" />

      <SectionTitle>Variables</SectionTitle>
      <TextArea
        label="Default Variables (JSON)"
        value={JSON.stringify(data.variables ?? {}, null, 2)}
        onChange={(v) => {
          try {
            onUpdate({ variables: JSON.parse(v) });
          } catch {
            // Invalid JSON, ignore
          }
        }}
        placeholder='{"greeting": "Hello"}'
        rows={5}
      />

      <SectionTitle>Required Variables</SectionTitle>
      <InputField
        label="Comma-separated list"
        value={(data.required ?? []).join(', ')}
        onChange={(v) => onUpdate({ required: v.split(',').map((s) => s.trim()).filter(Boolean) })}
        placeholder="var1, var2"
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Output config
// ---------------------------------------------------------------------------

function OutputConfig({ data, onUpdate }: { data: OutputNodeData; onUpdate: (d: Partial<OutputNodeData>) => void }) {
  return (
    <>
      <InputField label="Name" value={data.name} onChange={(v) => onUpdate({ name: v })} placeholder="Output name" />

      <SectionTitle>Output Mapping</SectionTitle>
      <TextArea
        label="Mapping (JSON)"
        value={JSON.stringify(data.outputMapping ?? {}, null, 2)}
        onChange={(v) => {
          try {
            onUpdate({ outputMapping: JSON.parse(v) });
          } catch {
            // Invalid JSON, ignore
          }
        }}
        placeholder='{"result": "agent_1.output"}'
        rows={5}
      />

      <SectionTitle>Format</SectionTitle>
      <select
        value={data.format ?? 'json'}
        onChange={(e) => onUpdate({ format: e.target.value as OutputNodeData['format'] })}
        className="w-full px-2.5 py-1.5 text-sm bg-background border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="json">JSON</option>
        <option value="text">Text</option>
        <option value="markdown">Markdown</option>
      </select>
    </>
  );
}

// ---------------------------------------------------------------------------
// Branch config
// ---------------------------------------------------------------------------

function BranchConfig({ data, onUpdate }: { data: BranchNodeData; onUpdate: (d: Partial<BranchNodeData>) => void }) {
  const addCondition = useCallback(() => {
    const newCondition = {
      id: `cond-${Date.now()}`,
      outputPort: `port-${(data.conditions?.length ?? 0) + 1}`,
      evaluatorType: 'prompt' as const,
      evaluatorConfig: {},
    };
    onUpdate({ conditions: [...(data.conditions ?? []), newCondition] });
  }, [data.conditions, onUpdate]);

  const removeCondition = useCallback(
    (id: string) => {
      onUpdate({ conditions: (data.conditions ?? []).filter((c) => c.id !== id) });
    },
    [data.conditions, onUpdate]
  );

  return (
    <>
      <InputField label="Name" value={data.name} onChange={(v) => onUpdate({ name: v })} placeholder="Branch name" />

      <SectionTitle>Default Output</SectionTitle>
      <InputField
        label="Default Port"
        value={data.defaultOutput ?? 'default'}
        onChange={(v) => onUpdate({ defaultOutput: v })}
        placeholder="default"
      />

      <SectionTitle>Conditions</SectionTitle>
      <div className="space-y-2">
        {(data.conditions ?? []).map((cond) => (
          <div key={cond.id} className="flex items-center gap-2 p-2 bg-muted/50 rounded">
            <input
              value={cond.outputPort}
              onChange={(e) => {
                const updated = (data.conditions ?? []).map((c) =>
                  c.id === cond.id ? { ...c, outputPort: e.target.value } : c
                );
                onUpdate({ conditions: updated });
              }}
              className="flex-1 px-2 py-1 text-xs bg-background border border-border rounded"
              placeholder="Port name"
            />
            <select
              value={cond.evaluatorType}
              onChange={(e) => {
                const updated = (data.conditions ?? []).map((c) =>
                  c.id === cond.id ? { ...c, evaluatorType: e.target.value as typeof cond.evaluatorType } : c
                );
                onUpdate({ conditions: updated });
              }}
              className="px-2 py-1 text-xs bg-background border border-border rounded"
            >
              <option value="prompt">AI</option>
              <option value="regex">Regex</option>
              <option value="json_path">JSON Path</option>
            </select>
            <button
              onClick={() => removeCondition(cond.id)}
              className="p-1 text-destructive hover:bg-destructive/10 rounded"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
        <button
          onClick={addCondition}
          className="w-full py-1.5 text-xs text-primary hover:bg-primary/10 rounded border border-dashed border-primary/30"
        >
          + Add Condition
        </button>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Transform config
// ---------------------------------------------------------------------------

function TransformConfig({ data, onUpdate }: { data: TransformNodeData; onUpdate: (d: Partial<TransformNodeData>) => void }) {
  return (
    <>
      <InputField label="Name" value={data.name} onChange={(v) => onUpdate({ name: v })} placeholder="Transform name" />

      <SectionTitle>Transform Type</SectionTitle>
      <select
        value={data.transformType}
        onChange={(e) => onUpdate({ transformType: e.target.value as TransformNodeData['transformType'] })}
        className="w-full px-2.5 py-1.5 text-sm bg-background border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="template">Template</option>
        <option value="json_path">JSON Path</option>
        <option value="script">Script</option>
      </select>

      <SectionTitle>Configuration</SectionTitle>
      <TextArea
        label="Config (JSON)"
        value={JSON.stringify(data.transformConfig ?? {}, null, 2)}
        onChange={(v) => {
          try {
            onUpdate({ transformConfig: JSON.parse(v) });
          } catch {
            // Invalid JSON, ignore
          }
        }}
        placeholder='{"template": "Hello {{name}}"}'
        rows={5}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Node icon
// ---------------------------------------------------------------------------

const NODE_ICONS: Record<string, React.ReactNode> = {
  agent: <Bot className="w-4 h-4 text-primary" />,
  input: <LogIn className="w-4 h-4 text-blue-500" />,
  output: <LogOut className="w-4 h-4 text-purple-500" />,
  branch: <GitBranch className="w-4 h-4 text-amber-500" />,
  transform: <ArrowRightLeft className="w-4 h-4 text-teal-500" />,
};

const NODE_LABELS: Record<string, string> = {
  agent: 'Agent',
  input: 'Input',
  output: 'Output',
  branch: 'Branch',
  transform: 'Transform',
};

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export function NodeConfigPanel() {
  const selectedNode = useWorkflowStore(selectSelectedNode);
  const selectNode = useWorkflowStore((s) => s.selectNode);
  const updateNodeData = useWorkflowStore((s) => s.updateNodeData);
  const removeNode = useWorkflowStore((s) => s.removeNode);

  if (!selectedNode) return null;

  const nodeData = selectedNode.data as WorkflowNodeData;
  const nodeType = nodeData.type;

  const handleClose = () => selectNode(null);

  const handleUpdate = <T extends WorkflowNodeData>(updates: Partial<T>) => {
    updateNodeData<T>(selectedNode.id, updates);
  };

  const handleDelete = () => {
    removeNode(selectedNode.id);
  };

  return (
    <div className="w-80 h-full border-l border-border bg-card overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-card border-b border-border px-4 py-3 flex items-center gap-2 z-10">
        {NODE_ICONS[nodeType]}
        <span className="font-medium text-sm">{NODE_LABELS[nodeType]} Node</span>
        <div className="ml-auto flex gap-1">
          <button
            onClick={handleDelete}
            className="p-1.5 text-destructive hover:bg-destructive/10 rounded"
            title="Delete node"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleClose}
            className="p-1.5 text-muted-foreground hover:bg-muted rounded"
            title="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Node ID */}
      <div className="px-4 py-2 border-b border-border/50">
        <span className="text-xs text-muted-foreground font-mono">{selectedNode.id}</span>
      </div>

      {/* Config fields */}
      <div className="p-4 space-y-3">
        {nodeType === 'agent' && (
          <AgentConfig data={nodeData as AgentNodeData} onUpdate={handleUpdate} />
        )}
        {nodeType === 'input' && (
          <InputConfig data={nodeData as InputNodeData} onUpdate={handleUpdate} />
        )}
        {nodeType === 'output' && (
          <OutputConfig data={nodeData as OutputNodeData} onUpdate={handleUpdate} />
        )}
        {nodeType === 'branch' && (
          <BranchConfig data={nodeData as BranchNodeData} onUpdate={handleUpdate} />
        )}
        {nodeType === 'transform' && (
          <TransformConfig data={nodeData as TransformNodeData} onUpdate={handleUpdate} />
        )}
      </div>
    </div>
  );
}
