import React, { useEffect, useState, useMemo } from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import { api } from '../api/client';
import {
  Trash2, DollarSign, Tag, Zap, AlertTriangle, UploadCloud, Database, ShieldAlert,
  BarChart3, CheckCircle2, Flame, Search, ArrowRight, Plus, X, Sparkles, Clock, Package
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid, Cell
} from 'recharts';

const SAMPLE_NEAR_EXPIRY_ITEMS = [
  { product_name: 'Amul Taaza Toned Milk 1L', category: 'Dairy & Refrigerated', days_remaining: 1, unit_cost: '₹72', current_stock: 120 },
  { product_name: 'Organic Greek Yogurt 500g', category: 'Dairy & Refrigerated', days_remaining: 2, unit_cost: '₹150', current_stock: 65 },
  { product_name: 'Fresh Strawberries 250g', category: 'Fresh Produce', days_remaining: 3, unit_cost: '₹199', current_stock: 40 },
  { product_name: 'Artisanal Sourdough Bread', category: 'Bakery & Bread', days_remaining: 4, unit_cost: '₹110', current_stock: 25 },
  { product_name: 'Fresh Paneer 200g', category: 'Dairy & Refrigerated', days_remaining: 2, unit_cost: '₹95', current_stock: 80 },
  { product_name: 'Free Range Eggs (Pack of 6)', category: 'Poultry & Meat', days_remaining: 5, unit_cost: '₹65', current_stock: 110 }
];

export default function WastageManagement() {
  const [wastageData, setWastageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterDecision, setFilterDecision] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [actionSuccess, setActionSuccess] = useState(null);

  // Modal & Form State for Adding Near-Expiry Items
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newItem, setNewItem] = useState({
    product_name: '',
    product_id: '',
    category: 'Dairy & Refrigerated',
    days_remaining: 3,
    expiry_date: '',
    discount_override: '',
    unit_cost: '₹120',
    current_stock: 100,
  });

  const navigate = useNavigate();

  const fetchWastageData = async () => {
    try {
      const res = await api.getPipelineWastage();
      setWastageData(res);
    } catch (err) {
      console.error('Failed to fetch wastage data:', err);
    }
  };

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    api.getPipelineWastage().then((res) => {
      if (isMounted) {
        setWastageData(res);
      }
      setLoading(false);
    });
    return () => { isMounted = false; };
  }, []);

  const summary = wastageData?.summary || {};
  const decisions = wastageData?.decisions || [];
  const expiryAvailable = wastageData?.expiry_available;

  const filteredDecisions = useMemo(() => {
    return decisions.filter((d) => {
      const matchesSearch =
        !searchQuery ||
        d.product_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.product_id?.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      if (filterDecision === 'NEAR_EXPIRY') return d.days_remaining !== null && d.days_remaining <= 5 && d.days_remaining >= 0;
      if (filterDecision === 'EXPIRED') return d.decision === 'Do Not Sell' || (d.days_remaining !== null && d.days_remaining < 0);
      if (filterDecision === 'NORMAL') return d.days_remaining !== null && d.days_remaining > 5;
      return true;
    });
  }, [decisions, filterDecision, searchQuery]);

  // Chart data: Item Name vs Days Remaining to Expiry
  const itemChartData = useMemo(() => {
    const valid = decisions.filter(d => d.days_remaining !== null && d.days_remaining !== undefined);
    const sorted = [...valid].sort((a, b) => a.days_remaining - b.days_remaining);

    return sorted.slice(0, 15).map((item) => {
      const name = item.product_name || item.product_id;
      const shortName = name.length > 15 ? name.slice(0, 15) + '...' : name;
      const days = item.days_remaining;
      let fill = '#38BDF8';
      if (days < 0) fill = '#FFB4AB';
      else if (days <= 2) fill = '#FF9800';
      else if (days <= 5) fill = '#FFC176';
      else if (days <= 10) fill = '#BDC2FF';

      return {
        item_name: shortName,
        full_name: name,
        product_id: item.product_id,
        days_remaining: days,
        abs_days: Math.max(0, days),
        decision: item.decision,
        discount: item.discount,
        fill: fill,
      };
    });
  }, [decisions]);

  const handleApplyDiscountAction = async (item) => {
    try {
      await api.executeKeyAction({
        action_type: 'DISCOUNT_SUGGESTION',
        target_id: item.product_id || item.product_name,
        details: `Dynamic promo markdown applied for batch ${item.product_name}`
      });
      setActionSuccess(`Promo Markdown Applied: ${item.product_name} (${item.discount})`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (e) {
      console.error('Failed to execute discount action:', e);
    }
  };

  const handleAddNearExpirySubmit = async (e) => {
    if (e) e.preventDefault();
    if (!newItem.product_name.trim()) return;

    setSubmitting(true);
    try {
      const res = await api.addNearExpiryItem({
        product_name: newItem.product_name,
        product_id: newItem.product_id || undefined,
        category: newItem.category,
        days_remaining: parseInt(newItem.days_remaining, 10),
        expiry_date: newItem.expiry_date || undefined,
        discount_override: newItem.discount_override || undefined,
        unit_cost: newItem.unit_cost,
        current_stock: parseInt(newItem.current_stock, 10),
      });

      setActionSuccess(`Added "${res.data.product_name}" to Wastage Agent! Assigned Discount: ${res.data.discount}`);
      setShowAddModal(false);
      setNewItem({
        product_name: '',
        product_id: '',
        category: 'Dairy & Refrigerated',
        days_remaining: 3,
        expiry_date: '',
        discount_override: '',
        unit_cost: '₹120',
        current_stock: 100,
      });

      await fetchWastageData();
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err) {
      console.error('Failed to add near-expiry item:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddQuickSample = async (sampleData) => {
    const sample = sampleData || SAMPLE_NEAR_EXPIRY_ITEMS[Math.floor(Math.random() * SAMPLE_NEAR_EXPIRY_ITEMS.length)];
    setLoading(true);
    try {
      const res = await api.addNearExpiryItem(sample);
      setActionSuccess(`Added sample near-to-expire item "${res.data.product_name}" (${res.data.days_remaining}d remaining) — Assigned ${res.data.discount}!`);
      await fetchWastageData();
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err) {
      console.error('Failed to add sample near-expiry item:', err);
    } finally {
      setLoading(false);
    }
  };

  const getDecisionBadge = (decision) => {
    switch (decision) {
      case 'Apply Discount':
        return 'MEDIUM';
      case 'Do Not Sell':
        return 'HIGH';
      default:
        return 'HEALTHY';
    }
  };

  if (loading) {
    return (
      <div className="space-y-lg">
        <PageHeader title="Automation & Expiry Agent" subtitle="Loading expiry analysis..." />
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  const nearExpiryItems = decisions.filter(d => d.days_remaining !== null && d.days_remaining <= 5 && d.days_remaining >= 0);
  const expiredItems = decisions.filter(d => d.decision === 'Do Not Sell' || (d.days_remaining !== null && d.days_remaining < 0));

  const actionButtons = (
    <div className="flex items-center gap-xs flex-wrap">
      <button
        onClick={() => handleAddQuickSample()}
        className="bg-tertiary/15 hover:bg-tertiary/25 text-tertiary border border-tertiary/30 font-bold px-md py-sm rounded-lg text-label-md flex items-center gap-xs transition-all cursor-pointer"
        title="Add a sample perishable item to monitor expiry shelf-life"
      >
        <Sparkles className="w-4 h-4" />
        Quick Add Sample
      </button>
      <button
        onClick={() => setShowAddModal(true)}
        className="bg-primary hover:bg-primary/90 text-on-primary font-bold px-md py-sm rounded-lg text-label-md flex items-center gap-xs transition-all shadow-lg shadow-primary/20 cursor-pointer"
      >
        <Plus className="w-4 h-4" />
        Add Near-Expiry Item
      </button>
    </div>
  );

  if (!wastageData || !wastageData.has_data) {
    return (
      <div className="space-y-lg">
        <PageHeader
          title="Automation & Expiry Agent"
          subtitle="Monitors perishable shelf life, detects near-expiry items, and flags batches requiring expedited transit or quarantine."
          actions={actionButtons}
        />

        {actionSuccess && (
          <div className="p-md rounded-xl bg-primary/10 border border-primary/30 flex items-center gap-sm text-primary font-bold shadow-md animate-fade-in">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}

        <div className="glass-card rounded-xl p-2xl flex flex-col items-center justify-center text-center space-y-md min-h-[400px]">
          <div className="w-20 h-20 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
            <UploadCloud className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-title-lg font-bold text-on-surface">No Wastage Analysis Available</h2>
          <p className="text-body-md text-on-surface-variant max-w-md">
            Add near-to-expire items directly to run shelf-life analysis, or upload a dataset from Data Ingestion.
          </p>
          <div className="flex items-center gap-md flex-wrap justify-center mt-md">
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-primary text-on-primary font-bold rounded-lg px-lg py-md text-label-md hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary/20 flex items-center gap-xs cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Add Near-Expiry Item
            </button>
            <button
              onClick={() => handleAddQuickSample()}
              className="bg-tertiary/20 text-tertiary border border-tertiary/40 font-bold rounded-lg px-lg py-md text-label-md hover:bg-tertiary/30 transition-all flex items-center gap-xs cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              Load Sample Near-Expiry Items
            </button>
            <button
              onClick={() => navigate('/data-collection')}
              className="bg-surface-container-high text-on-surface font-bold rounded-lg px-lg py-md text-label-md hover:bg-surface-variant transition-all border border-outline-variant flex items-center gap-xs cursor-pointer"
            >
              <Database className="w-4 h-4" />
              Go to Data Ingestion
            </button>
          </div>
        </div>

        {/* RENDER MODAL EVEN IN EMPTY STATE */}
        {showAddModal && renderAddModal()}
      </div>
    );
  }

  function renderAddModal() {
    return (
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[100] flex items-center justify-center p-md animate-fade-in">
        <div className="bg-surface-container-high border border-outline-variant rounded-2xl p-xl max-w-lg w-full shadow-2xl space-y-md relative">
          <div className="flex items-center justify-between border-b border-outline-variant/60 pb-sm">
            <div className="flex items-center gap-xs text-primary font-bold text-title-md">
              <Clock className="w-5 h-5" />
              <h3>Add Near-to-Expire Item</h3>
            </div>
            <button
              onClick={() => setShowAddModal(false)}
              className="p-1 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <p className="text-body-sm text-on-surface-variant">
            Enter item details below. The <strong>Automation & Expiry Agent</strong> will track remaining shelf life and flag batches requiring expedited transit or quarantine.
          </p>

          <form onSubmit={handleAddNearExpirySubmit} className="space-y-sm">
            <div>
              <label className="block text-label-sm text-on-surface-variant uppercase font-mono mb-1">
                Product Item Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Organic Whole Milk 1L, Fresh Strawberries"
                value={newItem.product_name}
                onChange={(e) => setNewItem({ ...newItem, product_name: e.target.value })}
                className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-2 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-sm">
              <div>
                <label className="block text-label-sm text-on-surface-variant uppercase font-mono mb-1">
                  Item SKU / Code (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. SKU-MLK-101"
                  value={newItem.product_id}
                  onChange={(e) => setNewItem({ ...newItem, product_id: e.target.value })}
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-2 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-label-sm text-on-surface-variant uppercase font-mono mb-1">
                  Category
                </label>
                <select
                  value={newItem.category}
                  onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-2 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
                >
                  <option value="Dairy & Refrigerated">Dairy & Refrigerated</option>
                  <option value="Fresh Produce">Fresh Produce</option>
                  <option value="Poultry & Meat">Poultry & Meat</option>
                  <option value="Bakery & Bread">Bakery & Bread</option>
                  <option value="Frozen Foods">Frozen Foods</option>
                  <option value="Beverages">Beverages</option>
                  <option value="General">General</option>
                </select>
              </div>
            </div>

            {/* Days Remaining & Preset Buttons */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-label-sm text-on-surface-variant uppercase font-mono">
                  Days Remaining to Expiry: <strong className="text-primary font-bold font-mono">{newItem.days_remaining} day(s)</strong>
                </label>
                <span className="text-[11px] font-mono text-tertiary">
                  {newItem.days_remaining <= 0 ? 'Quarantined (100% Off)' :
                   newItem.days_remaining <= 2 ? 'Auto 50% Markdown' :
                   newItem.days_remaining <= 5 ? 'Auto 30% Promo' :
                   newItem.days_remaining <= 7 ? 'Auto 20% Discount' : 'Auto 10% Discount'}
                </span>
              </div>
              <input
                type="range"
                min="-2"
                max="14"
                value={newItem.days_remaining}
                onChange={(e) => setNewItem({ ...newItem, days_remaining: parseInt(e.target.value, 10) })}
                className="w-full accent-primary cursor-pointer"
              />
              <div className="flex gap-1 mt-1.5 flex-wrap">
                <button
                  type="button"
                  onClick={() => setNewItem({ ...newItem, days_remaining: 1 })}
                  className={`px-2 py-0.5 text-[11px] font-mono rounded border cursor-pointer ${newItem.days_remaining === 1 ? 'bg-error text-on-error font-bold' : 'bg-surface-container-low border-outline-variant text-on-surface-variant'}`}
                >
                  1 Day (50% Off)
                </button>
                <button
                  type="button"
                  onClick={() => setNewItem({ ...newItem, days_remaining: 3 })}
                  className={`px-2 py-0.5 text-[11px] font-mono rounded border cursor-pointer ${newItem.days_remaining === 3 ? 'bg-tertiary text-on-tertiary font-bold' : 'bg-surface-container-low border-outline-variant text-on-surface-variant'}`}
                >
                  3 Days (30% Off)
                </button>
                <button
                  type="button"
                  onClick={() => setNewItem({ ...newItem, days_remaining: 5 })}
                  className={`px-2 py-0.5 text-[11px] font-mono rounded border cursor-pointer ${newItem.days_remaining === 5 ? 'bg-tertiary/80 text-on-tertiary font-bold' : 'bg-surface-container-low border-outline-variant text-on-surface-variant'}`}
                >
                  5 Days (20% Off)
                </button>
                <button
                  type="button"
                  onClick={() => setNewItem({ ...newItem, days_remaining: 0 })}
                  className={`px-2 py-0.5 text-[11px] font-mono rounded border cursor-pointer ${newItem.days_remaining === 0 ? 'bg-error/30 text-error font-bold border-error' : 'bg-surface-container-low border-outline-variant text-on-surface-variant'}`}
                >
                  0 Days (Expired)
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-sm">
              <div>
                <label className="block text-label-sm text-on-surface-variant uppercase font-mono mb-1">
                  Unit Price / Cost
                </label>
                <input
                  type="text"
                  placeholder="e.g. ₹120"
                  value={newItem.unit_cost}
                  onChange={(e) => setNewItem({ ...newItem, unit_cost: e.target.value })}
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-2 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-label-sm text-on-surface-variant uppercase font-mono mb-1">
                  Stock Units
                </label>
                <input
                  type="number"
                  min="1"
                  value={newItem.current_stock}
                  onChange={(e) => setNewItem({ ...newItem, current_stock: parseInt(e.target.value, 10) || 1 })}
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-2 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>
            </div>



            <div className="pt-md flex items-center justify-end gap-sm border-t border-outline-variant/60">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="px-md py-2 rounded-lg text-body-md font-bold text-on-surface-variant hover:bg-surface-variant transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="bg-primary hover:bg-primary/90 text-on-primary font-bold px-lg py-2 rounded-lg text-body-md transition-all flex items-center gap-xs shadow-lg shadow-primary/20 cursor-pointer disabled:opacity-50"
              >
                {submitting ? (
                  <div className="animate-spin w-4 h-4 border-2 border-on-primary border-t-transparent rounded-full" />
                ) : (
                  <>
                    <Flame className="w-4 h-4" />
                    Add to Expiry Tracking
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-lg">
      <PageHeader
        title="Automation & Expiry Agent"
        subtitle="Monitors perishable shelf life, detects near-expiry items, and flags batches requiring expedited transit or quarantine."
        actions={actionButtons}
      />

      {actionSuccess && (
        <div className="p-md rounded-xl bg-primary/10 border border-primary/30 flex items-center gap-sm text-primary font-bold shadow-md animate-fade-in">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        <KPICard
          title="Total Managed Items"
          value={String(summary.total_products || 0)}
          status="positive"
          subtitle="Active product items monitored"
          icon={Trash2}
        />
        <KPICard
          title="Near-Expiry Items"
          value={String(summary.near_expiry_count || 0)}
          delta={summary.near_expiry_count > 0 ? 'Action Required' : 'All Clear'}
          status={summary.near_expiry_count > 0 ? "warning" : "healthy"}
          subtitle={`${summary.near_expiry_pct || 0}% near expiration`}
          icon={Tag}
        />
        <KPICard
          title="Near-Expiry Critical Batch"
          value={String(nearExpiryItems.length || summary.near_expiry_count || 0)}
          status={nearExpiryItems.length > 0 ? "warning" : "healthy"}
          subtitle="Shelf life <= 5 days remaining"
          icon={Flame}
        />
        <KPICard
          title="Expired Items"
          value={String(summary.expired_count || 0)}
          status={summary.expired_count > 0 ? "critical" : "healthy"}
          subtitle={summary.expired_count > 0 ? "Do Not Sell" : "No expired items"}
          icon={ShieldAlert}
        />
      </div>

      {summary.displayed_items > 0 && summary.near_expiry_count > decisions.length && (
        <div className="p-sm rounded-lg bg-primary/10 border border-primary/20 text-body-md text-primary">
          Showing the {decisions.length} most valuable near-expiry items of {summary.near_expiry_count.toLocaleString()} flagged.
          Shelf-life thresholds: Critical (≤2 days) · Urgent (≤5 days) · Safe (&gt;5 days).
        </div>
      )}

      {!expiryAvailable && (
        <div className="p-md rounded-xl bg-tertiary/10 border border-tertiary/30 flex gap-sm text-body-md">
          <AlertTriangle className="w-5 h-5 text-tertiary shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-tertiary text-label-md">Expiry Date Field Warning</p>
            <p className="text-on-surface-variant text-[13px] mt-xs">
              Your uploaded dataset does not contain an explicit <code className="bg-surface-container-high px-xs rounded font-mono text-primary">expiry_date</code> column. 
              You can manually add near-to-expire items above or dynamic shelf-life estimation is used.
            </p>
          </div>
        </div>
      )}

      {/* DEDICATED NEAR-TO-EXPIRE ITEM GRAPH (ITEM NAMES ON X-AXIS) */}
      <div className="glass-card rounded-xl p-lg border border-outline-variant/60 space-y-md">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-md">
          <div className="flex items-center gap-xs">
            <div className="p-xs bg-tertiary/15 rounded-lg text-tertiary">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-title-md text-title-md font-bold text-on-surface flex items-center gap-2">
                Near-to-Expire Item Expiry Graph
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-tertiary/15 text-tertiary border border-tertiary/20">
                  PRODUCT ITEM NAMES
                </span>
              </h3>
              <p className="text-body-sm text-on-surface-variant">
                Visualizing Days Remaining to Expiry for individual item names to monitor shelf-life and prevent spoilage
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="text-label-sm font-bold text-primary bg-primary/10 hover:bg-primary/20 px-sm py-1 rounded-lg border border-primary/20 transition-all flex items-center gap-1 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Near-Expiry Item
          </button>
        </div>

        <div className="w-full h-[320px] chart-grid border-l border-b border-outline-variant/60 p-2 rounded-bl-sm relative">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={itemChartData} margin={{ top: 15, right: 20, left: -10, bottom: 35 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" opacity={0.5} />
              <XAxis
                dataKey="item_name"
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
                formatter={(value, name, item) => [
                  `${item.payload.days_remaining < 0 ? `Expired (${Math.abs(item.payload.days_remaining)}d ago)` : `${value} Day(s) Remaining`}`,
                  'Days To Expiry'
                ]}
                labelFormatter={(label, payload) => payload?.[0]?.payload?.full_name || label}
              />
              <Bar dataKey="abs_days" name="Days to Expiry" radius={[4, 4, 0, 0]}>
                {itemChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="absolute top-2 left-4 text-[11px] font-mono text-on-surface-variant bg-surface-container-high/80 px-2 py-1 rounded border border-outline-variant">
            Bars: Red = Expired | Orange = 0-2 Days | Amber = 3-5 Days | Indigo/Cyan = Safe
          </div>
        </div>
      </div>

      {/* EXPIRED ITEMS ALERT CARDS */}
      {expiredItems.length > 0 && (
        <div className="glass-card rounded-xl p-lg space-y-md border border-error/30">
          <div className="flex items-center gap-xs text-error">
            <ShieldAlert className="w-5 h-5" />
            <h3 className="font-title-md text-title-md text-on-surface font-bold">Expired Items — Quarantined / Do Not Sell</h3>
          </div>
          <div className="space-y-xs">
            {expiredItems.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between p-sm rounded-lg bg-error/10 border border-error/20">
                <div>
                  <span className="font-bold text-on-surface">{item.product_name}</span>
                  <span className="text-on-surface-variant text-label-sm ml-sm font-mono">{item.product_id} • {item.expiry_date}</span>
                </div>
                <span className="px-sm py-xs rounded bg-error text-on-primary font-label-sm font-bold">EXPIRED</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SEARCH AND WASTAGE DECISIONS TABLE (ITEM NAMES EMPHASIZED) */}
      <div className="glass-panel rounded-xl overflow-hidden flex flex-col border border-outline-variant/60">
        <div className="p-lg border-b border-outline-variant bg-surface-container-low/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-md">
          <div className="flex items-center gap-md">
            <h3 className="font-title-md text-title-md font-bold text-on-surface">All Item Wastage & Expiry Decisions</h3>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-2 py-1 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-label-sm font-bold transition-all flex items-center gap-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Item
            </button>
          </div>

          <div className="flex items-center gap-sm flex-wrap w-full sm:w-auto">
            {/* Decision Filter Pills */}
            <div className="flex items-center gap-xs bg-surface-container-high p-1 rounded-lg border border-outline-variant">
              <button
                onClick={() => setFilterDecision('ALL')}
                className={`px-sm py-xs font-label-sm text-label-sm rounded-md transition-all cursor-pointer ${
                  filterDecision === 'ALL' ? 'bg-primary text-on-primary font-bold shadow' : 'text-on-surface-variant'
                }`}
              >
                All ({decisions.length})
              </button>
              <button
                onClick={() => setFilterDecision('NEAR_EXPIRY')}
                className={`px-sm py-xs font-label-sm text-label-sm rounded-md transition-all cursor-pointer ${
                  filterDecision === 'NEAR_EXPIRY' ? 'bg-tertiary text-on-tertiary font-bold shadow' : 'text-tertiary'
                }`}
              >
                Near Expiry ({nearExpiryItems.length})
              </button>
              <button
                onClick={() => setFilterDecision('EXPIRED')}
                className={`px-sm py-xs font-label-sm text-label-sm rounded-md transition-all cursor-pointer ${
                  filterDecision === 'EXPIRED' ? 'bg-error text-on-error font-bold shadow' : 'text-error'
                }`}
              >
                Expired ({expiredItems.length})
              </button>
            </div>

            {/* Search Input */}
            <div className="relative flex-1 sm:w-56">
              <Search className="w-4 h-4 text-on-surface-variant absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search item name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-surface-container-high border border-outline-variant rounded-lg pl-9 pr-4 py-1.5 text-body-md text-on-surface focus:ring-1 focus:ring-primary w-full"
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead className="bg-surface-container-high/30">
              <tr>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Product Item Name</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Item Code / SKU</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Expiry Date</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Days Remaining</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Decision</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Expiry Urgency</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Reason & Agent Intervention</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 text-body-md">
              {filteredDecisions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-lg py-xl text-center text-on-surface-variant italic">
                    No wastage item decisions match the current filter or search query.
                  </td>
                </tr>
              ) : (
                filteredDecisions.map((item, idx) => (
                  <tr key={idx} className="hover:bg-surface-variant/20 transition-colors">
                    <td className="px-lg py-md">
                      <div className="font-bold text-on-surface text-body-md">{item.product_name}</div>
                    </td>
                    <td className="px-lg py-md font-mono text-on-surface-variant">{item.product_id}</td>
                    <td className="px-lg py-md font-mono text-on-surface-variant">
                      {item.expiry_date || 'N/A'}
                    </td>
                    <td className="px-lg py-md font-mono font-bold">
                      {item.days_remaining !== null && item.days_remaining !== undefined ? (
                        item.days_remaining < 0 ? (
                          <span className="px-xs py-0.5 rounded bg-error/20 text-error font-bold text-[12px]">
                            Expired ({Math.abs(item.days_remaining)}d ago)
                          </span>
                        ) : (
                          <span className={item.days_remaining <= 2 ? 'text-error font-bold' : item.days_remaining <= 5 ? 'text-tertiary font-bold' : 'text-on-surface'}>
                            {item.days_remaining} {item.days_remaining === 1 ? 'day' : 'days'}
                          </span>
                        )
                      ) : (
                        <span className="text-on-surface-variant">—</span>
                      )}
                    </td>
                    <td className="px-lg py-md">
                      <StatusBadge status={getDecisionBadge(item.decision)} />
                    </td>
                    <td className="px-lg py-md font-mono font-bold">
                      {item.days_remaining !== null && item.days_remaining !== undefined ? (
                        item.days_remaining <= 0 ? (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-error/20 text-error border border-error/30">QUARANTINE</span>
                        ) : item.days_remaining <= 2 ? (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-error/15 text-error border border-error/25">CRITICAL (&lt;=2d)</span>
                        ) : item.days_remaining <= 5 ? (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#FF9800]/15 text-[#FF9800] border border-[#FF9800]/25">URGENT (&lt;=5d)</span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">SAFE (&gt;5d)</span>
                        )
                      ) : (
                        <span className="text-on-surface-variant text-[11px]">NORMAL</span>
                      )}
                    </td>
                    <td className="px-lg py-md text-on-surface-variant max-w-xs truncate" title={item.reason}>
                      {item.reason}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* RENDER ADD MODAL */}
      {showAddModal && renderAddModal()}
    </div>
  );
}
