import React from 'react';
import { Cpu, Activity, Zap, CheckCircle2, Clock } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function AgentCard({ agent, onTrigger }) {
  return (
    <div className="glass-card rounded-xl p-lg flex flex-col justify-between group">
      <div>
        {/* Agent Name & Header */}
        <div className="flex justify-between items-start mb-md">
          <div className="flex items-center gap-md">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20">
              <Cpu className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h4 className="font-title-md text-title-md font-bold text-on-surface">{agent.name}</h4>
              <p className="font-label-sm text-label-sm text-on-surface-variant">{agent.role}</p>
            </div>
          </div>
          <StatusBadge status={agent.status} />
        </div>

        {/* Telemetry Metrics Grid */}
        <div className="grid grid-cols-3 gap-xs p-sm bg-surface-container-low rounded-lg border border-outline-variant/60 mb-md text-center">
          <div>
            <p className="text-[10px] text-on-surface-variant font-mono uppercase">Confidence</p>
            <p className="text-body-md font-bold font-mono text-primary">{agent.confidence}</p>
          </div>
          <div>
            <p className="text-[10px] text-on-surface-variant font-mono uppercase">Tasks Processed</p>
            <p className="text-body-md font-bold font-mono text-on-surface">{agent.tasksProcessed.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-[10px] text-on-surface-variant font-mono uppercase">Avg Latency</p>
            <p className="text-body-md font-bold font-mono text-secondary">{agent.latency}</p>
          </div>
        </div>

        {/* Last Action Stream */}
        <div className="p-sm bg-surface-container/50 rounded-lg border border-outline-variant/30 text-label-sm text-on-surface-variant flex items-start gap-xs">
          <Activity className="w-4 h-4 text-primary shrink-0 mt-0.5" />
          <p className="line-clamp-2">{agent.lastAction}</p>
        </div>
      </div>

      {/* Trigger Manual Action */}
      <button
        onClick={() => onTrigger && onTrigger(agent)}
        className="mt-lg w-full py-xs bg-surface-container-high border border-outline-variant hover:bg-surface-container-highest rounded font-label-md text-label-md text-on-surface transition-all flex items-center justify-center gap-xs font-bold"
      >
        <Zap className="w-3.5 h-3.5 text-primary" />
        <span>Run Diagnostic</span>
      </button>
    </div>
  );
}
