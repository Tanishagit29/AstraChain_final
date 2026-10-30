import React, { useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import ChartCard from '../components/ChartCard';
import AIRecommendationCard from '../components/AIRecommendationCard';
import { api } from '../api/client';
import { 
  DollarSign, PackageCheck, AlertTriangle, Trash2, Sparkles, Activity,
  Database, TrendingUp, UploadCloud, CheckCircle2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    api.getPipelineDashboard().then((res) => {
      if (isMounted && res) {
        setData(res);
      }
      setLoading(false);
    });
    return () => { isMounted = false; };
  }, []);

  // No data state
  if (!loading && (!data || !data.has_data)) {
    return (
      <div className="space-y-lg">
        <PageHeader
          title="Operations Dashboard"
          subtitle="Real-time predictive intelligence, XGBoost forecasting & automated decisions."
        />
        <div className="glass-card rounded-xl p-2xl flex flex-col items-center justify-center text-center space-y-md min-h-[400px]">
          <div className="w-20 h-20 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
            <UploadCloud className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-title-lg font-bold text-on-surface">No Pipeline Data Available</h2>
          <p className="text-body-md text-on-surface-variant max-w-md">
            Upload a dataset from the <strong>Data Ingestion</strong> page to run the automatic pipeline.
            The dashboard will populate with real insights from your data.
          </p>
          <button
            onClick={() => navigate('/data-collection')}
            className="bg-primary text-on-primary font-bold rounded-lg px-lg py-md text-label-md hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary/20 flex items-center gap-xs mt-md"
          >
            <Database className="w-4 h-4" />
            Go to Data Ingestion
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-lg">
        <PageHeader title="Operations Dashboard" subtitle="Loading pipeline data..." />
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  const kpis = data.kpiMetrics || {};
  const forecast = data.demandForecastData || [];
  const recs = data.aiRecommendations || [];
  const logs = data.recentActivityLogs || [];
  const health = data.healthIndicators || {};

  const handleExecuteRecommendation = async (rec) => {
    if (rec.type === 'HIGH_RISK' || rec.actionText?.includes('Restock')) {
      const pid = rec.product_id || rec.product;
      const res = await api.restockProduct({ product_id: pid, quantity: 500 });
      if (res && res.success) {
        setToastMessage(`Restocked ${res.product_name || rec.product} (+500 units)! Stockout risk resolved.`);
        setTimeout(() => setToastMessage(null), 4000);
        api.getPipelineDashboard().then((updated) => {
          if (updated) setData(updated);
        });
      }
    } else if (rec.type === 'EXPIRED') {
      setToastMessage(`Quarantine verified: ${rec.product} marked do-not-sell.`);
      setTimeout(() => setToastMessage(null), 4000);
    }
  };

  return (
    <div className="space-y-lg">
      {/* Page Header */}
      <PageHeader
        title="Operations Dashboard"
        subtitle="Real-time predictive intelligence, XGBoost forecasting & automated decisions."
      />

      {/* Success Notification Banner */}
      {toastMessage && (
        <div className="p-md rounded-xl bg-secondary/15 border border-secondary/30 text-secondary font-bold flex items-center gap-sm shadow-md animate-fade-in">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Pipeline Status Banner */}
      {data.pipeline_timestamp && (
        <div className="p-md rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-between">
          <div className="flex items-center gap-sm">
            <Sparkles className="w-6 h-6 text-primary" />
            <div>
              <p className="font-bold text-on-surface text-body-md">Pipeline Active — All Data From Uploaded Dataset</p>
              <p className="font-label-sm text-on-surface-variant">
                Data Collection → XGBoost Forecast → Inventory Analysis → Wastage Decisions
              </p>
            </div>
          </div>
          <span className="px-sm py-xs rounded bg-primary/20 text-primary font-label-sm font-bold hidden md:block">
            Dataset: {data.dataset_id}
          </span>
        </div>
      )}

      {/* Missing Field Warnings */}
      {data.missing_field_warnings && data.missing_field_warnings.length > 0 && (
        <div className="space-y-xs">
          {data.missing_field_warnings.map((warn, i) => (
            <div key={i} className="p-sm rounded-lg bg-tertiary/10 border border-tertiary/20 flex gap-xs text-body-md text-tertiary">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{warn}</span>
            </div>
          ))}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-md">
        <KPICard
          title="Dataset Records"
          value={kpis.totalSales?.value || "0"}
          delta={kpis.totalSales?.delta || ""}
          status="positive"
          subtitle={kpis.totalSales?.timeframe || "from uploaded dataset"}
          icon={DollarSign}
        />
        <KPICard
          title="Inventory Health"
          value={kpis.inventoryHealth?.value || "0%"}
          delta="Analyzed"
          status={kpis.inventoryHealth?.status || "healthy"}
          subtitle={kpis.inventoryHealth?.subtitle || ""}
          icon={PackageCheck}
        />
        <KPICard
          title="Stockout Risks"
          value={kpis.stockoutRisks?.value || "0"}
          delta={kpis.stockoutRisks?.delta || ""}
          status={kpis.stockoutRisks?.status || "healthy"}
          subtitle={kpis.stockoutRisks?.subtitle || ""}
          icon={AlertTriangle}
          borderAccent="border-l-error"
        />
        <KPICard
          title="Expiry Watch"
          value={kpis.wastageRate?.value || "0"}
          delta={kpis.wastageRate?.delta || ""}
          status={kpis.wastageRate?.status || "positive"}
          subtitle={kpis.wastageRate?.timeframe || ""}
          icon={Trash2}
        />
      </div>

      {/* Main Analytics & AI Recommendations Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
        {/* Demand Forecast Chart */}
        <div className="lg:col-span-2">
          {forecast.length > 0 ? (
            <ChartCard
              title="XGBoost Predictive Demand Modeling"
              subtitle="Forecast derived from uploaded dataset"
              data={forecast}
              type="area"
            />
          ) : (
            <div className="glass-card rounded-xl p-lg flex items-center justify-center min-h-[300px]">
              <p className="text-on-surface-variant text-body-md">No forecast chart data available.</p>
            </div>
          )}
        </div>

        {/* AI Recommendations Column */}
        <div className="glass-card rounded-xl p-lg space-y-lg flex flex-col justify-between">
          <div className="space-y-md">
            <div className="flex items-center gap-xs text-primary">
              <Sparkles className="w-5 h-5 text-primary" />
              <h4 className="font-title-md text-title-md text-on-surface font-bold">Pipeline Insights</h4>
            </div>

            <div className="space-y-md">
              {recs.map((rec) => (
                <AIRecommendationCard
                  key={rec.id}
                  recommendation={rec}
                  onExecute={handleExecuteRecommendation}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Health Progress Meters & Automation Decisions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
        {/* Pipeline Health Indicators */}
        <div className="glass-card rounded-xl p-lg space-y-lg">
          <h4 className="font-title-md text-title-md text-on-surface font-bold">Pipeline Health</h4>
          <div className="space-y-lg">
            <div className="space-y-xs">
              <div className="flex justify-between font-label-md text-label-md">
                <span className="text-on-surface-variant">Inventory Efficiency</span>
                <span className="text-primary font-bold">{health.inventoryEfficiency || '0%'}</span>
              </div>
              <div className="h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: health.inventoryEfficiency || '0%' }} />
              </div>
            </div>

            <div className="space-y-xs">
              <div className="flex justify-between font-label-md text-label-md">
                <span className="text-on-surface-variant">Data Quality</span>
                <span className="text-primary font-bold">{health.dataQuality || '0%'}</span>
              </div>
              <div className="h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: health.dataQuality || '0%' }} />
              </div>
            </div>

            <div className="space-y-xs">
              <div className="flex justify-between font-label-md text-label-md">
                <span className="text-on-surface-variant">Forecast Confidence</span>
                <span className="text-primary font-bold">{health.forecastConfidence || '0%'}</span>
              </div>
              <div className="h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: health.forecastConfidence || '0%' }} />
              </div>
            </div>

            <div className="space-y-xs">
              <div className="flex justify-between font-label-md text-label-md">
                <span className="text-on-surface-variant">Wastage Prevention</span>
                <span className="text-primary font-bold">{health.wastagePrevention || '0%'}</span>
              </div>
              <div className="h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: health.wastagePrevention || '0%' }} />
              </div>
            </div>
          </div>
        </div>

        {/* Automation Decisions Timeline */}
        <div className="lg:col-span-2 glass-card rounded-xl p-lg">
          <div className="flex justify-between items-center mb-lg">
            <h4 className="font-title-md text-title-md text-on-surface font-bold">Automated Decisions</h4>
            <span className="text-on-surface-variant font-label-sm">From latest pipeline run</span>
          </div>

          {logs.length > 0 ? (
            <div className="relative space-y-md before:absolute before:left-4 before:top-2 before:bottom-2 before:w-px before:bg-outline-variant">
              {logs.map((log, i) => (
                <div key={log.id || i} className="relative pl-10 group">
                  <div className="absolute left-2.5 top-1 w-3 h-3 rounded-full bg-primary border-4 border-background group-hover:scale-125 transition-transform" />
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-body-md text-body-md text-on-surface">
                        <span className="font-bold">{log.agent}</span> {log.action}
                      </p>
                      <p className="font-label-sm text-label-sm text-on-surface-variant mt-xs">{log.details}</p>
                    </div>
                    <span className="font-label-sm text-label-sm text-on-surface-variant shrink-0">{log.time}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-on-surface-variant text-body-md text-center py-lg">No automation decisions yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
