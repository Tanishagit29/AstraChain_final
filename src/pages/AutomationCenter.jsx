import React, { useState } from 'react';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import { automationRules } from '../data/mockData';
import { Zap, Play, Plus, CheckCircle2 } from 'lucide-react';

export default function AutomationCenter() {
  const [rules, setRules] = useState(automationRules);

  const toggleRule = (id) => {
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, status: r.status === 'ENABLED' ? 'DISABLED' : 'ENABLED' } : r))
    );
  };

  return (
    <div className="space-y-lg">
      <PageHeader
        title="Automation Rules & Guardrails"
        subtitle="Manage trigger-condition-action logic for automated supply chain execution."
        actions={
          <button className="px-md py-sm bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 active:scale-95 transition-all flex items-center gap-xs shadow-lg shadow-primary/20">
            <Plus className="w-4 h-4" />
            <span>Create Automation Rule</span>
          </button>
        }
      />

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
        {rules.map((rule) => (
          <div key={rule.id} className="glass-card rounded-xl p-lg space-y-md flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-sm">
                <div className="flex items-center gap-sm">
                  <div className="w-9 h-9 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20">
                    <Zap className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h4 className="font-title-md text-title-md font-bold text-on-surface">{rule.name}</h4>
                    <span className="font-label-sm text-label-sm text-on-surface-variant font-mono">{rule.id}</span>
                  </div>
                </div>
                <StatusBadge status={rule.status} />
              </div>

              {/* Trigger -> Action Box */}
              <div className="space-y-xs p-md bg-surface-container-low rounded-lg border border-outline-variant/50 text-body-md">
                <div>
                  <span className="text-on-surface-variant font-mono text-[10px] uppercase block">If (Trigger):</span>
                  <p className="font-bold text-tertiary">{rule.trigger}</p>
                </div>
                <div className="pt-xs border-t border-outline-variant/30">
                  <span className="text-on-surface-variant font-mono text-[10px] uppercase block">Then (Action):</span>
                  <p className="font-bold text-primary">{rule.action}</p>
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center pt-md border-t border-outline-variant/30">
              <span className="font-label-sm text-label-sm text-on-surface-variant">
                Executions today: <strong className="text-on-surface font-mono">{rule.executionsToday}</strong>
              </span>

              <button
                onClick={() => toggleRule(rule.id)}
                className={`px-md py-xs rounded font-label-md text-label-md transition-colors font-bold ${
                  rule.status === 'ENABLED'
                    ? 'bg-surface-container-high border border-outline-variant text-on-surface hover:bg-surface-container-highest'
                    : 'bg-primary text-on-primary hover:opacity-90'
                }`}
              >
                {rule.status === 'ENABLED' ? 'Disable Rule' : 'Enable Rule'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
