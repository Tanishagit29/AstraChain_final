import React, { useState, useEffect } from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import { api } from '../api/client';
import { 
  UploadCloud, 
  FileSpreadsheet, 
  CheckCircle, 
  AlertTriangle, 
  FileText, 
  Eye, 
  TrendingUp, 
  Database,
  RefreshCw,
  Cpu,
  Layers,
  Sparkles,
  Play,
  Package,
  Trash2
} from 'lucide-react';

const PIPELINE_STAGES = [
  { key: 'upload', label: 'Upload & Parse', icon: UploadCloud },
  { key: 'cleaning', label: 'Data Cleaning', icon: Database },
  { key: 'forecasting', label: 'XGBoost Forecast', icon: TrendingUp },
  { key: 'inventory', label: 'Inventory Analysis', icon: Package },
  { key: 'wastage', label: 'Wastage Decisions', icon: Trash2 },
];

export default function DataIntelligenceAgent() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  
  // Pipeline result
  const [pipelineResult, setPipelineResult] = useState(null);
  const [pipelineError, setPipelineError] = useState(null);
  const [pipelineStages, setPipelineStages] = useState({});

  const [activeTab, setActiveTab] = useState('preview');

  // Groq LLM agent reasoning (runs in the background after the pipeline results are already shown)
  const [agentInsights, setAgentInsights] = useState(null);

  useEffect(() => {
    if (!pipelineResult) {
      setAgentInsights(null);
      return undefined;
    }
    let cancelled = false;
    let timer;
    let tries = 0;
    const poll = async () => {
      const ins = await api.getPipelineAgents();
      if (cancelled) return;
      if (ins) setAgentInsights(ins);
      tries += 1;
      if ((!ins || ins.status === 'running' || ins.status === 'idle') && tries < 60) {
        timer = setTimeout(poll, 3000);
      }
    };
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [pipelineResult]);

  // Load existing pipeline result if available
  useEffect(() => {
    async function loadCurrentStatus() {
      try {
        const data = await api.getPipelineDataCollection();
        if (data && data.has_data) {
          setPipelineStages(data.stages || {
            upload: 'completed',
            cleaning: 'completed',
            forecasting: 'completed',
            inventory: 'completed',
            wastage: 'completed'
          });
          setPipelineResult(data);
        }
      } catch (e) {
        console.warn('Failed to load existing pipeline status:', e);
      }
    }
    loadCurrentStatus();
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
      setPipelineError(null);
    }
  };

  const handleRunPipeline = async () => {
    if (selectedFiles.length === 0) return;
    setIsPipelineRunning(true);
    setPipelineError(null);
    setPipelineResult(null);

    // Initial stage: uploading
    setPipelineStages({
      upload: 'running',
      cleaning: 'pending',
      forecasting: 'pending',
      inventory: 'pending',
      wastage: 'pending'
    });

    // Poll backend real-time stage execution every 2s
    const statusInterval = setInterval(async () => {
      try {
        const st = await api.getPipelineStatus();
        if (st && st.stages) {
          setPipelineStages(st.stages);
        }
      } catch (e) {
        // ignore transient polling errors
      }
    }, 2000);

    try {
      const res = await api.runFullPipeline(selectedFiles);
      clearInterval(statusInterval);

      if (res && res.status === 'success') {
        setPipelineStages({
          upload: 'completed',
          cleaning: 'completed',
          forecasting: 'completed',
          inventory: 'completed',
          wastage: 'completed'
        });
        setPipelineResult(res);
        setActiveTab('preview');
        setTimeout(() => {
          window.scrollTo({ top: 380, behavior: 'smooth' });
        }, 100);
      } else {
        setPipelineError(res?.error || 'Pipeline execution encountered an error. Please check your data format.');
        setPipelineStages(prev => {
          const updated = { ...(res?.stages || prev) };
          Object.keys(updated).forEach(k => {
            if (updated[k] === 'running') updated[k] = 'error';
          });
          return updated;
        });
      }
    } catch (err) {
      clearInterval(statusInterval);
      setPipelineError(err.message || 'Pipeline execution failed.');
      setPipelineStages(prev => {
        const updated = { ...prev };
        Object.keys(updated).forEach(k => {
          if (updated[k] === 'running') updated[k] = 'error';
        });
        return updated;
      });
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const result = pipelineResult;

  return (
    <div className="space-y-lg">
      <PageHeader
        title="Data Collection & Intelligence Agent"
        subtitle="Upload your dataset and the entire pipeline runs automatically: Cleaning → XGBoost Forecasting → Inventory Analysis → Wastage Decisions."
      />

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        <KPICard title="Agent Classification" value="Data Collection" status="healthy" subtitle="Primary Gateway Agent" icon={Layers} />
        <KPICard title="Supported Inputs" value="CSV / XLSX / PDF" status="positive" subtitle="Multi-file compilation" icon={FileSpreadsheet} />
        <KPICard title="Pipeline Automation" value="End-to-End" status="healthy" subtitle="Upload → Dashboard" icon={Cpu} />
        <KPICard title="Forecasting Engine" value="XGBoost" status="positive" subtitle="30-day demand predictions" icon={TrendingUp} />
      </div>

      {/* File Upload & Auto Pipeline Trigger */}
      <div className="glass-panel rounded-xl p-lg space-y-md">
        <h3 className="font-title-md text-title-md text-on-surface font-bold flex items-center gap-xs">
          <UploadCloud className="w-5 h-5 text-primary" /> Upload Dataset & Run Automatic Pipeline
        </h3>
        <p className="text-on-surface-variant text-body-md">
          Upload your retail/supply chain data (inventory records, sales ledgers, etc.). The system will <strong>automatically</strong> clean the data, run XGBoost demand forecasting, analyze inventory levels, and generate wastage/discount decisions.
        </p>

        <div className="border-2 border-dashed border-outline-variant/60 rounded-xl p-xl flex flex-col items-center justify-center bg-surface-container-lowest/50 hover:border-primary/50 transition-colors">
          <UploadCloud className="w-12 h-12 text-on-surface-variant/80 mb-md" />
          <input
            type="file"
            multiple
            accept=".csv, .xlsx, .xls, .pdf"
            id="file-upload-input"
            className="hidden"
            onChange={handleFileChange}
          />
          <label
            htmlFor="file-upload-input"
            className="bg-surface-container-high border border-outline-variant rounded-lg px-md py-sm font-label-md text-on-surface hover:bg-surface-container-highest cursor-pointer transition-all"
          >
            Select Datasets
          </label>
          <p className="text-on-surface-variant/70 text-label-sm mt-xs">
            Supports CSV, Excel (.xlsx), or PDF tables
          </p>

          {selectedFiles.length > 0 && (
            <div className="mt-md w-full max-w-lg space-y-xs bg-surface-container-low/40 p-sm rounded-lg border border-outline-variant/30">
              <p className="font-label-md text-label-sm text-primary uppercase tracking-wider mb-xs">Queued Files:</p>
              {selectedFiles.map((file, i) => (
                <div key={i} className="flex items-center justify-between text-body-md bg-surface-container/30 px-xs py-base rounded border border-outline-variant/20">
                  <span className="flex items-center gap-xs font-mono text-[13px] text-on-surface-variant truncate max-w-sm">
                    {file.name.endsWith('.pdf') ? <FileText className="w-4 h-4 text-error" /> : <FileSpreadsheet className="w-4 h-4 text-primary" />}
                    {file.name}
                  </span>
                  <span className="text-label-sm text-on-surface-variant/70 font-mono">{(file.size / 1024).toFixed(1)} KB</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end pt-xs">
          <button
            onClick={handleRunPipeline}
            disabled={selectedFiles.length === 0 || isPipelineRunning}
            className="bg-primary text-on-primary font-bold rounded-lg px-lg py-md text-label-md hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:pointer-events-none flex items-center gap-xs"
          >
            {isPipelineRunning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {isPipelineRunning ? 'Running Pipeline...' : 'Upload & Run Full Pipeline'}
          </button>
        </div>
      </div>

      {/* Pipeline Progress Indicator */}
      {(isPipelineRunning || Object.keys(pipelineStages).length > 0) && (
        <div className="glass-panel rounded-xl p-lg">
          <h4 className="font-title-md text-title-md text-on-surface font-bold mb-md flex items-center gap-xs">
            <Cpu className="w-5 h-5 text-primary" /> Pipeline Execution Progress
          </h4>
          <div className="flex items-center gap-xs overflow-x-auto pb-xs">
            {PIPELINE_STAGES.map((stage, idx) => {
              const status = pipelineStages[stage.key] || 'pending';
              const Icon = stage.icon;
              const isComplete = status === 'completed';
              const isRunning = status === 'running';
              const isError = status === 'error';

              return (
                <React.Fragment key={stage.key}>
                  <div className={`flex flex-col items-center gap-xs min-w-[100px] p-sm rounded-lg border transition-all ${
                    isComplete ? 'border-primary/50 bg-primary/10' :
                    isRunning ? 'border-tertiary/50 bg-tertiary/10 animate-pulse' :
                    isError ? 'border-error/50 bg-error/10' :
                    'border-outline-variant/30 bg-surface-container-low/30'
                  }`}>
                    {isComplete ? <CheckCircle className="w-5 h-5 text-primary" /> :
                     isRunning ? <RefreshCw className="w-5 h-5 text-tertiary animate-spin" /> :
                     isError ? <AlertTriangle className="w-5 h-5 text-error" /> :
                     <Icon className="w-5 h-5 text-on-surface-variant/50" />}
                    <span className={`text-[10px] font-label-sm text-center font-bold uppercase tracking-wider ${
                      isComplete ? 'text-primary' :
                      isRunning ? 'text-tertiary' :
                      isError ? 'text-error' :
                      'text-on-surface-variant/50'
                    }`}>{stage.label}</span>
                  </div>
                  {idx < PIPELINE_STAGES.length - 1 && (
                    <div className={`w-6 h-0.5 shrink-0 ${isComplete ? 'bg-primary' : 'bg-outline-variant/30'}`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      )}

      {/* Pipeline Error */}
      {pipelineError && (
        <div className="bg-error/10 border border-error/30 rounded-xl p-md flex gap-sm text-body-md text-error">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-base" />
          <div>
            <p className="font-bold text-label-md">Pipeline Error</p>
            <p className="text-[13px] text-on-surface/80 mt-xs">{pipelineError}</p>
          </div>
        </div>
      )}

      {/* Pipeline Results */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">

          {/* Left Column: Summary & Warnings */}
          <div className="space-y-lg lg:col-span-1">

            {/* Pipeline Summary */}
            <div className="glass-panel rounded-xl p-lg space-y-md">
              <h4 className="font-title-md text-title-md text-on-surface font-bold flex items-center gap-xs">
                <CheckCircle className="w-5 h-5 text-primary" /> Pipeline Complete
              </h4>

              <div className="space-y-xs text-body-md">
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Products Processed</span>
                  <span className="font-bold text-on-surface font-mono">{result.dataset_summary?.total_products || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Rows Cleaned</span>
                  <span className="font-bold text-on-surface font-mono">{result.dataset_summary?.total_rows || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Forecasted Products</span>
                  <span className="font-bold text-on-surface font-mono">{result.forecast_summary?.products_forecasted || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Stockout Risks</span>
                  <span className="font-bold text-error font-mono">{result.inventory_summary?.stockout_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Near-Expiry Items</span>
                  <span className="font-bold text-tertiary font-mono">{result.wastage_summary?.near_expiry_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Data Quality Score</span>
                  <span className="font-bold text-primary font-mono">{result.dataset_summary?.quality_score || 0}%</span>
                </div>
              </div>

              {/* Missing Field Warnings */}
              {result.missing_field_warnings && result.missing_field_warnings.length > 0 && (
                <div className="space-y-xs pt-sm border-t border-outline-variant/30">
                  <p className="text-label-sm font-label-md text-tertiary uppercase tracking-wider">Warnings</p>
                  {result.missing_field_warnings.map((warn, i) => (
                    <div key={i} className="flex gap-xs bg-tertiary/10 border border-tertiary/20 text-tertiary text-[12px] p-xs rounded">
                      <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
                      <span>{warn}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* AI Agent Insights (Groq) */}
            {agentInsights && (
              <div className="glass-panel rounded-xl p-lg space-y-md">
                <h4 className="font-title-md text-title-md text-on-surface font-bold flex items-center gap-xs">
                  <Cpu className="w-5 h-5 text-primary" /> AI Agent Insights
                  <span className="ml-auto text-[10px] uppercase tracking-wider font-mono px-xs py-base rounded border border-primary/30 text-primary">
                    {agentInsights.status === 'running' ? 'Analysing…' : agentInsights.status}
                  </span>
                </h4>
                <p className="text-[12px] text-on-surface-variant">{agentInsights.message}</p>
                {(agentInsights.agents || []).map((agent) => (
                  <div key={agent.agent_id || agent.agent_name} className="border-t border-outline-variant/30 pt-sm space-y-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-label-md font-bold text-on-surface">{agent.agent_name}</span>
                      <span className="text-[10px] font-mono uppercase text-on-surface-variant">{agent.mode}</span>
                    </div>
                    {agent.summary && <p className="text-[12px] text-on-surface/80 whitespace-pre-line">{agent.summary}</p>}
                    {agent.tools_used && agent.tools_used.length > 0 && (
                      <div className="flex flex-wrap gap-xs">
                        {agent.tools_used.map((tool, i) => (
                          <span key={`${tool}-${i}`} className="bg-primary/10 border border-primary/20 text-primary font-mono text-[10px] px-xs py-base rounded">
                            {tool}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Engineered Features */}
            {result.engineered_columns && result.engineered_columns.length > 0 && (
              <div className="bg-secondary-container/20 border border-primary/20 rounded-xl p-lg space-y-xs">
                <h4 className="font-title-md text-title-md text-primary font-bold flex items-center gap-xs">
                  <Sparkles className="w-5 h-5" /> Engineered Features
                </h4>
                <div className="flex flex-wrap gap-xs">
                  {result.engineered_columns.map((col) => (
                    <span key={col} className="bg-primary/10 border border-primary/20 text-primary font-mono text-[11px] px-xs py-base rounded">
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Data Tabs */}
          <div className="space-y-lg lg:col-span-2">

            {/* Tabs */}
            <div className="flex border-b border-outline-variant/30 gap-xs">
              <button
                onClick={() => setActiveTab('quality')}
                className={`px-md py-sm font-label-md text-label-sm border-b-2 transition-all ${
                  activeTab === 'quality' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface'
                }`}
              >
                Data Quality Report
              </button>
              <button
                onClick={() => setActiveTab('eda')}
                className={`px-md py-sm font-label-md text-label-sm border-b-2 transition-all ${
                  activeTab === 'eda' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface'
                }`}
              >
                Exploratory Data Analysis
              </button>
              <button
                onClick={() => setActiveTab('preview')}
                className={`px-md py-sm font-label-md text-label-sm border-b-2 transition-all ${
                  activeTab === 'preview' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface'
                }`}
              >
                Dataset Preview
              </button>
            </div>

            {/* Quality Tab */}
            {activeTab === 'quality' && (
              <div className="space-y-md">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
                  <div className="bg-surface-container-low/30 rounded-xl p-md border border-outline-variant/30">
                    <p className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider mb-xs">Duplicates Removed</p>
                    <p className="text-headline-md font-headline-md font-mono text-on-surface font-bold">
                      {result.quality_report?.duplicates || 0}
                    </p>
                  </div>
                  <div className="bg-surface-container-low/30 rounded-xl p-md border border-outline-variant/30">
                    <p className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider mb-xs">Empty Columns</p>
                    <p className="text-headline-md font-headline-md font-mono text-on-surface font-bold text-tertiary">
                      {result.quality_report?.empty_columns?.length || 0}
                    </p>
                  </div>
                  <div className="bg-surface-container-low/30 rounded-xl p-md border border-outline-variant/30">
                    <p className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider mb-xs">Total Outliers</p>
                    <p className="text-headline-md font-headline-md font-mono text-on-surface font-bold text-error">
                      {result.quality_report?.outliers
                        ? Object.values(result.quality_report.outliers).reduce((sum, item) => sum + item.count, 0)
                        : 0}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* EDA Tab */}
            {activeTab === 'eda' && (
              <div className="space-y-md">
                <div className="glass-panel rounded-xl p-lg grid grid-cols-2 md:grid-cols-4 gap-md">
                  <div>
                    <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider block mb-base">Total Rows</span>
                    <span className="text-title-md font-mono text-on-surface font-bold">{result.eda_summary?.rows || 0}</span>
                  </div>
                  <div>
                    <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider block mb-base">Total Columns</span>
                    <span className="text-title-md font-mono text-on-surface font-bold">{result.eda_summary?.columns || 0}</span>
                  </div>
                  <div>
                    <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider block mb-base">Memory</span>
                    <span className="text-title-md font-mono text-on-surface font-bold">{result.eda_summary?.memory_kb || 0} KB</span>
                  </div>
                  <div>
                    <span className="text-[11px] font-label-sm text-on-surface-variant uppercase tracking-wider block mb-base">Quality Score</span>
                    <span className="text-title-md text-primary font-bold">{result.dataset_summary?.quality_score || 0}%</span>
                  </div>
                </div>

                {/* Column Types */}
                {result.eda_summary?.columns_info && (
                  <div className="glass-panel rounded-xl p-lg space-y-md overflow-hidden">
                    <h4 className="font-title-md text-title-md text-on-surface font-bold">Column Profile</h4>
                    <div className="overflow-x-auto custom-scrollbar">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="bg-surface-container-high/30 border-b border-outline-variant/30">
                            <th className="px-sm py-xs text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Column</th>
                            <th className="px-sm py-xs text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Type</th>
                            <th className="px-sm py-xs text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Detected</th>
                            <th className="px-sm py-xs text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Nulls</th>
                            <th className="px-sm py-xs text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Distinct</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-outline-variant/20 font-mono text-[13px] text-on-surface/90">
                          {result.eda_summary.columns_info.map((col, idx) => (
                            <tr key={idx} className="hover:bg-surface-variant/20 transition-colors">
                              <td className="px-sm py-sm font-bold text-on-surface">{col.name}</td>
                              <td className="px-sm py-sm text-on-surface-variant">{col.pandas_dtype}</td>
                              <td className="px-sm py-sm text-primary">{col.detected_type}</td>
                              <td className="px-sm py-sm text-error">{col.missing_count}</td>
                              <td className="px-sm py-sm text-on-surface-variant">{col.unique_values}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Preview Tab */}
            {activeTab === 'preview' && (
              <div className="space-y-md">
                <div className="glass-panel rounded-xl p-lg space-y-md overflow-hidden">
                  <div className="flex justify-between items-center gap-md">
                    <h4 className="font-title-md text-title-md text-on-surface font-bold">
                      Cleaned Dataset Preview
                    </h4>
                    <span className="text-label-sm text-on-surface-variant font-mono">
                      Showing first {result.preview_rows?.length || 0} rows
                    </span>
                  </div>

                  <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-surface-container-high/30 border-b border-outline-variant/30">
                          {result.preview_columns?.map((col) => (
                            <th key={col} className="px-sm py-xs text-[10px] font-bold text-on-surface-variant uppercase tracking-wider font-mono">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-outline-variant/20 font-mono text-[12px] text-on-surface/90">
                        {result.preview_rows?.map((row, idx) => (
                          <tr key={idx} className="hover:bg-surface-variant/20 transition-colors">
                            {result.preview_columns.map((col) => (
                              <td key={col} className="px-sm py-sm whitespace-nowrap truncate max-w-xs" title={row[col] !== null ? String(row[col]) : 'NULL'}>
                                {row[col] !== null ? String(row[col]) : <span className="text-error font-bold font-sans">NULL</span>}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>
      )}

    </div>
  );
}
