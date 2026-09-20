import React, { useState, useEffect } from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import { api } from '../api/client';
import { fleetRoutes as fallbackRoutes } from '../data/mockData';
import {
  Route,
  Navigation,
  Fuel,
  ShieldCheck,
  Thermometer,
  Plus,
  X,
  Sparkles,
  ArrowRight,
  MapPin,
  Clock,
  TrendingDown,
} from 'lucide-react';

const FALLBACK_LOCATIONS = [
  'Mumbai Central Port', 'Pune Logistics Hub', 'Pune North Hub', 'Nashik Warehouse',
  'Thane Cold Storage', 'Solapur Distribution', 'Surat Port Depot', 'Nagpur Park',
  'Mumbai Andheri Store', 'Mumbai Bandra Outlet', 'Navi Mumbai Vashi Hub',
  'Pune Kothrud Store', 'Pune Viman Nagar Outlet', 'Thane Ghodbunder Store',
  'Kolhapur Distribution', 'Aurangabad Depot', 'Satara Warehouse',
];

function MultiStopRouteOptimizer() {
  const [locations, setLocations] = useState(FALLBACK_LOCATIONS);
  const [truckId, setTruckId] = useState('MH-04-JK-4821');
  const [origin, setOrigin] = useState('Mumbai Central Port');
  const [selectedStops, setSelectedStops] = useState(['Pune Logistics Hub', 'Nashik Warehouse']);
  const [stopToAdd, setStopToAdd] = useState('');
  const [returnToOrigin, setReturnToOrigin] = useState(true);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;
    api.getKnownLocations().then((res) => {
      if (isMounted && Array.isArray(res) && res.length > 0) {
        setLocations(res);
      }
    });
    return () => { isMounted = false; };
  }, []);

  const availableToAdd = locations.filter((loc) => loc !== origin && !selectedStops.includes(loc));

  const addStop = () => {
    const next = stopToAdd || availableToAdd[0];
    if (next && !selectedStops.includes(next)) {
      setSelectedStops([...selectedStops, next]);
      setStopToAdd('');
    }
  };

  const removeStop = (loc) => {
    setSelectedStops(selectedStops.filter((s) => s !== loc));
  };

  const runOptimization = async () => {
    if (selectedStops.length < 2) {
      setError('Add at least 2 delivery stops to run the optimizer.');
      return;
    }
    setError('');
    setLoading(true);
    setResult(null);

    const res = await api.optimizeMultiStopRoute({
      truckId,
      origin,
      stops: selectedStops,
      returnToOrigin,
    });

    setLoading(false);
    if (!res) {
      setError('Route optimization failed. Please check your stops and try again.');
      return;
    }
    setResult(res);
  };

  return (
    <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
      <div className="p-lg border-b border-outline-variant bg-surface-container-low/50 flex justify-between items-center flex-wrap gap-sm">
        <div className="flex items-center gap-sm">
          <Sparkles className="w-5 h-5 text-primary" />
          <h3 className="font-title-md text-title-md font-bold text-on-surface">Multi-Stop Route Optimizer</h3>
        </div>
        <span className="font-label-sm text-label-sm text-primary font-mono">NEAREST NEIGHBOR + 2-OPT</span>
      </div>

      <div className="p-lg grid grid-cols-1 lg:grid-cols-3 gap-lg">
        {/* Configuration Panel */}
        <div className="lg:col-span-1 space-y-md">
          <div>
            <label className="font-label-sm text-label-sm text-on-surface-variant uppercase block mb-xs">Truck ID</label>
            <input
              value={truckId}
              onChange={(e) => setTruckId(e.target.value)}
              className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-sm text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary"
            />
          </div>

          <div>
            <label className="font-label-sm text-label-sm text-on-surface-variant uppercase block mb-xs">Origin / Depot</label>
            <select
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-sm text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary"
            >
              {locations.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="font-label-sm text-label-sm text-on-surface-variant uppercase block mb-xs">Delivery Stops</label>
            <div className="flex gap-xs mb-sm">
              <select
                value={stopToAdd}
                onChange={(e) => setStopToAdd(e.target.value)}
                className="flex-1 bg-surface-container-low border border-outline-variant rounded-lg px-sm py-xs text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary"
              >
                <option value="">Select a stop…</option>
                {availableToAdd.map((loc) => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
              <button
                onClick={addStop}
                disabled={availableToAdd.length === 0}
                className="bg-primary text-on-primary font-bold rounded-lg px-sm py-xs hover:opacity-90 active:scale-95 transition-all disabled:opacity-40"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-xs">
              {selectedStops.map((loc, idx) => (
                <div key={loc} className="flex items-center justify-between bg-surface-container-low border border-outline-variant rounded-lg px-sm py-xs">
                  <span className="font-mono text-label-sm text-on-surface flex items-center gap-xs">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-bold flex items-center justify-center">{idx + 1}</span>
                    {loc}
                  </span>
                  <button onClick={() => removeStop(loc)} className="text-on-surface-variant hover:text-error transition-colors">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {selectedStops.length === 0 && (
                <p className="text-label-sm text-on-surface-variant/60 italic">No stops added yet.</p>
              )}
            </div>
          </div>

          <label className="flex items-center gap-xs text-label-sm text-on-surface-variant">
            <input
              type="checkbox"
              checked={returnToOrigin}
              onChange={(e) => setReturnToOrigin(e.target.checked)}
              className="accent-primary"
            />
            Return to origin after final stop
          </label>

          {error && <p className="text-error text-label-sm">{error}</p>}

          <button
            onClick={runOptimization}
            disabled={loading}
            className="w-full bg-primary text-on-primary font-bold rounded-lg px-md py-md text-label-md hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-xs disabled:opacity-60"
          >
            <Sparkles className="w-4 h-4" />
            {loading ? 'Optimizing Route…' : 'Optimize Route'}
          </button>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2">
          {!result && (
            <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-center border border-dashed border-outline-variant rounded-xl p-lg">
              <Route className="w-10 h-10 text-on-surface-variant/40 mb-sm" />
              <p className="text-body-md text-on-surface-variant max-w-sm">
                Configure a truck, origin, and delivery stops, then run the optimizer to compute
                the shortest visiting sequence using a Nearest-Neighbor + 2-Opt heuristic.
              </p>
            </div>
          )}

          {result && (
            <div className="space-y-md">
              {/* Savings KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-sm">
                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Total Distance</p>
                  <p className="font-mono font-bold text-on-surface text-title-md">{result.total_distance_km} km</p>
                </div>
                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Distance Saved</p>
                  <p className="font-mono font-bold text-primary text-title-md flex items-center gap-1">
                    <TrendingDown className="w-4 h-4" /> {result.distance_saved_km} km
                  </p>
                </div>
                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Fuel Saved</p>
                  <p className="font-mono font-bold text-primary text-title-md">₹{result.fuel_saved_inr.toLocaleString()}</p>
                </div>
                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Savings</p>
                  <p className="font-mono font-bold text-primary text-title-md">{result.savings_pct}%</p>
                </div>
              </div>

              {/* Optimized Sequence Visualization */}
              <div className="glass-card rounded-lg p-md">
                <p className="font-label-sm text-label-sm text-on-surface-variant uppercase mb-sm">Optimized Visiting Order</p>
                <div className="flex flex-wrap items-center gap-xs">
                  {result.optimized_sequence.map((loc, idx) => (
                    <React.Fragment key={`${loc}-${idx}`}>
                      <div className="flex items-center gap-xs bg-surface-container-high/40 border border-outline-variant rounded-full px-sm py-xs">
                        <span className="w-5 h-5 rounded-full bg-primary text-on-primary text-[10px] font-bold flex items-center justify-center">{idx + 1}</span>
                        <MapPin className="w-3.5 h-3.5 text-primary" />
                        <span className="font-mono text-label-sm text-on-surface">{loc}</span>
                      </div>
                      {idx < result.optimized_sequence.length - 1 && (
                        <ArrowRight className="w-4 h-4 text-on-surface-variant/50 shrink-0" />
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* Leg-by-leg breakdown */}
              <div className="glass-card rounded-lg overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-surface-container-high/30">
                    <tr>
                      <th className="px-md py-xs text-label-sm text-on-surface-variant uppercase font-mono">Leg</th>
                      <th className="px-md py-xs text-label-sm text-on-surface-variant uppercase font-mono">Distance</th>
                      <th className="px-md py-xs text-label-sm text-on-surface-variant uppercase font-mono">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/30">
                    {result.legs.map((leg, idx) => (
                      <tr key={idx}>
                        <td className="px-md py-xs text-body-md text-on-surface-variant font-mono">
                          {leg.from_location} → <span className="text-on-surface font-bold">{leg.to_location}</span>
                        </td>
                        <td className="px-md py-xs font-mono text-on-surface">{leg.distance_km} km</td>
                        <td className="px-md py-xs font-mono text-on-surface flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-primary" /> {leg.duration_minutes} min
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="text-[10px] text-on-surface-variant/60 font-mono">
                Algorithm: {result.algorithm} · Naive order distance: {result.naive_distance_km} km · Total transit time: {result.total_duration_minutes} min
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RouteOptimization() {
  const [routes, setRoutes] = useState(fallbackRoutes);

  useEffect(() => {
    let isMounted = true;
    api.getRoutes().then((res) => {
      if (isMounted && Array.isArray(res) && res.length > 0) {
        setRoutes(res.map(r => ({
          id: r.route_code || r.id,
          truckId: r.truck_id,
          driver: r.driver,
          origin: r.origin,
          destination: r.destination,
          status: r.status,
          eta: r.eta,
          temp: r.temp,
          fuelSaved: r.fuel_saved,
          risk: r.risk
        })));
      }
    });
    return () => { isMounted = false; };
  }, []);
  return (
    <div className="space-y-lg">
      <PageHeader
        title="Route Optimization & Fleet Telemetry"
        subtitle="Real-time transit tracking, AI dynamic rerouting, and fuel economy."
      />

      {/* Fleet KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        <KPICard title="Active Fleet Trucks" value="42" status="healthy" subtitle="98% telemetry active" icon={Navigation} />
        <KPICard title="Route Efficiency" value="91.8%" delta="+3.4%" status="positive" subtitle="Optimal transit rate" icon={Route} />
        <KPICard title="Fuel Costs Saved" value="₹1.48M" delta="+18%" status="positive" subtitle="This month via dynamic reroutes" icon={Fuel} />
        <KPICard title="Avg Transit Delay" value="8.5 min" status="healthy" subtitle="NH-48 detour mitigation" icon={ShieldCheck} />
      </div>

      {/* Multi-Stop Route Optimizer (Vehicle Routing / TSP-style) */}
      <MultiStopRouteOptimizer />

      {/* Active Fleet Transit Table */}
      <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
        <div className="p-lg border-b border-outline-variant bg-surface-container-low/50 flex justify-between items-center">
          <h3 className="font-title-md text-title-md font-bold text-on-surface">Active Fleet Shipments & Telemetry</h3>
          <span className="font-label-sm text-label-sm text-primary font-mono">LIVE TELEMETRY STREAM</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-surface-container-high/30">
              <tr>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Route ID & Vehicle</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Driver Name</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Origin → Destination</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Estimated ETA</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Cold Chain Temp</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Fuel Saved</th>
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30">
              {routes.map((route) => (
                <tr key={route.id} className="hover:bg-surface-variant/20 transition-colors">
                  <td className="px-lg py-md">
                    <div className="font-bold text-on-surface">{route.id}</div>
                    <div className="text-[10px] text-on-surface-variant font-mono">{route.truckId}</div>
                  </td>
                  <td className="px-lg py-md text-body-md text-on-surface">{route.driver}</td>
                  <td className="px-lg py-md text-body-md font-mono text-on-surface-variant">
                    {route.origin} → <span className="text-on-surface font-bold">{route.destination}</span>
                  </td>
                  <td className="px-lg py-md text-body-md font-mono font-bold text-primary">{route.eta}</td>
                  <td className="px-lg py-md">
                    <span className="flex items-center gap-1 font-mono text-label-md text-on-surface">
                      <Thermometer className="w-4 h-4 text-primary" />
                      {route.temp}
                    </span>
                  </td>
                  <td className="px-lg py-md font-mono text-primary font-bold">{route.fuelSaved}</td>
                  <td className="px-lg py-md">
                    <StatusBadge status={route.status} />
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
