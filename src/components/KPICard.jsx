import React from 'react';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

export default function KPICard({ title, value, delta, status, subtitle, icon: Icon, borderAccent }) {
  const getStatusColor = () => {
    if (status === 'critical') return 'text-error';
    if (status === 'healthy' || status === 'positive') return 'text-primary';
    if (status === 'warning') return 'text-tertiary';
    return 'text-on-surface-variant';
  };

  const getIconBg = () => {
    if (status === 'critical') return 'bg-error/10 text-error';
    if (status === 'warning') return 'bg-tertiary/10 text-tertiary';
    return 'bg-primary/10 text-primary';
  };

  return (
    <div
      className={`glass-card rounded-xl p-lg flex flex-col justify-between group ${
        borderAccent ? `border-l-4 ${borderAccent}` : ''
      }`}
    >
      <div className="flex justify-between items-start mb-md">
        <div className={`p-xs rounded-lg ${getIconBg()}`}>
          {Icon ? <Icon className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
        </div>
        {delta && (
          <span className={`font-label-md text-label-md flex items-center gap-1 ${getStatusColor()}`}>
            {delta.includes('+') ? (
              <TrendingUp className="w-3.5 h-3.5" />
            ) : delta.includes('-') ? (
              <TrendingDown className="w-3.5 h-3.5" />
            ) : null}
            {delta}
          </span>
        )}
      </div>

      <div>
        <p className="text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider mb-base">
          {title}
        </p>
        <h3 className="text-headline-md font-headline-md text-on-surface font-bold">
          {value}
        </h3>
        {subtitle && (
          <p className="text-on-surface-variant/70 font-label-sm text-[10px] mt-xs">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
