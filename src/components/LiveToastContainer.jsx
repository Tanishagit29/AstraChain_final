import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, CheckCircle2, Zap, Clock, Sparkles, X, ChevronRight, RotateCw, Volume2, VolumeX
} from 'lucide-react';
import { useLiveNotifications } from '../context/NotificationContext';

function ToastCard({ toast, onDismiss, onRestock, onMitigateWastage, onPrestockFestival }) {
  const [actionLoading, setActionLoading] = useState(false);
  const [progress, setProgress] = useState(100);

  const duration = toast.duration || 7000;

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);
      if (remaining <= 0) {
        clearInterval(interval);
        onDismiss(toast.id);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [duration, onDismiss, toast.id]);

  const isStockout = toast.type === 'STOCKOUT';
  const isWastage = toast.type === 'WASTAGE';
  const isFestival = toast.type === 'FESTIVAL';
  const isRestocked = toast.type === 'RESTOCKED' || toast.severity === 'SUCCESS' || toast.is_restocked;

  const handleAction = async (e) => {
    e.stopPropagation();
    setActionLoading(true);
    try {
      if (isStockout && toast.can_restock && !toast.is_restocked) {
        await onRestock(toast);
      } else if (isWastage && toast.can_mitigate && !toast.is_mitigated) {
        await onMitigateWastage(toast);
      } else if (isFestival && toast.can_prestock && !toast.is_prestocked) {
        await onPrestockFestival(toast);
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Color schemes & icons
  let theme = {
    border: 'border-primary/40',
    bg: 'bg-surface/95',
    badgeBg: 'bg-primary/15 text-primary border-primary/30',
    iconBg: 'bg-primary/20 text-primary',
    progress: 'bg-primary',
    icon: <Zap className="w-5 h-5" />,
    badgeText: 'Operational Alert',
  };

  if (isStockout && !toast.is_restocked) {
    theme = {
      border: 'border-error/50 shadow-error/10',
      bg: 'bg-surface/95',
      badgeBg: 'bg-error/15 text-error border-error/30',
      iconBg: 'bg-error/20 text-error',
      progress: 'bg-error',
      icon: <AlertTriangle className="w-5 h-5 animate-bounce" />,
      badgeText: 'Live Stockout Risk',
    };
  } else if (isWastage && !toast.is_mitigated) {
    theme = {
      border: 'border-amber-500/50 shadow-amber-500/10',
      bg: 'bg-surface/95',
      badgeBg: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
      iconBg: 'bg-amber-500/20 text-amber-400',
      progress: 'bg-amber-500',
      icon: <Clock className="w-5 h-5" />,
      badgeText: toast.timestamp || 'Near-Expiry Wastage Alert',
    };
  } else if (isFestival && !toast.is_prestocked) {
    theme = {
      border: 'border-purple-500/50 shadow-purple-500/10',
      bg: 'bg-surface/95',
      badgeBg: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
      iconBg: 'bg-purple-500/20 text-purple-300',
      progress: 'bg-purple-500',
      icon: <Sparkles className="w-5 h-5" />,
      badgeText: `${toast.festival_name || 'Festive'} Demand Surge`,
    };
  } else if (isRestocked || toast.is_mitigated || toast.is_prestocked) {
    theme = {
      border: 'border-emerald-500/50 shadow-emerald-500/10',
      bg: 'bg-surface/95',
      badgeBg: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
      iconBg: 'bg-emerald-500/20 text-emerald-400',
      progress: 'bg-emerald-500',
      icon: <CheckCircle2 className="w-5 h-5" />,
      badgeText: toast.badge || 'Action Executed',
    };
  }

  return (
    <div
      className={`pointer-events-auto w-full backdrop-blur-2xl border ${theme.border} ${theme.bg} rounded-2xl p-4 shadow-2xl relative overflow-hidden transition-all duration-300 animate-slide-in hover:shadow-primary/20 group`}
    >
      {/* Top Header & Badge */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${theme.iconBg}`}>
            {theme.icon}
          </div>
          <div>
            <span className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${theme.badgeBg}`}>
              {theme.badgeText}
            </span>
          </div>
        </div>

        <button
          onClick={() => onDismiss(toast.id)}
          className="text-on-surface-variant/60 hover:text-on-surface p-1 rounded-lg hover:bg-surface-container-high transition-colors cursor-pointer"
          title="Dismiss alert"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Title & Message */}
      <div className="space-y-1 mb-3">
        <h4 className="text-[13px] font-bold text-on-surface leading-tight">
          {toast.title}
        </h4>
        <p className="text-[12px] text-on-surface-variant leading-relaxed line-clamp-3">
          {toast.message}
        </p>
      </div>

      {/* Context Data Tags */}
      <div className="flex items-center gap-1.5 flex-wrap font-mono text-[11px] mb-3">
        {toast.product_id && (
          <span className="bg-surface-container-high px-2 py-0.5 rounded-md text-on-surface-variant border border-outline-variant/60">
            {toast.product_id}
          </span>
        )}
        {toast.current_stock !== undefined && (
          <span className="bg-surface-container-high px-2 py-0.5 rounded-md text-on-surface-variant border border-outline-variant/60">
            Stock: <strong className={isStockout && !toast.is_restocked ? 'text-error' : 'text-primary'}>{toast.current_stock}</strong>
            {toast.predicted_demand ? ` / Demand: ${toast.predicted_demand}` : ''}
          </span>
        )}
        {toast.days_remaining !== undefined && (
          <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-md">
            {toast.days_remaining}d to expiry
          </span>
        )}
        {toast.festival_multiplier && (
          <span className="bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 rounded-md">
            {toast.festival_multiplier}x Surge (+{toast.uplift_pct}%)
          </span>
        )}
      </div>

      {/* 1-Click Interactive Action Button */}
      {isStockout && toast.can_restock && !toast.is_restocked && (
        <button
          onClick={handleAction}
          disabled={actionLoading}
          className="w-full bg-error hover:bg-error/90 active:scale-[0.98] text-on-error font-bold py-2 px-3 rounded-xl text-label-sm flex items-center justify-center gap-1.5 shadow-lg shadow-error/25 transition-all cursor-pointer disabled:opacity-60"
        >
          {actionLoading ? <RotateCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
          <span>1-Click Restock (+{toast.suggested_qty || 500} units)</span>
        </button>
      )}

      {isWastage && toast.can_mitigate && !toast.is_mitigated && (
        <button
          onClick={handleAction}
          disabled={actionLoading}
          className="w-full bg-amber-500 hover:bg-amber-600 active:scale-[0.98] text-slate-950 font-bold py-2 px-3 rounded-xl text-label-sm flex items-center justify-center gap-1.5 shadow-lg shadow-amber-500/25 transition-all cursor-pointer disabled:opacity-60"
        >
          {actionLoading ? <RotateCw className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
          <span>1-Click Dynamic Markdown ({toast.discount_recommended || '30% Off'})</span>
        </button>
      )}

      {isFestival && toast.can_prestock && !toast.is_prestocked && (
        <button
          onClick={handleAction}
          disabled={actionLoading}
          className="w-full bg-purple-600 hover:bg-purple-500 active:scale-[0.98] text-white font-bold py-2 px-3 rounded-xl text-label-sm flex items-center justify-center gap-1.5 shadow-lg shadow-purple-600/25 transition-all cursor-pointer disabled:opacity-60"
        >
          {actionLoading ? <RotateCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          <span>1-Click Pre-Stock Buffer (+{toast.suggested_qty || 600} units)</span>
        </button>
      )}

      {(toast.is_restocked || toast.is_mitigated || toast.is_prestocked) && (
        <div className="bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 py-1.5 px-3 rounded-xl text-label-sm font-bold flex items-center justify-center gap-1.5">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toast.badge || 'Action Successfully Executed'}</span>
        </div>
      )}

      {/* Progress countdown line */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-surface-container-high/50">
        <div
          className={`h-full ${theme.progress} transition-all duration-75`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export default function LiveToastContainer() {
  const {
    liveToasts,
    dismissToast,
    handleRestock,
    handleMitigateWastage,
    handlePrestockFestival,
  } = useLiveNotifications();

  if (!liveToasts || liveToasts.length === 0) return null;

  // Strictly display only 1 block at a time
  const currentToast = liveToasts[0];

  return (
    <div
      aria-live="polite"
      className="fixed top-20 right-5 z-[9999] w-80 sm:w-96 max-w-[calc(100vw-2.5rem)] pointer-events-none"
    >
      <ToastCard
        key={currentToast.id}
        toast={currentToast}
        onDismiss={dismissToast}
        onRestock={handleRestock}
        onMitigateWastage={handleMitigateWastage}
        onPrestockFestival={handlePrestockFestival}
      />
    </div>
  );
}

