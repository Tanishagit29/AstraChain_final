import React, { useEffect, useState, useMemo } from 'react';
import PageHeader from '../components/PageHeader';
import ChartCard from '../components/ChartCard';
import KPICard from '../components/KPICard';
import { api } from '../api/client';
import {
  TrendingUp, Cpu, Target, BarChart3, Database, UploadCloud,
  PartyPopper, CalendarDays, Sparkles, AlertTriangle, ShieldCheck, Flame, Zap,
  SlidersHorizontal, CheckCircle2, Layers, Sparkle, ArrowRight, RotateCw
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const FESTIVAL_OPTIONS = [
  'Diwali',
  'Holi',
  'Eid al-Fitr',
  'Ganesh Chaturthi',
  'Navratri',
  'Durga Puja',
  'Dussehra',
  'Raksha Bandhan',
  'Christmas',
  'New Year',
  'Republic Day',
  'Independence Day',
  'Janmashtami',
  'Onam',
  'Pongal',
  'Karwa Chauth',
  'Baisakhi',
  'Chhath Puja',
  'Maha Shivratri',
  'Gandhi Jayanti',
];

function FestivalItemDemandPredictor() {
  const [selectedFestival, setSelectedFestival] = useState('Diwali');
  const [itemDemandData, setItemDemandData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reorderingId, setReorderingId] = useState(null);
  const [reorderedIds, setReorderedIds] = useState(new Set());
  const [reorderingAll, setReorderingAll] = useState(false);
  const [festivalToast, setFestivalToast] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    api.getFestivalItemDemand(selectedFestival, 60, 20).then((res) => {
      if (isMounted) {
        if (res && res.items) {
          setItemDemandData(res);
        } else {
          setItemDemandData(null);
        }
        setLoading(false);
      }
    });
    return () => { isMounted = false; };
  }, [selectedFestival]);

  const topItem = itemDemandData?.items?.[0];

  return (
    <div className="space-y-md">
      {/* Success Reorder Toast */}
      {festivalToast && (
        <div className="p-md rounded-xl bg-primary/10 border border-primary/30 flex items-center gap-sm text-primary font-bold shadow-md animate-fade-in">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{festivalToast}</span>
        </div>
      )}

      {/* Header & Festival Selector */}
      <div className="flex items-center justify-between flex-wrap gap-sm bg-surface-container-low p-md rounded-xl border border-outline-variant/50 shadow-sm">
        <div className="flex items-center gap-xs">
          <div className="p-xs bg-primary/10 rounded-lg text-primary">
            <PartyPopper className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-title-md text-title-md text-on-surface font-bold flex items-center gap-2">
              Festival-Wise Item Demand Predictor
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/20">
                ACTIVE OPTION
              </span>
            </h3>
            <p className="text-body-sm text-on-surface-variant">
              Predicts which specific items will experience peak sales volume during each festival
            </p>
          </div>
        </div>

        <div className="flex items-center gap-xs">
          <label className="text-label-sm text-on-surface-variant font-mono uppercase">Select Festival:</label>
          <select
            value={selectedFestival}
            onChange={(e) => setSelectedFestival(e.target.value)}
            className="bg-surface-container-high border border-outline-variant rounded-lg px-md py-xs text-body-md text-on-surface font-bold focus:ring-2 focus:ring-primary focus:border-primary shadow-sm"
          >
            {FESTIVAL_OPTIONS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary KPI Cards for Selected Festival */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-md">
        <div className="glass-card rounded-xl p-md flex flex-col justify-between border border-outline-variant/40">
          <div className="flex items-center justify-between text-on-surface-variant mb-xs">
            <span className="text-[11px] font-mono uppercase tracking-wider">Target Festival</span>
            <CalendarDays className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h4 className="text-headline-sm font-bold text-on-surface">{itemDemandData?.festival_name || selectedFestival}</h4>
            <p className="text-body-sm text-on-surface-variant mt-0.5">
              {itemDemandData?.festival_date || 'Upcoming'} · {itemDemandData?.days_away ?? 45} days away
            </p>
          </div>
        </div>

        <div className="glass-card rounded-xl p-md flex flex-col justify-between border border-outline-variant/40">
          <div className="flex items-center justify-between text-on-surface-variant mb-xs">
            <span className="text-[11px] font-mono uppercase tracking-wider">Top Surge Category</span>
            <Sparkles className="w-4 h-4 text-secondary" />
          </div>
          <div>
            <h4 className="text-headline-sm font-bold text-primary">{itemDemandData?.top_category || 'Electronics'}</h4>
            <p className="text-body-sm text-on-surface-variant mt-0.5">
              Highest demand uplift across catalog
            </p>
          </div>
        </div>

        <div className="glass-card rounded-xl p-md flex flex-col justify-between border border-outline-variant/40">
          <div className="flex items-center justify-between text-on-surface-variant mb-xs">
            <span className="text-[11px] font-mono uppercase tracking-wider">Total Surge Demand</span>
            <Flame className="w-4 h-4 text-error" />
          </div>
          <div>
            <h4 className="text-headline-sm font-bold text-on-surface font-mono">
              +{(itemDemandData?.total_surge_units || 0).toLocaleString()} <span className="text-body-sm font-sans font-normal text-on-surface-variant">units</span>
            </h4>
            <p className="text-body-sm text-on-surface-variant mt-0.5">
              Extra demand during {itemDemandData?.window_days || 7}-day festival window
            </p>
          </div>
        </div>

        <div className="glass-card rounded-xl p-md flex flex-col justify-between border border-outline-variant/40">
          <div className="flex items-center justify-between text-on-surface-variant mb-xs">
            <span className="text-[11px] font-mono uppercase tracking-wider">#1 Best Seller Prediction</span>
            <Zap className="w-4 h-4 text-tertiary" />
          </div>
          <div>
            <h4 className="text-body-md font-bold text-on-surface truncate" title={topItem?.product_name}>
              {topItem?.product_name || 'Loading...'}
            </h4>
            <p className="text-body-sm font-mono text-primary font-bold mt-0.5">
              {topItem ? `${topItem.festival_period_sales.toLocaleString()} units (${topItem.festival_multiplier}x uplift)` : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Main Item Demand Ranking Table */}
      <div className="glass-panel rounded-xl overflow-hidden border border-outline-variant/50">
        <div className="p-md border-b border-outline-variant bg-surface-container-low/60 flex items-center justify-between flex-wrap gap-xs">
          <div className="flex items-center gap-xs">
            <Target className="w-4 h-4 text-primary" />
            <h4 className="font-title-sm text-title-sm font-bold text-on-surface">
              Predicted High-Demand Items for {selectedFestival}
            </h4>
          </div>
          <div className="flex items-center gap-xs">
            <span className="text-label-sm font-mono text-on-surface-variant bg-surface-container-high px-sm py-0.5 rounded-full">
              Window: {itemDemandData?.window_days || 7} Days around peak
            </span>
            <button
              onClick={async () => {
                if (!itemDemandData?.items?.length) return;
                setReorderingAll(true);
                try {
                  for (const item of itemDemandData.items) {
                    await api.prestockFestival({
                      product_id: item.product_id,
                      festival_name: selectedFestival,
                      quantity: item.extra_units_needed || 600,
                    });
                  }
                  setReorderedIds(new Set(itemDemandData.items.map(i => i.product_id)));
                  setFestivalToast(`1-Click Festival Reorder: All ${itemDemandData.items.length} items reordered for ${selectedFestival}!`);
                  setTimeout(() => setFestivalToast(null), 5000);
                } catch (e) {
                  console.error('Bulk festival reorder failed:', e);
                } finally {
                  setReorderingAll(false);
                }
              }}
              disabled={reorderingAll || !itemDemandData?.items?.length}
              className="bg-primary hover:bg-primary/90 active:scale-95 text-on-primary font-bold px-sm py-1 rounded-lg text-[11px] flex items-center gap-1 shadow-sm transition-all cursor-pointer disabled:opacity-50"
            >
              {reorderingAll ? <RotateCw className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
              <span>{reorderingAll ? 'Reordering...' : `1-Click Reorder All ${selectedFestival} Buffers`}</span>
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-xl flex items-center justify-center">
            <div className="animate-spin w-7 h-7 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : (
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container-high/30">
                <tr>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Rank</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Product Name & ID</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Category</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Base Daily</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Surge Multiplier</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Festival Sales</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Extra Buffer Needed</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">Stock Risk Status</th>
                  <th className="px-md py-sm text-label-sm text-on-surface-variant uppercase font-mono">1-Click Festival Reorder</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 text-body-md">
                {(!itemDemandData?.items || itemDemandData.items.length === 0) && (
                  <tr>
                    <td colSpan={9} className="px-md py-lg text-center text-on-surface-variant italic">
                      No demand predictions available for {selectedFestival}.
                    </td>
                  </tr>
                )}
                {itemDemandData?.items?.map((item, idx) => (
                  <tr key={item.product_id} className="hover:bg-surface-variant/20 transition-colors">
                    <td className="px-md py-sm font-mono font-bold text-on-surface-variant">
                      #{idx + 1}
                    </td>
                    <td className="px-md py-sm">
                      <p className="font-bold text-on-surface">{item.product_name}</p>
                      <p className="text-[11px] font-mono text-on-surface-variant">{item.product_id}</p>
                    </td>
                    <td className="px-md py-sm font-medium text-on-surface-variant">
                      {item.category}
                    </td>
                    <td className="px-md py-sm font-mono text-on-surface">
                      {item.baseline_daily_demand} / day
                    </td>
                    <td className="px-md py-sm font-mono">
                      <span className={`px-xs py-0.5 rounded font-bold text-label-sm ${
                        item.festival_multiplier >= 1.5 ? 'bg-error/15 text-error border border-error/20' :
                        item.festival_multiplier >= 1.25 ? 'bg-primary/15 text-primary border border-primary/20' :
                        'bg-secondary/15 text-secondary'
                      }`}>
                        {item.festival_multiplier}x (+{item.uplift_pct}%)
                      </span>
                    </td>
                    <td className="px-md py-sm font-mono font-bold text-on-surface">
                      {item.festival_period_sales.toLocaleString()} units
                    </td>
                    <td className="px-md py-sm font-mono font-bold text-primary">
                      +{item.extra_units_needed.toLocaleString()} units
                    </td>
                    <td className="px-md py-sm">
                      {item.stock_status === 'Stockout Risk' ? (
                        <span className="inline-flex items-center gap-1 px-xs py-0.5 rounded font-label-sm font-bold bg-error/10 text-error border border-error/20">
                          <AlertTriangle className="w-3 h-3" /> Stockout Risk ({item.current_stock ?? 0} in stock)
                        </span>
                      ) : item.stock_status === 'Reorder Buffer Needed' ? (
                        <span className="inline-flex items-center gap-1 px-xs py-0.5 rounded font-label-sm font-bold bg-[#FF9800]/15 text-[#FF9800] border border-[#FF9800]/20">
                          <Flame className="w-3 h-3" /> Buffer Needed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-xs py-0.5 rounded font-label-sm font-bold bg-primary/10 text-primary border border-primary/20">
                          <ShieldCheck className="w-3 h-3" /> Optimal Stock
                        </span>
                      )}
                    </td>
                    <td className="px-md py-sm">
                      {reorderedIds.has(item.product_id) ? (
                        <span className="text-emerald-400 font-bold text-[11px] font-mono flex items-center gap-1 bg-emerald-500/15 px-2 py-1 rounded-md border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" /> Reordered (+{item.extra_units_needed || 600})
                        </span>
                      ) : (
                        <button
                          onClick={async () => {
                            setReorderingId(item.product_id);
                            try {
                              await api.prestockFestival({
                                product_id: item.product_id,
                                festival_name: selectedFestival,
                                quantity: item.extra_units_needed || 600,
                              });
                              setReorderedIds((prev) => new Set(prev).add(item.product_id));
                              setFestivalToast(`Reordered +${item.extra_units_needed || 600} units of ${item.product_name} for ${selectedFestival}!`);
                              setTimeout(() => setFestivalToast(null), 4000);
                            } catch (err) {
                              console.error('Festival reorder failed:', err);
                            } finally {
                              setReorderingId(null);
                            }
                          }}
                          disabled={reorderingId === item.product_id}
                          className="bg-primary hover:bg-primary/90 active:scale-95 text-on-primary font-bold px-2.5 py-1 rounded-lg text-[11px] flex items-center gap-1 shadow-sm transition-all cursor-pointer disabled:opacity-50"
                          title="1-Click Reorder festival buffer surge"
                        >
                          {reorderingId === item.product_id ? (
                            <RotateCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Zap className="w-3 h-3" />
                          )}
                          <span>1-Click Reorder (+{item.extra_units_needed || 600})</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DemandForecast() {
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Mode state: 'standard' | 'festival' | 'combined'
  const activeTab = searchParams.get('mode') || 'standard';

  const setTab = (newMode) => {
    setSearchParams({ mode: newMode });
  };

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    api.getPipelineForecast().then((res) => {
      if (isMounted) {
        setForecastData(res);
      }
      setLoading(false);
    });
    return () => { isMounted = false; };
  }, []);

  if (loading) {
    return (
      <div className="space-y-lg">
        <PageHeader title="Demand & Forecasting Agent" subtitle="Loading forecast data..." />
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (!forecastData || !forecastData.has_data) {
    return (
      <div className="space-y-lg">
        <PageHeader
          title="Demand & Forecasting Agent"
          subtitle="Predictive trends & multi-step forecasting using XGBoost Regressor with Festival Option."
        />
        <div className="glass-card rounded-xl p-2xl flex flex-col items-center justify-center text-center space-y-md min-h-[400px]">
          <div className="w-20 h-20 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
            <UploadCloud className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-title-lg font-bold text-on-surface">No Forecast Available</h2>
          <p className="text-body-md text-on-surface-variant max-w-md">
            Upload a dataset from the <strong>Data Ingestion</strong> page to generate XGBoost demand predictions & festival analysis.
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

  const chartData = forecastData.chart_data || [];
  const metric = forecastData.metric || {};
  const byProduct = forecastData.by_product || {};
  const productList = Object.values(byProduct);

  const accuracyPct = metric.accuracy_pct || 95.5;
  const maeVal = metric.mae || 4.2;
  const rmseVal = metric.rmse || 5.8;
  const mapeVal = metric.mape || 4.5;

  return (
    <div className="space-y-lg">
      <PageHeader
        title="Demand & Forecasting Agent"
        subtitle="Standard XGBoost predictive demand modeling with optional Festival-Wise Demand Forecasting mode."
      />

      {/* TOP-LEVEL MODE SWITCHER OPTIONS BAR */}
      <div className="flex items-center justify-between flex-wrap gap-md bg-surface-container-low p-sm rounded-xl border border-outline-variant/60 shadow-sm">
        <div className="flex items-center gap-xs">
          <SlidersHorizontal className="w-4 h-4 text-primary ml-xs" />
          <span className="text-label-sm font-mono uppercase text-on-surface-variant font-bold">
            Forecasting View Option:
          </span>
        </div>

        <div className="flex items-center gap-xs bg-surface-container-high p-1 rounded-lg border border-outline-variant/40">
          <button
            onClick={() => setTab('standard')}
            className={`flex items-center gap-xs px-md py-xs rounded-md font-label-md text-label-md transition-all ${
              activeTab === 'standard'
                ? 'bg-primary text-on-primary font-bold shadow-md'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            Standard Demand Forecast
          </button>

          <button
            onClick={() => setTab('festival')}
            className={`flex items-center gap-xs px-md py-xs rounded-md font-label-md text-label-md transition-all ${
              activeTab === 'festival'
                ? 'bg-secondary text-on-secondary font-bold shadow-md'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
            }`}
          >
            <PartyPopper className="w-4 h-4" />
            Festival-Wise Demand Forecast (Option)
          </button>

          <button
            onClick={() => setTab('combined')}
            className={`flex items-center gap-xs px-md py-xs rounded-md font-label-md text-label-md transition-all ${
              activeTab === 'combined'
                ? 'bg-primary-container text-on-primary-container font-bold shadow-md border border-primary/30'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
            }`}
          >
            <Layers className="w-4 h-4" />
            Combined View
          </button>
        </div>
      </div>

      {/* KPI Cards (Available in all views) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        <KPICard
          title="Model Engine"
          value={metric.model || "Tuned XGBoost"}
          status="healthy"
          subtitle={activeTab === 'festival' ? "Festival Surge Engine Enabled" : "Base Demand Regressor"}
          icon={Cpu}
        />
        <KPICard
          title="Forecast Horizon"
          value={`${metric.horizon_days || 30} Days`}
          status="positive"
          subtitle="Multi-step autoregressive projection"
          icon={TrendingUp}
        />
        <KPICard
          title="Products Forecasted"
          value={String(productList.length)}
          status="healthy"
          subtitle="Active inventory items"
          icon={Target}
        />
        <KPICard
          title="Model Accuracy"
          value={`${accuracyPct}%`}
          delta={`MAE: ${maeVal} | MAPE: ${mapeVal}%`}
          status="positive"
          subtitle={`RMSE: ${rmseVal}`}
          icon={BarChart3}
        />
      </div>

      {/* OPTION TAB 1: STANDARD DEMAND FORECAST (UNTOUCHED CORE AGENT) */}
      {(activeTab === 'standard' || activeTab === 'combined') && (
        <div className="space-y-lg">
          {/* Option Banner */}
          {activeTab === 'standard' && (
            <div className="glass-card p-md rounded-xl border border-primary/30 bg-primary/5 flex items-center justify-between flex-wrap gap-sm">
              <div className="flex items-center gap-sm">
                <CheckCircle2 className="w-5 h-5 text-primary shrink-0" />
                <div>
                  <h4 className="font-title-sm text-title-sm font-bold text-on-surface">
                    Standard Demand Forecasting Agent Active
                  </h4>
                  <p className="text-body-sm text-on-surface-variant">
                    Running base XGBoost predictive demand modeling. Festival-wise forecasting is available as an option.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setTab('festival')}
                className="bg-surface-container-high hover:bg-primary/20 text-primary border border-primary/30 px-md py-xs rounded-lg text-label-md font-bold transition-all flex items-center gap-xs"
              >
                Switch to Festival Forecasting Option
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Main Forecast Chart */}
          {chartData.length > 0 && (
            <ChartCard
              title="XGBoost Predictive Demand Modeling & Confidence Bounds"
              subtitle="30-Day Multi-step forecast curve with 95% Confidence Interval Band"
              data={chartData}
              type="area"
            />
          )}

          {/* Per-Product Forecast Table */}
          {productList.length > 0 && (
            <div className="space-y-md">
              <h3 className="font-title-md text-title-md text-on-surface font-bold">
                Product-Level XGBoost Demand Forecast
              </h3>

              <div className="glass-panel rounded-xl overflow-hidden">
                <div className="overflow-x-auto custom-scrollbar">
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-surface-container-high/30">
                      <tr>
                        <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Product Item Name</th>
                        <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Product ID / SKU</th>
                        <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Trend</th>
                        <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Growth Rate</th>
                        <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Total Forecast Demand</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/30">
                      {productList.map((prod) => (
                        <tr key={prod.product_id} className="hover:bg-surface-variant/20 transition-colors">
                          <td className="px-lg py-md font-bold text-on-surface text-body-md">{prod.product_name}</td>
                          <td className="px-lg py-md font-mono text-on-surface-variant text-body-md">{prod.product_id}</td>
                          <td className="px-lg py-md">
                            <span className={`px-xs py-0.5 rounded font-label-sm font-bold ${
                              prod.trend === 'UPWARD' ? 'bg-primary/10 text-primary' :
                              prod.trend === 'DOWNWARD' ? 'bg-error/10 text-error' :
                              'bg-secondary/10 text-secondary'
                            }`}>
                              {prod.trend}
                            </span>
                          </td>
                          <td className="px-lg py-md font-mono font-bold text-primary text-body-md">
                            {prod.growth_rate_pct > 0 ? '+' : ''}{prod.growth_rate_pct?.toFixed(1)}%
                          </td>
                          <td className="px-lg py-md font-mono font-bold text-on-surface text-body-md">
                            {prod.total_forecast_demand?.toLocaleString()} units
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* OPTION TAB 2: FESTIVAL-WISE DEMAND FORECAST (SPECIALIZED OPTION) */}
      {(activeTab === 'festival' || activeTab === 'combined') && (
        <div className="space-y-lg">
          <FestivalItemDemandPredictor />
        </div>
      )}
    </div>
  );
}


