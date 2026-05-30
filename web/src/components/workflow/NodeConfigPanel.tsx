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

interface Condition {
  id: string;
  outputPort: string;
  evaluatorType: 'prompt' | 'regex' | 'json_path';
  evaluatorConfig: Record<string, unknown>;
}

function ConditionConfigPanel({
  condition,
  onChange,
}: {
  condition: Condition;
  onChange: (config: Record<string, unknown>) => void;
}) {
  const config = condition.evaluatorConfig;

  switch (condition.evaluatorType) {
    case 'regex':
      return (
        <div className="space-y-2 mt-2 pl-3 border-l-2 border-amber-500/30">
          <InputField
            label="Pattern"
            value={(config.pattern as string) ?? ''}
            onChange={(v) => onChange({ ...config, pattern: v })}
            placeholder="success|completed"
          />
          <InputField
            label="Input Path"
            value={(config.input_path as string) ?? ''}
            onChange={(v) => onChange({ ...config, input_path: v })}
            placeholder="agent_1.output"
          />
          <InputField
            label="Flags (i=ignore case, m=multiline)"
            value={(config.flags as string) ?? ''}
            onChange={(v) => onChange({ ...config, flags: v })}
            placeholder="i"
          />
        </div>
      );

    case 'json_path':
      return (
        <div className="space-y-2 mt-2 pl-3 border-l-2 border-amber-500/30">
          <InputField
            label="Path"
            value={(config.path as string) ?? ''}
            onChange={(v) => onChange({ ...config, path: v })}
            placeholder="agent_1.output.status"
          />
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Operator</label>
            <select
              value={(config.operator as string) ?? 'eq'}
              onChange={(e) => onChange({ ...config, operator: e.target.value })}
              className="w-full px-2 py-1 text-xs bg-background border border-border rounded"
            >
              <option value="exists">exists</option>
              <option value="eq">equals (==)</option>
              <option value="ne">not equals (!=)</option>
              <option value="gt">greater than (&gt;)</option>
              <option value="lt">less than (&lt;)</option>
              <option value="gte">greater or equal (&gt;=)</option>
              <option value="lte">less or equal (&lt;=)</option>
              <option value="contains">contains</option>
            </select>
          </div>
          {(config.operator as string) !== 'exists' && (
            <InputField
              label="Value"
              value={String(config.value ?? '')}
              onChange={(v) => onChange({ ...config, value: v })}
              placeholder="success"
            />
          )}
        </div>
      );

    case 'prompt':
      return (
        <div className="space-y-2 mt-2 pl-3 border-l-2 border-amber-500/30">
          <TextArea
            label="Prompt (use {{input}} for value)"
            value={(config.prompt as string) ?? ''}
            onChange={(v) => onChange({ ...config, prompt: v })}
            placeholder="Does this indicate success? {{input}}"
            rows={3}
          />
          <InputField
            label="Input Path"
            value={(config.input_path as string) ?? ''}
            onChange={(v) => onChange({ ...config, input_path: v })}
            placeholder="agent_1.output"
          />
          <InputField
            label="True Patterns (comma-separated)"
            value={((config.true_patterns as string[]) ?? ['yes', 'true']).join(', ')}
            onChange={(v) => onChange({ ...config, true_patterns: v.split(',').map((s) => s.trim()).filter(Boolean) })}
            placeholder="yes, true, 1"
          />
        </div>
      );

    default:
      return null;
  }
}

function BranchConfig({ data, onUpdate }: { data: BranchNodeData; onUpdate: (d: Partial<BranchNodeData>) => void }) {
  const addCondition = useCallback(() => {
    const newCondition: Condition = {
      id: `cond-${Date.now()}`,
      outputPort: `port-${(data.conditions?.length ?? 0) + 1}`,
      evaluatorType: 'json_path' as const,
      evaluatorConfig: {
        path: '',
        operator: 'eq',
        value: '',
      },
    };
    onUpdate({ conditions: [...(data.conditions ?? []), newCondition] });
  }, [data.conditions, onUpdate]);

  const removeCondition = useCallback(
    (id: string) => {
      onUpdate({ conditions: (data.conditions ?? []).filter((c) => c.id !== id) });
    },
    [data.conditions, onUpdate]
  );

  const updateCondition = useCallback(
    (id: string, updates: Partial<Condition>) => {
      const updated = (data.conditions ?? []).map((c) =>
        c.id === id ? { ...c, ...updates } : c
      );
      onUpdate({ conditions: updated });
    },
    [data.conditions, onUpdate]
  );

  const updateConditionConfig = useCallback(
    (id: string, config: Record<string, unknown>) => {
      const updated = (data.conditions ?? []).map((c) =>
        c.id === id ? { ...c, evaluatorConfig: config } : c
      );
      onUpdate({ conditions: updated });
    },
    [data.conditions, onUpdate]
  );

  return (
    <>
      <InputField label="Name" value={data.name} onChange={(v) => onUpdate({ name: v })} placeholder="Branch name" />

      <SectionTitle>Default Output</SectionTitle>
      <InputField
        label="Default Port (used when no condition matches)"
        value={data.defaultOutput ?? 'default'}
        onChange={(v) => onUpdate({ defaultOutput: v })}
        placeholder="default"
      />

      <SectionTitle>Conditions (first match wins)</SectionTitle>
      <div className="space-y-3">
        {(data.conditions ?? []).map((cond, index) => (
          <div key={cond.id} className="p-2 bg-muted/30 rounded border border-border/50">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-muted-foreground">#{index + 1}</span>
              <input
                value={cond.outputPort}
                onChange={(e) => updateCondition(cond.id, { outputPort: e.target.value })}
                className="flex-1 px-2 py-1 text-xs bg-background border border-border rounded"
                placeholder="Output port name"
              />
              <select
                value={cond.evaluatorType}
                onChange={(e) => {
                  const newType = e.target.value as Condition['evaluatorType'];
                  // Reset config when changing type
                  const defaultConfig: Record<string, Record<string, unknown>> = {
                    regex: { pattern: '', input_path: '', flags: 'i' },
                    json_path: { path: '', operator: 'eq', value: '' },
                    prompt: { prompt: '', input_path: '', true_patterns: ['yes', 'true'] },
                  };
                  updateCondition(cond.id, {
                    evaluatorType: newType,
                    evaluatorConfig: defaultConfig[newType] ?? {},
                  });
                }}
                className="px-2 py-1 text-xs bg-background border border-border rounded"
              >
                <option value="json_path">JSON Path</option>
                <option value="regex">Regex</option>
                <option value="prompt">AI Prompt</option>
              </select>
              <button
                onClick={() => removeCondition(cond.id)}
                className="p-1 text-destructive hover:bg-destructive/10 rounded"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
            <ConditionConfigPanel
              condition={cond}
              onChange={(config) => updateConditionConfig(cond.id, config)}
            />
          </div>
        ))}
        <button
          onClick={addCondition}
          className="w-full py-2 text-xs text-primary hover:bg-primary/10 rounded border border-dashed border-primary/30"
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
