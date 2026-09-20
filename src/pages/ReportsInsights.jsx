import React from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import { reportsList } from '../data/mockData';
import { FileText, Download, TrendingUp, DollarSign, PieChart, ShieldCheck } from 'lucide-react';

export default function ReportsInsights() {
  const handleDownload = (rep) => {
    alert(`Downloading report: ${rep.title}`);
  };

  return (
    <div className="space-y-lg">
      <PageHeader
        title="Reports & Supply Chain Insights"
        subtitle="Download executive summaries, ROI impact metrics, and operational audit reports."
      />

      {/* Financial ROI KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
        <KPICard title="Total AI Cost Savings" value="₹3.42M" delta="+22%" status="positive" subtitle="This quarter via automation" icon={DollarSign} />
        <KPICard title="Perishable Spoilage Savings" value="₹890,000" delta="+15%" status="positive" subtitle="Dynamic markdown ROI" icon={TrendingUp} />
        <KPICard title="Compliance Score" value="99.2%" status="healthy" subtitle="Regulatory & thermal audit" icon={ShieldCheck} />
      </div>

      {/* Downloadable Reports List */}
      <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
        <div className="p-lg border-b border-outline-variant bg-surface-container-low/50">
          <h3 className="font-title-md text-title-md font-bold text-on-surface">Available Operational Reports</h3>
        </div>

        <div className="divide-y divide-outline-variant/30">
          {reportsList.map((rep) => (
            <div key={rep.id} className="p-lg flex flex-col sm:flex-row sm:items-center justify-between gap-md hover:bg-surface-variant/20 transition-colors">
              <div className="flex items-center gap-md">
                <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20 shrink-0">
                  <FileText className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-body-md font-bold text-on-surface">{rep.title}</h4>
                  <p className="font-label-sm text-label-sm text-on-surface-variant">
                    Type: {rep.type} • Author: {rep.author} • Size: {rep.size}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-md">
                <span className="font-mono text-label-sm text-on-surface-variant">{rep.date}</span>
                <button
                  onClick={() => handleDownload(rep)}
                  className="px-md py-xs bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 active:scale-95 transition-all flex items-center gap-xs text-label-md"
                >
                  <Download className="w-4 h-4" />
                  <span>Download</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
