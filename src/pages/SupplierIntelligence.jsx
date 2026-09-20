import React, { useState, useEffect } from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import { api } from '../api/client';
import { supplierData as fallbackSuppliers } from '../data/mockData';
import { Building2, Award, Clock, AlertTriangle } from 'lucide-react';

export default function SupplierIntelligence() {
  const [suppliers, setSuppliers] = useState(fallbackSuppliers);

  useEffect(() => {
    let isMounted = true;
    api.getSuppliers().then((res) => {
      if (isMounted && Array.isArray(res) && res.length > 0) {
        setSuppliers(res.map(s => ({
          id: s.supplier_code || s.id,
          name: s.name,
          category: s.category,
          reliabilityScore: s.reliability_score || "90%",
          onTimeDelivery: s.on_time_delivery || "90%",
          leadTimeAvg: s.lead_time_avg || "1.5 days",
          riskLevel: s.risk_level || "LOW",
          status: s.status || "VERIFIED"
        })));
      }
    });
    return () => { isMounted = false; };
  }, []);
  return (
    <div className="space-y-lg">
      <PageHeader
        title="Supplier Intelligence & Vendor Risk"
        subtitle="Monitor vendor compliance, lead times, on-time delivery rates, and quality scorecards."
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        <KPICard title="Total Active Suppliers" value="28 Vendors" status="healthy" subtitle="Across Dairy, Staples, Produce" icon={Building2} />
        <KPICard title="Avg Reliability Score" value="94.2%" delta="+1.1%" status="positive" subtitle="Target >= 90%" icon={Award} />
        <KPICard title="Avg Order Lead Time" value="1.8 Days" status="positive" subtitle="-0.4 days improvement" icon={Clock} />
        <KPICard title="Suppliers Under Review" value="1 Vendor" status="warning" subtitle="Solapur Edible Oils Ltd" icon={AlertTriangle} />
      </div>

      {/* Supplier Matrix Table */}
      <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
        <div className="p-lg border-b border-outline-variant bg-surface-container-low/50">
          <h3 className="font-title-md text-title-md font-bold text-on-surface">Supplier Performance Scorecard</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-surface-container-high/30">
              <tr>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Supplier Name & ID</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Category</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Reliability Score</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">On-Time Delivery</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Avg Lead Time</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Risk Level</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Verification Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30">
              {suppliers.map((sup) => (
                <tr key={sup.id} className="hover:bg-surface-variant/20 transition-colors">
                  <td className="px-lg py-md">
                    <div className="font-bold text-on-surface">{sup.name}</div>
                    <div className="text-[10px] text-on-surface-variant font-mono">{sup.id}</div>
                  </td>
                  <td className="px-lg py-md font-mono text-on-surface-variant">{sup.category}</td>
                  <td className="px-lg py-md font-mono font-bold text-primary">{sup.reliabilityScore}</td>
                  <td className="px-lg py-md font-mono font-bold text-on-surface">{sup.onTimeDelivery}</td>
                  <td className="px-lg py-md font-mono text-on-surface-variant">{sup.leadTimeAvg}</td>
                  <td className="px-lg py-md">
                    <StatusBadge status={sup.riskLevel} />
                  </td>
                  <td className="px-lg py-md">
                    <StatusBadge status={sup.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
