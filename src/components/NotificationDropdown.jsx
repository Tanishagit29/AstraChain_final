import React, { useState, useEffect, useRef } from 'react';
import { 
  Bell, AlertTriangle, CheckCircle2, RotateCw, CheckCheck, 
  Zap, Package, ShieldAlert, Sparkles, X, ChevronRight, Info,
  Clock, Flame, Gift, Volume2, VolumeX, Trash2, Search, Play,
  Smartphone
} from 'lucide-react';
import { useLiveNotifications } from '../context/NotificationContext';
import PhoneIntegrationModal from './PhoneIntegrationModal';

export default function NotificationDropdown({ onRestockComplete }) {
  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState('ALL'); // 'ALL', 'STOCKOUT', 'WASTAGE', 'FESTIVAL', 'RESTOCKED'
  const [searchQuery, setSearchQuery] = useState('');
  const [actionInProgress, setActionInProgress] = useState({});
  const [showSimMenu, setShowSimMenu] = useState(false);
  const [showPhoneModal, setShowPhoneModal] = useState(false);

  const dropdownRef = useRef(null);

  const {
    notifications,
    counts,
    loading,
    isWsConnected,
    soundEnabled,
    toggleSound,
    handleRestock,
    handleMitigateWastage,
    handlePrestockFestival,
    handleMarkAllRead,
    handleMarkRead,
    handleDismiss,
    handleSimulate,
    refreshNotifications,
  } = useLiveNotifications();

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setShowSimMenu(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Action wrappers with loading tracking
  const onRestockClick = async (n, e) => {
    if (e) e.stopPropagation();
    setActionInProgress((prev) => ({ ...prev, [n.id]: true }));
    try {
      const res = await handleRestock(n);
      if (res && onRestockComplete) {
        onRestockComplete(res);
      }
    } finally {
      setActionInProgress((prev) => ({ ...prev, [n.id]: false }));
    }
  };

  const onWastageClick = async (n, e) => {
    if (e) e.stopPropagation();
    setActionInProgress((prev) => ({ ...prev, [n.id]: true }));
    try {
      await handleMitigateWastage(n);
    } finally {
      setActionInProgress((prev) => ({ ...prev, [n.id]: false }));
    }
  };

  const onFestivalClick = async (n, e) => {
    if (e) e.stopPropagation();
    setActionInProgress((prev) => ({ ...prev, [n.id]: true }));
    try {
      await handlePrestockFestival(n);
    } finally {
      setActionInProgress((prev) => ({ ...prev, [n.id]: false }));
    }
  };

  const onSimulateClick = async (type) => {
    setShowSimMenu(false);
    await handleSimulate(type);
  };

  // Filter & Search
  const filteredNotifications = notifications.filter((n) => {
    // Category Filter
    if (filter === 'STOCKOUT') {
      if (n.type !== 'STOCKOUT') return false;
    } else if (filter === 'WASTAGE') {
      if (n.type !== 'WASTAGE') return false;
    } else if (filter === 'FESTIVAL') {
      if (n.type !== 'FESTIVAL') return false;
    } else if (filter === 'RESTOCKED') {
      if (n.type !== 'RESTOCKED' && !n.is_restocked && n.severity !== 'SUCCESS') return false;
    }

    // Keyword Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = (n.title || '').toLowerCase().includes(q);
      const matchMsg = (n.message || '').toLowerCase().includes(q);
      const matchProd = (n.product_name || '').toLowerCase().includes(q);
      const matchPid = (n.product_id || '').toLowerCase().includes(q);
      const matchFest = (n.festival_name || '').toLowerCase().includes(q);
      return matchTitle || matchMsg || matchProd || matchPid || matchFest;
    }

    return true;
  });

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high rounded-full transition-all relative cursor-pointer"
        title="Manager Operational Notification Hub"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />

        {/* Unread Counter Badge */}
        {counts.unread_count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[20px] h-5 px-1 bg-error text-on-error rounded-full text-[11px] font-bold font-mono flex items-center justify-center shadow-md animate-pulse">
            {counts.unread_count > 99 ? '99+' : counts.unread_count}
          </span>
        )}

        {/* Live WebSocket Status Dot */}
        <span
          className={`absolute bottom-1 right-1 w-2.5 h-2.5 rounded-full border-2 border-surface ${
            isWsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
          }`}
          title={isWsConnected ? 'Live WebSocket Connected' : 'Auto-Sync Polling Active'}
        />
      </button>

      {/* Popover Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-3 w-84 sm:w-[480px] max-h-[88vh] bg-surface/95 backdrop-blur-2xl border border-outline-variant/80 rounded-2xl shadow-2xl shadow-black/60 z-50 flex flex-col overflow-hidden animate-fade-in">
          {/* Header */}
          <div className="p-4 border-b border-outline-variant/50 bg-surface-container-low/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                <Bell className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-on-surface text-[14px]">
                    Manager Notification Hub
                  </h3>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center gap-1 border ${
                      isWsConnected
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${isWsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                    {isWsConnected ? 'Live Real-Time' : 'Auto-Sync'}
                  </span>
                </div>
                <p className="text-[11px] text-on-surface-variant font-mono">
                  Stockouts, Wastage, Restocking & Festival Surges
                </p>
              </div>
            </div>

            {/* Header Action Controls */}
            <div className="flex items-center gap-1">
              {/* Sound Alert Toggle */}
              <button
                onClick={toggleSound}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  soundEnabled
                    ? 'text-primary hover:bg-primary/10'
                    : 'text-on-surface-variant/50 hover:bg-surface-container-high'
                }`}
                title={soundEnabled ? 'Mute Alert Chimes' : 'Unmute Alert Chimes'}
              >
                {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              </button>

              {/* Refresh */}
              <button
                onClick={refreshNotifications}
                disabled={loading}
                className="p-1.5 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container-high transition-colors cursor-pointer"
                title="Refresh notifications"
              >
                <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-primary' : ''}`} />
              </button>

              {/* Mark All Read */}
              {counts.unread_count > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="p-1.5 text-on-surface-variant hover:text-primary rounded-lg hover:bg-surface-container-high transition-colors cursor-pointer text-[11px] flex items-center gap-1"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-4 h-4" />
                </button>
              )}

              {/* Close */}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container-high transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Quick Simulation Trigger Bar */}
          <div className="px-4 py-2 bg-surface-container-high/40 border-b border-outline-variant/30 flex items-center justify-between text-[11px]">
            <span className="font-mono text-on-surface-variant flex items-center gap-1">
              <Play className="w-3 h-3 text-primary" /> Test Live Alerts:
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => onSimulateClick('stockout')}
                className="bg-error/15 hover:bg-error/25 text-error border border-error/30 font-bold px-2 py-0.5 rounded-md transition-all cursor-pointer"
                title="Simulate live stockout alert"
              >
                + Stockout
              </button>
              <button
                onClick={() => onSimulateClick('restock')}
                className="bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30 font-bold px-2 py-0.5 rounded-md transition-all cursor-pointer"
                title="Simulate live restocking fulfillment"
              >
                + Restock
              </button>
              <button
                onClick={() => onSimulateClick('wastage')}
                className="bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 font-bold px-2 py-0.5 rounded-md transition-all cursor-pointer"
                title="Simulate near-expiry perishable wastage alert"
              >
                + Wastage
              </button>
              <button
                onClick={() => onSimulateClick('festival')}
                className="bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/30 font-bold px-2 py-0.5 rounded-md transition-all cursor-pointer"
                title="Simulate festival demand surge recommendation"
              >
                + Festival
              </button>
            </div>
          </div>

          {/* Search Field */}
          <div className="px-4 py-2 border-b border-outline-variant/30 bg-surface-container-lowest/30 flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-on-surface-variant" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by product, SKU, festival, or warehouse..."
              className="w-full bg-transparent text-[12px] text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-on-surface-variant hover:text-on-surface"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div className="px-4 py-2 bg-surface-container-lowest/50 border-b border-outline-variant/30 flex items-center gap-1.5 overflow-x-auto custom-scrollbar text-[11px] font-medium">
            <button
              onClick={() => setFilter('ALL')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer shrink-0 ${
                filter === 'ALL'
                  ? 'bg-primary text-on-primary font-bold shadow'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
              }`}
            >
              All ({notifications.length})
            </button>
            <button
              onClick={() => setFilter('STOCKOUT')}
              className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 cursor-pointer shrink-0 ${
                filter === 'STOCKOUT'
                  ? 'bg-error text-on-error font-bold shadow'
                  : 'text-error hover:bg-error/10'
              }`}
            >
              <Zap className="w-3 h-3" />
              Stockouts ({counts.stockout_count})
            </button>
            <button
              onClick={() => setFilter('WASTAGE')}
              className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 cursor-pointer shrink-0 ${
                filter === 'WASTAGE'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow'
                  : 'text-amber-400 hover:bg-amber-500/10'
              }`}
            >
              <Clock className="w-3 h-3" />
              Wastage ({counts.wastage_count})
            </button>
            <button
              onClick={() => setFilter('FESTIVAL')}
              className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 cursor-pointer shrink-0 ${
                filter === 'FESTIVAL'
                  ? 'bg-purple-600 text-white font-bold shadow'
                  : 'text-purple-300 hover:bg-purple-500/10'
              }`}
            >
              <Sparkles className="w-3 h-3" />
              Festival ({counts.festival_count})
            </button>
            <button
              onClick={() => setFilter('RESTOCKED')}
              className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 cursor-pointer shrink-0 ${
                filter === 'RESTOCKED'
                  ? 'bg-emerald-600 text-white font-bold shadow'
                  : 'text-emerald-400 hover:bg-emerald-500/10'
              }`}
            >
              <CheckCircle2 className="w-3 h-3" />
              Restocked ({counts.restocked_count})
            </button>
          </div>

          {/* Notification List Scroll Area */}
          <div className="flex-1 overflow-y-auto max-h-[460px] custom-scrollbar divide-y divide-outline-variant/20">
            {filteredNotifications.length === 0 ? (
              <div className="p-8 text-center space-y-2 text-on-surface-variant">
                <CheckCircle2 className="w-8 h-8 text-emerald-400/60 mx-auto" />
                <p className="text-[14px] font-bold text-on-surface">No alerts in this category</p>
                <p className="text-[12px] max-w-xs mx-auto">
                  {searchQuery
                    ? 'No matching notifications found for your query.'
                    : 'Inventory stockouts, shelf-life expiry, and festival recommendations are in healthy operational standing.'}
                </p>
              </div>
            ) : (
              filteredNotifications.map((n) => {
                const isStockout = n.type === 'STOCKOUT';
                const isWastage = n.type === 'WASTAGE';
                const isFestival = n.type === 'FESTIVAL';
                const isRestocked = n.type === 'RESTOCKED' || n.is_restocked || n.severity === 'SUCCESS';
                const isBusy = actionInProgress[n.id];

                // Badge and accent styling
                let borderStyle = '';
                let iconEl = <Info className="w-4 h-4 text-primary" />;
                let iconBg = 'bg-primary/10 border-primary/20 text-primary';

                if (isStockout && !n.is_restocked) {
                  borderStyle = 'border-l-4 border-l-error bg-error/5';
                  iconEl = <AlertTriangle className="w-4 h-4 text-error" />;
                  iconBg = 'bg-error/20 border-error/30 text-error';
                } else if (isWastage && !n.is_mitigated) {
                  borderStyle = 'border-l-4 border-l-amber-500 bg-amber-500/5';
                  iconEl = <Clock className="w-4 h-4 text-amber-400" />;
                  iconBg = 'bg-amber-500/20 border-amber-500/30 text-amber-400';
                } else if (isFestival && !n.is_prestocked) {
                  borderStyle = 'border-l-4 border-l-purple-500 bg-purple-500/5';
                  iconEl = <Sparkles className="w-4 h-4 text-purple-300" />;
                  iconBg = 'bg-purple-500/20 border-purple-500/30 text-purple-300';
                } else if (isRestocked || n.is_mitigated || n.is_prestocked) {
                  borderStyle = 'border-l-4 border-l-emerald-500 bg-emerald-500/5';
                  iconEl = <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
                  iconBg = 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400';
                }

                return (
                  <div
                    key={n.id}
                    onClick={() => handleMarkRead(n.id)}
                    className={`p-3.5 transition-all duration-200 hover:bg-surface-container-high/40 relative group ${borderStyle} ${
                      !n.is_read ? 'font-semibold' : 'opacity-90'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      {/* Category Icon */}
                      <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center mt-0.5 border ${iconBg}`}>
                        {iconEl}
                      </div>

                      {/* Content Details */}
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1 flex-wrap">
                          <h4 className="font-bold text-on-surface text-[13px] leading-snug">
                            {n.title}
                          </h4>
                          <span className="text-[10px] font-mono text-on-surface-variant shrink-0">
                            {n.timestamp}
                          </span>
                        </div>

                        <p className="text-[12px] text-on-surface-variant leading-relaxed">
                          {n.message}
                        </p>

                        {/* Metadata Pills */}
                        <div className="flex items-center gap-1.5 flex-wrap pt-1 font-mono text-[11px]">
                          {n.product_id && (
                            <span className="bg-surface-container-high px-1.5 py-0.5 rounded text-on-surface-variant border border-outline-variant">
                              {n.product_id}
                            </span>
                          )}

                          {/* Stockout Specific Metadata */}
                          {isStockout && (
                            <>
                              <span className="bg-surface-container-high px-1.5 py-0.5 rounded text-on-surface-variant border border-outline-variant">
                                Stock: <strong className={!n.is_restocked ? 'text-error' : 'text-emerald-400'}>{n.current_stock?.toLocaleString()}</strong>
                                {n.predicted_demand ? ` / Demand: ${n.predicted_demand?.toLocaleString()}` : ''}
                              </span>
                              {n.warehouse && (
                                <span className="text-on-surface-variant/80 text-[10px]">
                                  @{n.warehouse}
                                </span>
                              )}
                            </>
                          )}

                          {/* Wastage Specific Metadata */}
                          {isWastage && (
                            <>
                              <span className="bg-amber-500/15 text-amber-400 border border-amber-500/30 px-1.5 py-0.5 rounded font-bold">
                                {n.days_remaining}d to expiry
                              </span>
                              {n.current_stock !== undefined && (
                                <span className="bg-surface-container-high px-1.5 py-0.5 rounded text-on-surface-variant border border-outline-variant">
                                  {n.current_stock} units at risk
                                </span>
                              )}
                              {n.discount_recommended && (
                                <span className="bg-amber-500/10 text-amber-300 border border-amber-500/20 px-1.5 py-0.5 rounded">
                                  {n.discount_recommended}
                                </span>
                              )}
                            </>
                          )}

                          {/* Festival Specific Metadata */}
                          {isFestival && (
                            <>
                              <span className="bg-purple-500/15 text-purple-300 border border-purple-500/30 px-1.5 py-0.5 rounded font-bold">
                                {n.festival_name || 'Diwali'} Window
                              </span>
                              {n.festival_multiplier && (
                                <span className="bg-purple-500/10 text-purple-300 border border-purple-500/20 px-1.5 py-0.5 rounded">
                                  {n.festival_multiplier}x Uplift (+{n.uplift_pct}%)
                                </span>
                              )}
                              {n.suggested_qty && (
                                <span className="bg-surface-container-high px-1.5 py-0.5 rounded text-on-surface-variant border border-outline-variant">
                                  Buffer: +{n.suggested_qty?.toLocaleString()} units
                                </span>
                              )}
                            </>
                          )}

                          {/* Restocked Metadata */}
                          {isRestocked && n.quantity_added && (
                            <span className="bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded font-bold">
                              +{n.quantity_added?.toLocaleString()} units replenished
                            </span>
                          )}
                        </div>

                        {/* Interactive 1-Click Action Buttons */}
                        <div className="pt-2 flex items-center gap-2">
                          {/* Stockout Restock Button */}
                          {isStockout && (
                            n.can_restock && !n.is_restocked ? (
                              <button
                                onClick={(e) => onRestockClick(n, e)}
                                disabled={isBusy}
                                className="bg-error hover:bg-error/90 active:scale-95 text-on-error font-bold px-3 py-1.5 rounded-lg text-label-sm flex items-center gap-1.5 shadow-md shadow-error/20 transition-all cursor-pointer disabled:opacity-50"
                              >
                                {isBusy ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                                <span>1-Click Restock (+{n.suggested_qty || 500} units)</span>
                              </button>
                            ) : (
                              <span className="text-emerald-400 font-bold text-[11px] font-mono flex items-center gap-1 bg-emerald-500/15 px-2 py-1 rounded-md border border-emerald-500/30">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Replenished (+{n.suggested_qty || 500} units)
                              </span>
                            )
                          )}

                          {/* Wastage Markdown Button */}
                          {isWastage && (
                            n.can_mitigate && !n.is_mitigated ? (
                              <button
                                onClick={(e) => onWastageClick(n, e)}
                                disabled={isBusy}
                                className="bg-amber-500 hover:bg-amber-600 active:scale-95 text-slate-950 font-bold px-3 py-1.5 rounded-lg text-label-sm flex items-center gap-1.5 shadow-md shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
                              >
                                {isBusy ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Clock className="w-3.5 h-3.5" />}
                                <span>1-Click Apply Markdown ({n.discount_recommended || '30% Off'})</span>
                              </button>
                            ) : (
                              <span className="text-emerald-400 font-bold text-[11px] font-mono flex items-center gap-1 bg-emerald-500/15 px-2 py-1 rounded-md border border-emerald-500/30">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Markdown Active
                              </span>
                            )
                          )}

                          {/* Festival Pre-Stock Button */}
                          {isFestival && (
                            n.can_prestock && !n.is_prestocked ? (
                              <button
                                onClick={(e) => onFestivalClick(n, e)}
                                disabled={isBusy}
                                className="bg-purple-600 hover:bg-purple-500 active:scale-95 text-white font-bold px-3 py-1.5 rounded-lg text-label-sm flex items-center gap-1.5 shadow-md shadow-purple-600/20 transition-all cursor-pointer disabled:opacity-50"
                              >
                                {isBusy ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                                <span>1-Click Pre-Stock (+{n.suggested_qty || 600} units)</span>
                              </button>
                            ) : (
                              <span className="text-emerald-400 font-bold text-[11px] font-mono flex items-center gap-1 bg-emerald-500/15 px-2 py-1 rounded-md border border-emerald-500/30">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Buffer Stocked
                              </span>
                            )
                          )}
                        </div>
                      </div>

                      {/* Right Dismiss Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDismiss(n.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-on-surface-variant hover:text-error p-1 rounded hover:bg-surface-container-high transition-all cursor-pointer shrink-0"
                        title="Dismiss notification"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer Telemetry & Phone Alerts */}
          <div className="p-xs bg-surface-container-lowest border-t border-outline-variant/40 px-4 py-2 flex items-center justify-between text-[11px] text-on-surface-variant">
            <span className="flex items-center gap-1.5 font-mono">
              <span className={`w-2 h-2 rounded-full inline-block ${isWsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
              {isWsConnected ? 'Live Real-Time Telemetry' : 'Auto-Sync Active'}
            </span>
            <div className="flex items-center gap-3">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowPhoneModal(true);
                }}
                className="flex items-center gap-1 text-primary hover:text-primary/80 font-bold font-mono transition-colors cursor-pointer"
                title="Connect notifications directly to your mobile phone"
              >
                <Smartphone className="w-3.5 h-3.5" />
                <span>Phone Alerts</span>
              </button>
              <span className="font-mono text-on-surface-variant/50">|</span>
              <span className="font-mono text-on-surface-variant font-bold">Manager Mode</span>
            </div>
          </div>
        </div>
      )}

      {/* Phone Integration Modal */}
      <PhoneIntegrationModal isOpen={showPhoneModal} onClose={() => setShowPhoneModal(false)} />
    </div>
  );
}
