import React, { useState, useEffect } from 'react';
import PageHeader from '../components/PageHeader';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import LiveRouteMap, { FLEET_VEHICLES } from '../components/LiveRouteMap';
import { api } from '../api/client';
import { solveTwoOpt } from '../utils/routeCalculator';
import { fleetRoutes as fallbackRoutes } from '../data/mockData';
import {
  Route,
  Navigation,
  Fuel,
  ShieldCheck,
  Thermometer,
  Truck,
  Plus,
  X,
  Sparkles,
  ArrowRight,
  MapPin,
  Clock,
  TrendingDown,
  AlertTriangle,
  Leaf,
  Radio,
  Gauge,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Send,
} from 'lucide-react';

const FALLBACK_LOCATIONS = [
  'Mumbai Central Port', 'Pune Logistics Hub', 'Pune North Hub', 'Nashik Warehouse',
  'Thane Cold Storage', 'Solapur Distribution', 'Surat Port Depot', 'Nagpur Park',
  'Mumbai Andheri Store', 'Mumbai Bandra Outlet', 'Navi Mumbai Vashi Hub',
  'Pune Kothrud Store', 'Pune Viman Nagar Outlet', 'Thane Ghodbunder Store',
  'Kolhapur Distribution', 'Aurangabad Depot', 'Satara Warehouse',
];

const CORRIDOR_TRAFFIC_DATA = [
  {
    corridor: 'NH-48 Mumbai-Pune Expressway',
    condition: 'MODERATE_SLOWDOWN',
    statusText: 'Bottleneck near Vashi Toll (+8 min) · 35 km/h Ghat curve restriction',
    speed: '42 km/h avg',
    mitigation: 'AI Eastern Freeway / MTHL Bypass active',
    severity: 'warning',
  },
  {
    corridor: 'NH-60 Nashik-Pune Freight Link',
    condition: 'OPTIMAL_FLOW',
    statusText: 'Free-flow transit across Kasara Ghat; Chakan auto corridor clear',
    speed: '68 km/h avg',
    mitigation: 'Standard 2-Opt corridor recommended',
    severity: 'success',
  },
  {
    corridor: 'Thane Ghodbunder Container Corridor',
    condition: 'HEAVY_CONGESTION',
    statusText: 'Metro pier construction reducing flow to 2 lanes (+14 min delay)',
    speed: '16 km/h avg',
    mitigation: 'Dynamic diversion via Airoli-Kalyan link engaged',
    severity: 'danger',
  },
];

function MultiStopRouteOptimizer({
  activeTruck,
  setActiveTruck,
}) {
  const [locations, setLocations] = useState(FALLBACK_LOCATIONS);
  const [truckId, setTruckId] = useState(activeTruck?.truckId || 'MH-04-JK-4821');
  const [origin, setOrigin] = useState(activeTruck?.origin || 'Mumbai Central Port');
  const [selectedStops, setSelectedStops] = useState(activeTruck?.stops || ['Pune Logistics Hub', 'Nashik Warehouse']);
  const [stopToAdd, setStopToAdd] = useState('');
  const [returnToOrigin, setReturnToOrigin] = useState(true);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runOptimization = async (overrideStops = null, overrideOrigin = null, overrideTruckId = null) => {
    const stopsToUse = overrideStops || selectedStops;
    const originToUse = overrideOrigin || origin;
    const truckToUse = overrideTruckId || truckId;

    if (stopsToUse.length < 2) {
      setError('Add at least 2 delivery stops to run the optimizer.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const res = await api.optimizeMultiStopRoute({
        truckId: truckToUse,
        origin: originToUse,
        stops: stopsToUse,
        returnToOrigin,
      });

      if (res && res.optimized_sequence) {
        setResult(res);
      } else {
        const clientRes = solveTwoOpt(originToUse, stopsToUse, returnToOrigin);
        clientRes.truck_id = truckToUse;
        setResult(clientRes);
      }
    } catch {
      const clientRes = solveTwoOpt(originToUse, stopsToUse, returnToOrigin);
      clientRes.truck_id = truckToUse;
      setResult(clientRes);
    } finally {
      setLoading(false);
    }
  };

  // Run initial optimization on mount
  useEffect(() => {
    runOptimization(selectedStops, origin, truckId);
  }, []);

  // Sync and immediately re-optimize when activeTruck changes
  useEffect(() => {
    if (activeTruck) {
      setTruckId(activeTruck.truckId);
      const newOrigin = activeTruck.origin || origin;
      const newStops = activeTruck.stops && activeTruck.stops.length > 0 ? activeTruck.stops : selectedStops;
      setOrigin(newOrigin);
      setSelectedStops(newStops);
      runOptimization(newStops, newOrigin, activeTruck.truckId);
    }
  }, [activeTruck]);

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
      const updated = [...selectedStops, next];
      setSelectedStops(updated);
      setStopToAdd('');
      runOptimization(updated, origin, truckId);
    }
  };

  const removeStop = (loc) => {
    const updated = selectedStops.filter((s) => s !== loc);
    setSelectedStops(updated);
    if (updated.length >= 2) {
      runOptimization(updated, origin, truckId);
    }
  };

  const handleSelectTruckFromMap = (vehicle) => {
    setActiveTruck(vehicle);
    setTruckId(vehicle.truckId);
    setOrigin(vehicle.origin);
    setSelectedStops(vehicle.stops);
    runOptimization(vehicle.stops, vehicle.origin, vehicle.truckId);
  };

  return (
    <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
      <div className="p-lg border-b border-outline-variant bg-surface-container-low/50 flex justify-between items-center flex-wrap gap-sm">
        <div className="flex items-center gap-sm">
          <Sparkles className="w-5 h-5 text-primary" />
          <h3 className="font-title-md text-title-md font-bold text-on-surface">Multi-Stop Route Optimizer & Real-Time Telemetry</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-label-sm text-label-sm text-primary font-mono px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20">
            NEAREST NEIGHBOR + 2-OPT HEURISTIC
          </span>
          <span className="font-label-sm text-label-sm text-emerald-400 font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live Traffic Aware
          </span>
        </div>
      </div>

      <div className="p-lg grid grid-cols-1 lg:grid-cols-3 gap-lg">
        {/* Configuration Panel */}
        <div className="lg:col-span-1 space-y-md">
          <div>
            <label className="font-label-sm text-label-sm text-on-surface-variant uppercase block mb-xs">Truck ID & Assigned Fleet</label>
            <div className="flex gap-xs">
              <input
                value={truckId}
                onChange={(e) => setTruckId(e.target.value)}
                className="flex-1 bg-surface-container-low border border-outline-variant rounded-lg px-md py-sm text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary font-mono"
              />
              <select
                onChange={(e) => {
                  const found = FLEET_VEHICLES.find((v) => v.truckId === e.target.value);
                  if (found) handleSelectTruckFromMap(found);
                }}
                value={truckId}
                className="bg-surface-container-low border border-outline-variant rounded-lg px-xs py-sm text-body-sm text-on-surface-variant font-mono"
              >
                {FLEET_VEHICLES.map((v) => (
                  <option key={v.truckId} value={v.truckId}>{v.truckId}</option>
                ))}
              </select>
            </div>
            {activeTruck && (
              <p className="text-[10px] font-mono text-on-surface-variant mt-1">
                Driver: <strong className="text-on-surface">{activeTruck.driver}</strong> · {activeTruck.cargo}
              </p>
            )}
          </div>

          <div>
            <label className="font-label-sm text-label-sm text-on-surface-variant uppercase block mb-xs">Origin / Central Depot</label>
            <select
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-md py-sm text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary font-mono"
            >
              {locations.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="font-label-sm text-label-sm text-on-surface-variant uppercase block mb-xs">
              Delivery Stops ({selectedStops.length})
            </label>
            <div className="flex gap-xs mb-sm">
              <select
                value={stopToAdd}
                onChange={(e) => setStopToAdd(e.target.value)}
                className="flex-1 bg-surface-container-low border border-outline-variant rounded-lg px-sm py-xs text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary font-mono text-body-sm"
              >
                <option value="">Select a stop to add…</option>
                {availableToAdd.map((loc) => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
              <button
                onClick={addStop}
                disabled={availableToAdd.length === 0}
                className="bg-primary text-on-primary font-bold rounded-lg px-sm py-xs hover:opacity-90 active:scale-95 transition-all disabled:opacity-40 cursor-pointer"
                title="Add Delivery Stop"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-xs max-h-48 overflow-y-auto pr-1 scrollbar-thin">
              {selectedStops.map((loc, idx) => (
                <div key={loc} className="flex items-center justify-between bg-surface-container-low border border-outline-variant rounded-lg px-sm py-xs">
                  <span className="font-mono text-label-sm text-on-surface flex items-center gap-xs">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <span className="truncate max-w-[190px]">{loc}</span>
                  </span>
                  <button
                    onClick={() => removeStop(loc)}
                    className="text-on-surface-variant hover:text-error transition-colors cursor-pointer"
                    title="Remove Stop"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {selectedStops.length === 0 && (
                <p className="text-label-sm text-on-surface-variant/60 italic">No stops added yet.</p>
              )}
            </div>
          </div>

          <label className="flex items-center gap-xs text-label-sm text-on-surface-variant cursor-pointer select-none">
            <input
              type="checkbox"
              checked={returnToOrigin}
              onChange={(e) => {
                const checked = e.target.checked;
                setReturnToOrigin(checked);
                runOptimization(selectedStops, origin, truckId);
              }}
              className="accent-primary"
            />
            <span>Return to origin depot after final delivery drop</span>
          </label>

          {error && <p className="text-error text-label-sm font-mono">{error}</p>}

          <button
            onClick={() => runOptimization()}
            disabled={loading}
            className="w-full bg-primary text-on-primary font-bold rounded-lg px-md py-md text-label-md hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-xs disabled:opacity-60 cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            {loading ? 'Optimizing Route Sequence…' : 'Optimize Route & Compute Fuel'}
          </button>
        </div>

        {/* Results & Live Google Maps Telemetry Panel */}
        <div className="lg:col-span-2 space-y-md">
          {/* Live Google Map Visualization with Real-Time Truck Telemetry */}
          <LiveRouteMap
            origin={origin}
            stops={selectedStops}
            optimizedSequence={result?.optimized_sequence}
            naiveSequence={result?.naive_sequence}
            truckId={truckId}
            distanceSavedKm={result?.distance_saved_km || 0}
            savingsPct={result?.savings_pct || 0}
            returnToOrigin={returnToOrigin}
            onSelectTruck={handleSelectTruckFromMap}
          />

          {!result && (
            <div className="flex items-center justify-between p-md bg-surface-container-low/70 border border-outline-variant/60 rounded-xl text-on-surface-variant text-[12px] font-mono flex-wrap gap-2">
              <span className="flex items-center gap-2">
                <Route className="w-4 h-4 text-primary" />
                <span>Selected <strong>{selectedStops.length}</strong> delivery stops from <strong>{origin}</strong>.</span>
              </span>
              <span className="text-primary font-bold">Ready to Optimize Route</span>
            </div>
          )}

          {result && (
            <div className="space-y-md animate-fade-in">
              {/* Savings KPIs & Economics Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-sm">
                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Optimized Distance</p>
                  <p className="font-mono font-bold text-on-surface text-title-md">{result.total_distance_km} km</p>
                  <p className="text-[10px] text-on-surface-variant/70 font-mono mt-0.5">Naive: {result.naive_distance_km} km</p>
                </div>

                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Distance Saved</p>
                  <p className="font-mono font-bold text-emerald-400 text-title-md flex items-center gap-1">
                    <TrendingDown className="w-4 h-4" /> {result.distance_saved_km} km
                  </p>
                  <p className="text-[10px] text-emerald-400/80 font-mono mt-0.5">-{result.savings_pct}% mileage cut</p>
                </div>

                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Fuel Saved (L & ₹)</p>
                  <p className="font-mono font-bold text-primary text-title-md">
                    {result.fuel_saved_liters ? `${result.fuel_saved_liters} L` : `₹${result.fuel_saved_inr.toLocaleString()}`}
                  </p>
                  <p className="text-[10px] text-primary font-mono mt-0.5">
                    ₹{result.fuel_saved_inr.toLocaleString()} savings
                  </p>
                </div>

                <div className="glass-card rounded-lg p-sm">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">CO₂ Abated (ESG)</p>
                  <p className="font-mono font-bold text-emerald-400 text-title-md flex items-center gap-1">
                    <Leaf className="w-4 h-4 text-emerald-400" />
                    {result.co2_abated_kg ? `${result.co2_abated_kg} kg` : `${(result.distance_saved_km * 0.52).toFixed(1)} kg`}
                  </p>
                  <p className="text-[10px] text-emerald-400 font-mono mt-0.5">Clean Fleet standard</p>
                </div>
              </div>

              {/* Optimized Sequence Visualization */}
              <div className="glass-card rounded-lg p-md">
                <div className="flex items-center justify-between mb-sm flex-wrap gap-2">
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">AI 2-Opt Optimized Visiting Sequence</p>
                  <span className="text-[11px] font-mono text-primary font-bold">
                    Transit Duration: ~{result.total_duration_minutes} min ({Math.round(result.total_duration_minutes / 60)}h {result.total_duration_minutes % 60}m)
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-xs">
                  {result.optimized_sequence.map((loc, idx) => (
                    <React.Fragment key={`${loc}-${idx}`}>
                      <div className="flex items-center gap-xs bg-surface-container-high/60 border border-outline-variant rounded-full px-sm py-xs">
                        <span className="w-5 h-5 rounded-full bg-primary text-on-primary text-[10px] font-bold flex items-center justify-center">
                          {idx === 0 ? 'A' : idx === result.optimized_sequence.length - 1 && returnToOrigin ? '✓' : idx}
                        </span>
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
                  <thead className="bg-surface-container-high/40">
                    <tr>
                      <th className="px-md py-xs text-label-sm text-on-surface-variant uppercase font-mono">Transit Leg</th>
                      <th className="px-md py-xs text-label-sm text-on-surface-variant uppercase font-mono">Corridor Distance</th>
                      <th className="px-md py-xs text-label-sm text-on-surface-variant uppercase font-mono">Duration</th>
                      <th className="px-md py-xs text-label-sm text-on-surface-variant uppercase font-mono">Traffic Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/30">
                    {result.legs.map((leg, idx) => (
                      <tr key={idx} className="hover:bg-surface-variant/20 transition-colors">
                        <td className="px-md py-xs text-body-md text-on-surface-variant font-mono">
                          {leg.from_location} → <span className="text-on-surface font-bold">{leg.to_location}</span>
                        </td>
                        <td className="px-md py-xs font-mono text-on-surface">{leg.distance_km} km</td>
                        <td className="px-md py-xs font-mono text-on-surface flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-primary" /> {leg.duration_minutes} min
                        </td>
                        <td className="px-md py-xs font-mono text-[11px]">
                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Optimal (65 km/h)
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="p-sm bg-surface-container-low rounded-xl border border-outline-variant/40 flex items-center justify-between text-[11px] font-mono text-on-surface-variant flex-wrap gap-2">
                <span>
                  Algorithm: <strong>{result.algorithm}</strong> · Unoptimized baseline distance: <strong>{result.naive_distance_km} km</strong>
                </span>
                <span className="text-primary font-bold">
                  Total Fuel Savings: ₹{result.fuel_saved_inr.toLocaleString()} (approx {result.fuel_saved_liters || (result.distance_saved_km / 5.2).toFixed(1)} L)
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RouteOptimization() {
  const [routes, setRoutes] = useState(fallbackRoutes);
  const [activeTruck, setActiveTruck] = useState(FLEET_VEHICLES[0]);
  const [rerouteStatus, setRerouteStatus] = useState(null);

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

  const handleSelectRouteRow = (route) => {
    const matched = FLEET_VEHICLES.find((v) => v.truckId === route.truckId);
    if (matched) {
      setActiveTruck(matched);
    } else {
      setActiveTruck({
        truckId: route.truckId,
        driver: route.driver,
        vehicleType: 'Fleet Transit Reefer',
        cargo: 'Cold Storage Deliveries',
        origin: route.origin,
        stops: [route.destination, 'Thane Cold Storage'],
        temp: route.temp,
        fuelLevel: 75,
        speed: 64,
        fuelSavedLiters: 16.5,
        fuelSavedInr: 1650,
        co2AbatedKg: 44.2,
      });
    }
    window.scrollTo({ top: 320, behavior: 'smooth' });
  };

  const handleAutoRerouteAll = () => {
    setRerouteStatus('optimizing');
    setTimeout(() => {
      setRerouteStatus('done');
      setTimeout(() => setRerouteStatus(null), 4000);
    }, 1200);
  };

  return (
    <div className="space-y-lg">
      <PageHeader
        title="Route Optimization & Fleet Telemetry Hub"
        subtitle="Real-time transit tracking, highway traffic congestion mitigation, fuel economics, and ESG emissions abatement."
      />

      {/* Fleet High-Level Telemetry KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        <KPICard title="Active Fleet Trucks" value="42" status="healthy" subtitle="98% telemetry active" icon={Navigation} />
        <KPICard title="Route Efficiency" value="92.4%" delta="+3.6%" status="positive" subtitle="Optimal 2-Opt transit rate" icon={Route} />
        <KPICard title="Fuel Costs Saved" value="₹1.48M" delta="+18.2%" status="positive" subtitle="14,280 L diesel saved this mo." icon={Fuel} />
        <KPICard title="CO₂ Abated (ESG)" value="38.2 T" delta="+14%" status="positive" subtitle="Scope-1 Clean Fleet standard" icon={Leaf} />
      </div>

      {/* Live Highway Traffic & Congestion Alert Center */}
      <div className="glass-panel rounded-xl overflow-hidden flex flex-col border border-amber-500/25">
        <div className="p-md border-b border-outline-variant bg-surface-container-low/60 flex justify-between items-center flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-amber-400 animate-pulse" />
            <h3 className="font-title-sm text-title-sm font-bold text-on-surface">
              Live Freight Corridor Traffic & Toll Plaza Monitor
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-on-surface-variant">Maharashtra State Logistics Grid</span>
            <button
              onClick={handleAutoRerouteAll}
              disabled={rerouteStatus === 'optimizing'}
              className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 font-bold px-2.5 py-1 rounded-lg text-[11px] flex items-center gap-1 cursor-pointer transition-all disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{rerouteStatus === 'optimizing' ? 'Recalculating…' : rerouteStatus === 'done' ? 'All 3 Rerouted ✓' : 'Auto-Reroute Affected Fleet'}</span>
            </button>
          </div>
        </div>

        <div className="p-md grid grid-cols-1 md:grid-cols-3 gap-md">
          {CORRIDOR_TRAFFIC_DATA.map((item, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-xl border flex flex-col justify-between ${
                item.severity === 'danger'
                  ? 'bg-rose-500/10 border-rose-500/30'
                  : item.severity === 'warning'
                  ? 'bg-amber-500/10 border-amber-500/30'
                  : 'bg-emerald-500/10 border-emerald-500/30'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-bold text-[12px] text-on-surface">{item.corridor}</span>
                  <span
                    className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                      item.severity === 'danger'
                        ? 'bg-rose-500/20 text-rose-400'
                        : item.severity === 'warning'
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-emerald-500/20 text-emerald-400'
                    }`}
                  >
                    {item.speed}
                  </span>
                </div>
                <p className="text-[11px] text-on-surface-variant font-mono">{item.statusText}</p>
              </div>

              <div className="mt-2 pt-2 border-t border-outline-variant/30 flex items-center justify-between text-[10px] font-mono">
                <span className="text-on-surface-variant">Mitigation:</span>
                <span className="text-primary font-bold">{item.mitigation}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Multi-Stop Route Optimizer & Real-Time Map */}
      <MultiStopRouteOptimizer
        activeTruck={activeTruck}
        setActiveTruck={setActiveTruck}
      />

      {/* Active Fleet Transit Table with Direct Map Focus */}
      <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
        <div className="p-lg border-b border-outline-variant bg-surface-container-low/50 flex justify-between items-center flex-wrap gap-2">
          <div>
            <h3 className="font-title-md text-title-md font-bold text-on-surface">Active Fleet Shipments & Telemetry</h3>
            <p className="text-[11px] text-on-surface-variant">Click any vehicle to track in Google Maps & load live sensor HUD.</p>
          </div>
          <span className="font-label-sm text-label-sm text-primary font-mono flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            LIVE TELEMETRY STREAM (42 TRUCKS)
          </span>
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
                <th className="px-lg py-md text-label-sm text-on-surface-variant uppercase font-mono text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30">
              {routes.map((route) => {
                const isSelected = activeTruck?.truckId === route.truckId;
                return (
                  <tr
                    key={route.id}
                    onClick={() => handleSelectRouteRow(route)}
                    className={`hover:bg-surface-variant/20 transition-colors cursor-pointer ${
                      isSelected ? 'bg-primary/10 border-l-4 border-primary' : ''
                    }`}
                  >
                    <td className="px-lg py-md">
                      <div className="font-bold text-on-surface flex items-center gap-1.5">
                        <Truck className={`w-3.5 h-3.5 ${isSelected ? 'text-primary' : 'text-on-surface-variant'}`} />
                        <span>{route.id}</span>
                      </div>
                      <div className="text-[10px] text-on-surface-variant font-mono">{route.truckId}</div>
                    </td>
                    <td className="px-lg py-md text-body-md text-on-surface">{route.driver}</td>
                    <td className="px-lg py-md text-body-md font-mono text-on-surface-variant">
                      {route.origin} → <span className="text-on-surface font-bold">{route.destination}</span>
                    </td>
                    <td className="px-lg py-md text-body-md font-mono font-bold text-primary">{route.eta}</td>
                    <td className="px-lg py-md">
                      <span className="flex items-center gap-1 font-mono text-label-md text-emerald-400">
                        <Thermometer className="w-4 h-4 text-emerald-400" />
                        {route.temp}
                      </span>
                    </td>
                    <td className="px-lg py-md font-mono text-primary font-bold">{route.fuelSaved}</td>
                    <td className="px-lg py-md">
                      <StatusBadge status={route.status} />
                    </td>
                    <td className="px-lg py-md text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectRouteRow(route);
                        }}
                        className={`text-[11px] font-mono px-2.5 py-1 rounded-lg border font-bold transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-primary text-on-primary border-primary'
                            : 'bg-surface-container-high text-on-surface-variant border-outline-variant hover:text-on-surface'
                        }`}
                      >
                        {isSelected ? 'Tracking' : 'Track in Map'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
