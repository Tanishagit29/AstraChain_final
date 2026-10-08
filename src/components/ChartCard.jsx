import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

export default function ChartCard({ title, subtitle, data = [], type = 'area' }) {
  const [timeframe, setTimeframe] = useState('30D');

  const filteredData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    if (timeframe === '7D') return data.slice(0, 7);
    if (timeframe === '30D') return data.slice(0, 30);
    return data;
  }, [data, timeframe]);

  const hasConfidence = filteredData.some(d => d.confidenceUpper !== undefined && d.confidenceLower !== undefined);

  return (
    <div className="glass-card rounded-xl p-lg flex flex-col h-full">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-xl gap-md">
        <div>
          <h4 className="font-title-md text-title-md text-on-surface font-bold">{title}</h4>
          {subtitle && <p className="font-label-sm text-label-sm text-on-surface-variant">{subtitle}</p>}
        </div>

        <div className="flex bg-surface-container-low p-base rounded-lg border border-outline-variant">
          {['7D', '30D', '90D'].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-sm py-xs font-label-sm text-label-sm transition-all rounded-md cursor-pointer ${
                timeframe === tf
                  ? 'bg-primary-container text-on-primary-container font-bold shadow'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="flex-1 min-h-[320px] w-full relative chart-grid border-l border-b border-outline-variant/60 rounded-bl-sm p-2">
        <ResponsiveContainer width="100%" height={320}>
          {type === 'area' ? (
            <AreaChart data={filteredData} margin={{ top: 15, right: 15, left: -15, bottom: 5 }}>
              <defs>
                <linearGradient id="cyanGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="indigoGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#BDC2FF" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#BDC2FF" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.12} />
                  <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" opacity={0.5} />
              <XAxis dataKey="day" stroke="#87929A" fontSize={11} fontFamily="JetBrains Mono" tickLine={false} />
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
              />
              {hasConfidence && (
                <Area
                  type="monotone"
                  dataKey="confidenceUpper"
                  stroke="#38BDF8"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  fillOpacity={1}
                  fill="url(#confidenceGradient)"
                  name="Upper Bound (95% CI)"
                />
              )}
              {hasConfidence && (
                <Area
                  type="monotone"
                  dataKey="confidenceLower"
                  stroke="#87929A"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  fillOpacity={0}
                  name="Lower Bound (95% CI)"
                />
              )}
              <Area type="monotone" dataKey="forecast" stroke="#38BDF8" strokeWidth={3} fillOpacity={1} fill="url(#cyanGradient)" name="XGBoost Forecast" />
              <Area type="monotone" dataKey="historical" stroke="#BDC2FF" strokeWidth={2} fillOpacity={1} fill="url(#indigoGradient)" name="Historical Demand" />
            </AreaChart>
          ) : (
            <LineChart data={filteredData} margin={{ top: 15, right: 15, left: -15, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" opacity={0.5} />
              <XAxis dataKey="day" stroke="#87929A" fontSize={11} fontFamily="JetBrains Mono" tickLine={false} />
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
              />
              {hasConfidence && (
                <Line type="monotone" dataKey="confidenceUpper" stroke="#38BDF8" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Upper Bound" />
              )}
              {hasConfidence && (
                <Line type="monotone" dataKey="confidenceLower" stroke="#87929A" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Lower Bound" />
              )}
              <Line type="monotone" dataKey="forecast" stroke="#38BDF8" strokeWidth={3} strokeDasharray="8 4" dot={{ fill: '#38BDF8', r: 4 }} name="Forecast" />
              <Line type="monotone" dataKey="historical" stroke="#BDC2FF" strokeWidth={3} dot={{ fill: '#BDC2FF', r: 4 }} name="Historical" />
            </LineChart>
          )}
        </ResponsiveContainer>

        {/* AI Confidence Indicator Pill */}
        <div className="absolute top-3 right-3 bg-primary-container/20 border border-primary text-primary px-sm py-xs rounded text-[10px] font-bold font-mono shadow-sm">
          AI CONFIDENCE: 95.5% · XGBoost Regressor
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-lg mt-lg flex-wrap items-center">
        <div className="flex items-center gap-xs">
          <div className="w-3 h-3 rounded-full bg-secondary" />
          <span className="font-label-sm text-label-sm text-on-surface-variant">Historical Actuals</span>
        </div>
        <div className="flex items-center gap-xs">
          <div className="w-3 h-3 rounded-full bg-primary" />
          <span className="font-label-sm text-label-sm text-on-surface-variant">XGBoost Forecast Curve</span>
        </div>
        <div className="flex items-center gap-xs">
          <div className="w-3 h-3 rounded-full bg-primary/20 border border-primary/40" />
          <span className="font-label-sm text-label-sm text-on-surface-variant">95% Confidence Interval Band</span>
        </div>
      </div>
    </div>
  );
}
