import React, { useState, useEffect } from 'react';
import PageHeader from '../components/PageHeader';
import AgentCard from '../components/AgentCard';
import KPICard from '../components/KPICard';
import { api } from '../api/client';
import { aiAgents as fallbackAgents } from '../data/mockData';
import { Cpu, Activity, ShieldCheck, Zap } from 'lucide-react';

export default function AgentActivity() {
  const [agents, setAgents] = useState(fallbackAgents);

  useEffect(() => {
    let isMounted = true;
    api.getAIAgents().then((res) => {
      if (isMounted && Array.isArray(res) && res.length > 0) {
        setAgents(res);
      }
    });
    return () => { isMounted = false; };
  }, []);

  const handleTriggerDiagnostic = (agent) => {
    alert(`Triggered diagnostic scan for agent: ${agent.name}`);
  };

  const activeCount = agents.filter(a => a.status === 'ACTIVE').length;
  const totalTasks = agents.reduce((acc, a) => acc + (a.tasksProcessed || 0), 0);

  return (
    <div className="space-y-lg">
      <PageHeader
        title="AI Agent Hub & Multi-Agent Telemetry"
        subtitle="Monitor active autonomous micro-agents, task confidence, and latency execution logs."
      />

      {/* Agents Summary KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        <KPICard title="Active Agents" value={`${activeCount} / ${agents.length}`} status="healthy" subtitle="Coordinated micro-agents" icon={Cpu} />
        <KPICard title="Total Tasks Executed" value={totalTasks > 0 ? totalTasks.toLocaleString() : "79,260"} delta="+14.2%" status="positive" subtitle="Pipeline runs & telemetry" icon={Activity} />
        <KPICard title="Avg Agent Confidence" value="94.2%" status="healthy" subtitle="High precision model threshold" icon={ShieldCheck} />
        <KPICard title="System Latency" value="16.8 ms" status="positive" subtitle="Real-time stream response" icon={Zap} />
      </div>

      {/* Agents Grid */}
      <div className="space-y-md">
        <h3 className="font-title-md text-title-md text-on-surface font-bold">Autonomous Agents Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-lg">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} onTrigger={handleTriggerDiagnostic} />
          ))}
        </div>
      </div>
    </div>
  );
}

