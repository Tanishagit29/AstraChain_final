import React, { useEffect, useState, useMemo } from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import { api } from '../api/client';
import {
  Boxes, AlertTriangle, ShieldAlert, Archive, CheckCircle, UploadCloud, Database,
  BarChart3, Search, Download
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid, Cell
} from 'recharts';

export default function InventoryIntelligence() {
  const [invData, setInvData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    api.getPipelineInventory().then((res) => {
      if (isMounted) {
        setInvData(res);
      }
      setLoading(false);
    });
    return () => { isMounted = false; };
  }, []);

  const summary = invData?.summary || {};
  const items = invData?.items || [];

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const matchesSearch =
        !searchQuery ||
        item.product_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.product_id?.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      if (filterRisk === 'STOCKOUT') return item.status === 'Stockout Risk' || item.status === 'Low Stock';
      if (filterRisk === 'OVERSTOCK') return item.status === 'Overstock';
      if (filterRisk === 'OPTIMAL') return item.status === 'Optimal Stock' || item.status === 'Healthy' || item.status === 'Available';
      return true;
    });
  }, [items, filterRisk, searchQuery]);

  // Chart dataset: Item Names on X-Axis
  const chartData = useMemo(() => {
    return filteredItems.slice(0, 15).map((item) => ({
      name: item.product_name ? (item.product_name.length > 15 ? item.product_name.slice(0, 15) + '...' : item.product_name) : item.product_id,
      full_name: item.product_name || item.product_id,
      product_id: item.product_id,
      current_stock: item.current_stock || 0,
      predicted_demand: item.predicted_demand || 0,
      stock_ratio: item.stock_ratio || 1.0,
      status: item.status,
    }));
  }, [filteredItems]);

  const exportCSV = () => {
    if (!filteredItems || filteredItems.length === 0) return;
    const headers = ['Product Item Name', 'Product ID', 'Current Stock', 'Predicted Demand', 'Stock Ratio', 'Status', 'Warehouse'];
    const rows = filteredItems.map(i => [
      `"${i.product_name}"`, i.product_id, i.current_stock, i.predicted_demand, i.stock_ratio, i.status, `"${i.warehouse}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `inventory_item_prediction_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Stockout Risk':
        return 'HIGH';
      case 'Low Stock':
        return 'MEDIUM';
      case 'Overstock':
        return 'OVERSTOCK';
      default:
        return 'HEALTHY';
    }
  };

  if (loading) {
    return (
      <div className="space-y-lg">
        <PageHeader title="Inventory Intelligence & Stock Risk Agent" subtitle="Loading inventory analysis..." />
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (!invData || !invData.has_data) {
    return (
      <div className="space-y-lg">
        <PageHeader
          title="Inventory Intelligence & Stock Risk Agent"
          subtitle="Stock levels, safety stock calculations, and stockout/overstock risk detection."
        />
        <div className="glass-card rounded-xl p-2xl flex flex-col items-center justify-center text-center space-y-md min-h-[400px]">
          <div className="w-20 h-20 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
            <UploadCloud className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-title-lg font-bold text-on-surface">No Inventory Data Available</h2>
          <p className="text-body-md text-on-surface-variant max-w-md">
            Upload a dataset from the <strong>Data Ingestion</strong> page to analyze inventory stock levels.
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

  return (
    <div className="space-y-lg">
      <PageHeader
        title="Inventory Intelligence & Stock Risk Agent"
        subtitle="Stock levels vs XGBoost predicted demand for item names — detecting Stockout Risks and Overstock conditions in real time."
      />

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-md">
        <KPICard
          title="Total Managed Items"
          value={String(summary.total_items || 0)}
          status="positive"
          subtitle="Active items in unified catalog"
          icon={Boxes}
          borderAccent="border-l-primary"
        />
        <KPICard
          title="Optimal Stock Ratio"
          value={`${summary.healthy_pct || 0}%`}
          status={summary.healthy_pct >= 70 ? "healthy" : "critical"}
          subtitle={`${summary.available_count || 0} of ${summary.total_items || 0} items optimal`}
          icon={CheckCircle}
          borderAccent="border-l-primary"
        />
        <KPICard
          title="Stockout Risk Items"
          value={String(summary.stockout_count || 0)}
          delta="Stockout Guard"
          status={summary.stockout_count > 0 ? "critical" : "healthy"}
          subtitle="Predicted demand exceeds stock"
          icon={ShieldAlert}
          borderAccent="border-l-error"
        />
        <KPICard
          title="Overstock Items"
          value={String(summary.overstock_count || 0)}
          status="healthy"
          subtitle="Stock exceeds 200% predicted demand"
          icon={Archive}
          borderAccent="border-l-secondary"
        />
      </div>

      {/* Dataset scope note (e.g. top-priority sample of a large dataset) */}
      {summary.displayed_items > 0 && summary.total_items > items.length && (
        <div className="p-sm rounded-lg bg-primary/10 border border-primary/20 flex gap-xs text-body-md text-primary">
          <Database className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Showing the {items.length} highest-priority items of {summary.total_items.toLocaleString()} store/SKU records
            {' '}— {(summary.stockout_count || 0).toLocaleString()} stockout-risk and {(summary.overstock_count || 0).toLocaleString()} overstock items in total.
          </span>
        </div>
      )}

      {/* Missing Warnings Banner */}
      {invData.missing_warnings && invData.missing_warnings.length > 0 && (
        <div className="space-y-xs">
          {invData.missing_warnings.map((warn, i) => (
            <div key={i} className="p-sm rounded-lg bg-tertiary/10 border border-tertiary/20 flex gap-xs text-body-md text-tertiary">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{warn}</span>
            </div>
          ))}
        </div>
      )}

      {/* DEDICATED INVENTORY PREDICTION GRAPH (ITEM NAMES ON X-AXIS) */}
      <div className="glass-card rounded-xl p-lg border border-outline-variant/60 space-y-md">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-md">
          <div className="flex items-center gap-xs">
            <div className="p-xs bg-primary/10 rounded-lg text-primary">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-title-md text-title-md font-bold text-on-surface flex items-center gap-2">
                Inventory Item Stockout & Overstock Prediction Graph
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/20">
                  PRODUCT ITEM NAMES
                </span>
              </h3>
              <p className="text-body-sm text-on-surface-variant">
                Visualizing Current Stock vs Predicted Demand for specific item names to detect supply imbalances
              </p>
            </div>
          </div>

          {/* Interactive Risk Filter Buttons */}
          <div className="flex flex-wrap items-center gap-xs bg-surface-container-low p-1 rounded-lg border border-outline-variant">
            <button
              onClick={() => setFilterRisk('ALL')}
              className={`px-sm py-xs font-label-sm text-label-sm rounded-md transition-all cursor-pointer ${
                filterRisk === 'ALL'
                  ? 'bg-primary text-on-primary font-bold shadow'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              All Items ({items.length})
            </button>
            <button
              onClick={() => setFilterRisk('STOCKOUT')}
              className={`px-sm py-xs font-label-sm text-label-sm rounded-md transition-all cursor-pointer flex items-center gap-1 ${
                filterRisk === 'STOCKOUT'
                  ? 'bg-error text-on-error font-bold shadow'
                  : 'text-error hover:bg-error/10'
              }`}
            >
              <ShieldAlert className="w-3 h-3" /> Stockout Risk ({summary.stockout_count || 0})
            </button>
            <button
              onClick={() => setFilterRisk('OVERSTOCK')}
              className={`px-sm py-xs font-label-sm text-label-sm rounded-md transition-all cursor-pointer flex items-center gap-1 ${
                filterRisk === 'OVERSTOCK'
                  ? 'bg-tertiary text-on-tertiary font-bold shadow'
                  : 'text-tertiary hover:bg-tertiary/10'
              }`}
            >
              <Archive className="w-3 h-3" /> Overstock ({summary.overstock_count || 0})
            </button>
            <button
              onClick={() => setFilterRisk('OPTIMAL')}
              className={`px-sm py-xs font-label-sm text-label-sm rounded-md transition-all cursor-pointer ${
                filterRisk === 'OPTIMAL'
                  ? 'bg-secondary text-on-secondary font-bold shadow'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Optimal Stock ({summary.available_count || 0})
            </button>
          </div>
        </div>

        {/* Recharts Bar Chart Canvas */}
        <div className="w-full h-[360px] chart-grid border-l border-b border-outline-variant/60 p-2 rounded-bl-sm relative">
          {chartData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-on-surface-variant italic">
              <p>No inventory items match the selected filter ({filterRisk}).</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={chartData} margin={{ top: 20, right: 20, left: -10, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" opacity={0.5} />
                <XAxis
                  dataKey="name"
                  stroke="#87929A"
                  fontSize={11}
                  fontFamily="JetBrains Mono"
                  interval={0}
                  angle={-25}
                  textAnchor="end"
                  tickLine={false}
                />
                <YAxis stroke="#87929A" fontSize={11} fontFamily="JetBrains Mono" tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111C2E',
                    borderColor: '#1E293B',
                    borderRadius: '8px',
                    color: '#DEE3E8',
                    fontFamily: 'JetBrains Mono',
                    fontSize: '12px',
                    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)'
                  }}
                  formatter={(value, name) => [
                    `${Number(value).toLocaleString()} units`,
                    name === 'current_stock' ? 'Current Stock' : 'Predicted Demand'
                  ]}
                  labelFormatter={(label, payload) => payload?.[0]?.payload?.full_name || label}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ paddingBottom: '10px', fontSize: '12px', fontFamily: 'JetBrains Mono' }}
                />
                <Bar dataKey="current_stock" name="Current Stock Level" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => {
                    const color = entry.status === 'Stockout Risk' ? '#FFB4AB' : (entry.status === 'Overstock' ? '#FFC176' : '#8ED5FF');
                    return <Cell key={`cell-${index}`} fill={color} />;
                  })}
                </Bar>
                <Bar dataKey="predicted_demand" name="XGBoost Predicted Demand" fill="#38BDF8" radius={[4, 4, 0, 0]} opacity={0.7} />
              </BarChart>
            </ResponsiveContainer>
          )}

          <div className="absolute top-2 left-4 text-[11px] font-mono text-on-surface-variant bg-surface-container-high/80 px-2 py-1 rounded border border-outline-variant">
            Bars: Red = Stockout Risk | Amber = Overstock | Cyan = Current Stock vs Demand
          </div>
        </div>
      </div>

      {/* SEARCH AND FULL INVENTORY ITEM TABLE (NAME OF ITEMS PROMINENT) */}
      <div className="space-y-md">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-md">
          <h3 className="font-title-md text-title-md text-on-surface font-bold">
            Inventory Stock Levels & Item Demand Breakdown
          </h3>

          <div className="flex items-center gap-sm flex-wrap w-full sm:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 text-on-surface-variant absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search item name or SKU..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-surface-container-high border border-outline-variant rounded-lg pl-9 pr-4 py-1.5 text-body-md text-on-surface focus:ring-1 focus:ring-primary w-full"
              />
            </div>

            {/* CSV Export Button */}
            <button
              onClick={exportCSV}
              className="bg-surface-container-high hover:bg-surface-container-highest text-on-surface border border-outline-variant px-md py-1.5 rounded-lg text-label-md font-bold transition-all flex items-center gap-xs cursor-pointer"
            >
              <Download className="w-4 h-4 text-primary" />
              Export CSV
            </button>
          </div>
        </div>

        <div className="glass-panel rounded-xl overflow-hidden border border-outline-variant/60">
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container-high/40">
                <tr>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Product Item Name</th>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">SKU / Product ID</th>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Current Stock</th>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Predicted Demand</th>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Stock Ratio</th>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Stock Risk Status</th>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Warehouse Location</th>
                  <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Recommended Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 text-body-md">
                {filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-lg py-xl text-center text-on-surface-variant italic">
                      No inventory items match the current search query or filter.
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item, idx) => (
                    <tr key={item.product_id || idx} className="hover:bg-surface-variant/20 transition-colors">
                      <td className="px-lg py-md font-bold text-on-surface">{item.product_name}</td>
                      <td className="px-lg py-md font-mono text-on-surface-variant">{item.product_id}</td>
                      <td className="px-lg py-md font-mono font-bold text-on-surface">
                        {item.current_stock?.toLocaleString()} units
                      </td>
                      <td className="px-lg py-md font-mono text-primary font-bold">
                        {item.predicted_demand?.toLocaleString()} units
                      </td>
                      <td className="px-lg py-md font-mono">
                        <span className={`px-xs py-0.5 rounded font-bold text-label-sm ${
                          item.stock_ratio < 0.35 ? 'bg-error/20 text-error' :
                          item.stock_ratio > 2.0 ? 'bg-tertiary/20 text-tertiary' :
                          'bg-primary/10 text-primary'
                        }`}>
                          {item.stock_ratio}x
                        </span>
                      </td>
                      <td className="px-lg py-md">
                        <StatusBadge status={getStatusBadge(item.status)} />
                      </td>
                      <td className="px-lg py-md text-on-surface-variant">{item.warehouse}</td>
                      <td className="px-lg py-md font-mono text-label-sm">
                        {item.recommended_action ? (
                          <span className={
                            item.status === 'Stockout Risk' ? 'text-error font-bold' :
                            item.status === 'Overstock' ? 'text-tertiary font-bold' :
                            item.status === 'Low Stock' ? 'text-secondary font-bold' : 'text-on-surface-variant'
                          }>
                            {item.recommended_action.replace(/_/g, ' ')}
                            {item.suggested_reorder_qty > 0 ? ` · ${item.suggested_reorder_qty.toLocaleString()} units` : ''}
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
