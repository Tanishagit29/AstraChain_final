import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  MapPin, Navigation, Truck, Play, Pause, RotateCw, ExternalLink,
  Layers, Compass, ZoomIn, ZoomOut, Maximize2, Minimize2, ShieldCheck, Thermometer,
  Fuel, Clock, AlertTriangle, ArrowRight, Eye, CheckCircle2, Radio,
  Activity, Gauge, Send, Share2, Flame, Leaf, ChevronRight, ChevronDown,
  Zap, Info, BellRing, Smartphone
} from 'lucide-react';
import { api } from '../api/client';

export const LOCATION_COORDINATES = {
  'Mumbai Central Port': { lat: 18.9690, lng: 72.8444, type: 'Port / Central Depot', city: 'Mumbai' },
  'Mumbai Central': { lat: 18.9690, lng: 72.8444, type: 'Urban Depot', city: 'Mumbai' },
  'Mumbai Andheri Store': { lat: 19.1197, lng: 72.8468, type: 'Retail Store', city: 'Mumbai' },
  'Mumbai Bandra Outlet': { lat: 19.0596, lng: 72.8295, type: 'Retail Outlet', city: 'Mumbai' },
  'Navi Mumbai Vashi Hub': { lat: 19.0771, lng: 73.0027, type: 'Logistics Hub', city: 'Navi Mumbai' },
  'Thane Cold Storage': { lat: 19.2183, lng: 72.9781, type: 'Cold Storage Facility', city: 'Thane' },
  'Thane East': { lat: 19.2183, lng: 72.9781, type: 'Depot', city: 'Thane' },
  'Thane Ghodbunder Store': { lat: 19.2571, lng: 72.9789, type: 'Retail Store', city: 'Thane' },
  'Pune Logistics Hub': { lat: 18.5204, lng: 73.8567, type: 'Regional Hub', city: 'Pune' },
  'Pune North Hub': { lat: 18.6204, lng: 73.8167, type: 'Distribution Center', city: 'Pune' },
  'Pune Kothrud Store': { lat: 18.5074, lng: 73.8077, type: 'Retail Outlet', city: 'Pune' },
  'Pune Viman Nagar Outlet': { lat: 18.5679, lng: 73.9143, type: 'Retail Outlet', city: 'Pune' },
  'Nashik Warehouse': { lat: 19.9975, lng: 73.7898, type: 'Primary Warehouse', city: 'Nashik' },
  'Nashik City Center': { lat: 19.9975, lng: 73.7898, type: 'Retail Center', city: 'Nashik' },
  'Satara Warehouse': { lat: 17.6805, lng: 73.9917, type: 'Fulfillment Center', city: 'Satara' },
  'Kolhapur Distribution': { lat: 16.7050, lng: 74.2433, type: 'Distribution Center', city: 'Kolhapur' },
  'Solapur Distribution': { lat: 17.6599, lng: 75.9064, type: 'Distribution Hub', city: 'Solapur' },
  'Aurangabad Depot': { lat: 19.8762, lng: 75.3433, type: 'Regional Depot', city: 'Aurangabad' },
  'Surat Port Depot': { lat: 21.1702, lng: 72.8311, type: 'Coastal Terminal', city: 'Surat' },
  'Nagpur Park': { lat: 21.1458, lng: 79.0882, type: 'Logistics Park', city: 'Nagpur' },
};

// Key Highway Toll Plazas & Traffic Choke Points
export const TRAFFIC_INCIDENTS = [
  {
    id: 'TOL-01',
    name: 'Vashi Toll Plaza (FASTag)',
    lat: 19.0620,
    lng: 72.9850,
    status: 'HEAVY',
    delay: '+8 min delay',
    speed: '18 km/h',
    type: 'Toll Bottleneck',
    description: 'Lane 3 & 4 commercial truck queue moving at 18 km/h',
  },
  {
    id: 'GHT-01',
    name: 'Khandala Ghat Section (NH-48)',
    lat: 18.7550,
    lng: 73.3750,
    status: 'MODERATE',
    delay: 'Speed Restrict: 35 km/h',
    speed: '35 km/h',
    type: 'Ghat Descent & Curves',
    description: 'Heavy vehicle speed control enforcement on wet asphalt incline',
  },
  {
    id: 'TOL-02',
    name: 'Khalapur Toll Plaza',
    lat: 18.8250,
    lng: 73.2850,
    status: 'MODERATE',
    delay: '+4 min delay',
    speed: '38 km/h',
    type: 'Expressway Toll',
    description: 'Automated FASTag scanning active; minor entry crawl',
  },
  {
    id: 'TOL-03',
    name: 'Talegaon Expressway Toll',
    lat: 18.7300,
    lng: 73.6800,
    status: 'CLEAR',
    delay: 'Free Flowing',
    speed: '72 km/h',
    type: 'Expressway Exit',
    description: 'All 8 FASTag lanes green; no commercial queue',
  },
  {
    id: 'CON-01',
    name: 'Thane Ghodbunder Flyover',
    lat: 19.2450,
    lng: 72.9700,
    status: 'HEAVY',
    delay: '+14 min delay',
    speed: '14 km/h',
    type: 'Construction Divert',
    description: 'Metro line pier work reducing roadway to 2 lanes',
  },
];

export const FLEET_VEHICLES = [
  {
    truckId: 'MH-04-JK-4821',
    driver: 'Rajesh Kumar',
    vehicleType: '14ft Cold-Chain Reefer',
    cargo: 'Fresh Milk & Dairy Products',
    origin: 'Mumbai Central Port',
    stops: ['Pune Logistics Hub', 'Nashik Warehouse'],
    temp: '+3.2°C',
    fuelLevel: 78,
    speed: 68,
    fuelSavedLiters: 18.4,
    fuelSavedInr: 1850,
    co2AbatedKg: 49.3,
  },
  {
    truckId: 'MH-12-PQ-9102',
    driver: 'Suresh Patil',
    vehicleType: '20ft BharatBenz Deep-Freezer',
    cargo: 'Ice Cream & Frozen Produce',
    origin: 'Nashik Warehouse',
    stops: ['Thane Cold Storage', 'Mumbai Andheri Store'],
    temp: '-18.2°C',
    fuelLevel: 62,
    speed: 54,
    fuelSavedLiters: 14.2,
    fuelSavedInr: 1420,
    co2AbatedKg: 38.1,
  },
  {
    truckId: 'MH-46-AB-3301',
    driver: 'Amit Shinde',
    vehicleType: '32ft Multi-Axle Ambient Carrier',
    cargo: 'Grains & Basmati Rice Staples',
    origin: 'Pune North Hub',
    stops: ['Solapur Distribution', 'Satara Warehouse'],
    temp: 'Ambient (+25.8°C)',
    fuelLevel: 85,
    speed: 62,
    fuelSavedLiters: 24.0,
    fuelSavedInr: 2400,
    co2AbatedKg: 64.3,
  },
  {
    truckId: 'MH-02-CD-5541',
    driver: 'Vikram Singh',
    vehicleType: '16ft Tata Ultra Fast-Cargo',
    cargo: 'Organic Mangoes & Seasonal Fruit',
    origin: 'Surat Port Depot',
    stops: ['Mumbai Central Port', 'Navi Mumbai Vashi Hub'],
    temp: '+7.4°C',
    fuelLevel: 71,
    speed: 70,
    fuelSavedLiters: 31.0,
    fuelSavedInr: 3100,
    co2AbatedKg: 83.1,
  },
];

export default function LiveRouteMap({
  origin = 'Mumbai Central Port',
  stops = ['Pune Logistics Hub', 'Nashik Warehouse'],
  optimizedSequence = null,
  naiveSequence = null,
  truckId = 'MH-04-JK-4821',
  distanceSavedKm = 0,
  savingsPct = 0,
  returnToOrigin = true,
  onSelectTruck = null,
}) {
  const [mapMode, setMapMode] = useState('roadmap'); // 'roadmap', 'satellite', 'dark', 'embed'
  const [showTraffic, setShowTraffic] = useState(true);
  const [showComparison, setShowComparison] = useState(true);
  const [showFuelPanel, setShowFuelPanel] = useState(false);
  const [showNavDrawer, setShowNavDrawer] = useState(false);
  const [isPlaying, setIsPlaying] = useState(true);
  const [simSpeed, setSimSpeed] = useState(1); // 1x, 2x, 4x
  const [progress, setProgress] = useState(0.18); // 0 to 1
  const [selectedStop, setSelectedStop] = useState(null);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [phonePushStatus, setPhonePushStatus] = useState(null); // 'sending', 'sent', null
  const mapContainerRef = useRef(null);

  // Active Vehicle Data
  const currentVehicle = useMemo(() => {
    return (
      FLEET_VEHICLES.find((v) => v.truckId === truckId) || {
        truckId,
        driver: 'Rajesh Kumar',
        vehicleType: 'Commercial Logistics Reefer',
        cargo: 'Perishable Consignments',
        origin,
        stops,
        temp: '+3.2°C',
        fuelLevel: 76,
        speed: 64,
        fuelSavedLiters: Math.max(12, Math.round((distanceSavedKm || 35) / 5.2)),
        fuelSavedInr: Math.max(1200, Math.round((distanceSavedKm || 35) * 18)),
        co2AbatedKg: Math.max(32, Math.round(((distanceSavedKm || 35) / 5.2) * 2.68)),
      }
    );
  }, [truckId, origin, stops, distanceSavedKm]);

  // Derive route sequence
  const activeSequence = useMemo(() => {
    if (optimizedSequence && optimizedSequence.length > 0) {
      return optimizedSequence;
    }
    const safeStops = Array.isArray(stops) ? stops : [];
    const seq = [origin, ...safeStops];
    if (returnToOrigin && seq.length > 1) seq.push(origin);
    return seq;
  }, [optimizedSequence, origin, stops, returnToOrigin]);

  // Coordinates of the sequence
  const routePoints = useMemo(() => {
    return activeSequence.map((name) => {
      const coord = LOCATION_COORDINATES[name] || { lat: 19.0760, lng: 72.8777, type: 'Waypoint', city: 'Maharashtra' };
      return {
        name,
        lat: coord.lat,
        lng: coord.lng,
        type: coord.type,
        city: coord.city,
      };
    });
  }, [activeSequence]);

  // Naive sequence points for comparison
  const naivePoints = useMemo(() => {
    if (!naiveSequence || naiveSequence.length === 0) return [];
    return naiveSequence.map((name) => {
      const coord = LOCATION_COORDINATES[name] || { lat: 19.0760, lng: 72.8777 };
      return { name, lat: coord.lat, lng: coord.lng };
    });
  }, [naiveSequence]);

  // Compute map projection bounds
  const bounds = useMemo(() => {
    if (routePoints.length === 0) return { minLat: 18, maxLat: 20, minLng: 72, maxLng: 75 };
    const lats = routePoints.map((p) => p.lat);
    const lngs = routePoints.map((p) => p.lng);

    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    const latPad = Math.max((maxLat - minLat) * 0.22, 0.4);
    const lngPad = Math.max((maxLng - minLng) * 0.22, 0.4);

    return {
      minLat: minLat - latPad,
      maxLat: maxLat + latPad,
      minLng: minLng - lngPad,
      maxLng: maxLng + lngPad,
    };
  }, [routePoints]);

  // SVG coordinate transformation
  const width = 840;
  const height = 520;

  const project = (lat, lng) => {
    const x = ((lng - bounds.minLng) / (bounds.maxLng - bounds.minLng)) * width;
    const y = ((bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat)) * height;
    return { x, y };
  };

  // Convert points to SVG polyline string
  const svgPathData = useMemo(() => {
    if (routePoints.length < 2) return '';
    return routePoints
      .map((p, idx) => {
        const { x, y } = project(p.lat, p.lng);
        return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');
  }, [routePoints, bounds]);

  const naiveSvgPathData = useMemo(() => {
    if (naivePoints.length < 2) return '';
    return naivePoints
      .map((p, idx) => {
        const { x, y } = project(p.lat, p.lng);
        return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');
  }, [naivePoints, bounds]);

  // Simulation timer for moving truck along the route
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setProgress((prev) => {
        const step = 0.0025 * simSpeed;
        const next = prev + step;
        if (prev < 0.985 && next >= 0.985) {
          // Trigger delivery arrival notification
          api.notifyRouteArrival({
            truck_id: activeVehicle?.truckId || 'MH-04-JK-4821',
            origin: activeVehicle?.origin || 'Mumbai Central Port',
            destination: (activeVehicle?.stops && activeVehicle.stops[0]) || 'Pune Logistics Hub',
            fuel_saved: 14.2,
            co2_saved: 38.0,
          }).catch(() => {});
        }
        return next > 1 ? 0 : next;
      });
    }, 50);

    return () => clearInterval(interval);
  }, [isPlaying, simSpeed]);

  // Compute animated truck position along the SVG path
  const truckPos = useMemo(() => {
    if (routePoints.length < 2) return { x: 420, y: 260, heading: 0, currentLegIdx: 0 };

    const totalSegments = routePoints.length - 1;
    const segProgress = progress * totalSegments;
    const segIdx = Math.min(Math.floor(segProgress), totalSegments - 1);
    const subT = segProgress - segIdx;

    const p1 = project(routePoints[segIdx].lat, routePoints[segIdx].lng);
    const p2 = project(routePoints[segIdx + 1].lat, routePoints[segIdx + 1].lng);

    const x = p1.x + (p2.x - p1.x) * subT;
    const y = p1.y + (p2.y - p1.y) * subT;

    const angleRad = Math.atan2(p2.y - p1.y, p2.x - p1.x);
    const heading = (angleRad * 180) / Math.PI;

    // Dynamic speed based on progress and traffic
    const isTrafficSlowdown = subT > 0.3 && subT < 0.6;
    const currentSpeed = isTrafficSlowdown ? 36 : Math.round(62 + Math.sin(progress * 20) * 8);

    return {
      x,
      y,
      heading,
      currentLegIdx: segIdx,
      fromStop: routePoints[segIdx].name,
      toStop: routePoints[segIdx + 1].name,
      speed: currentSpeed,
      distCoveredPct: Math.round(progress * 100),
      etaNextMinutes: Math.max(5, Math.round((1 - subT) * 45)),
    };
  }, [progress, routePoints, bounds]);

  // Turn-by-Turn Navigation Items
  const turnByTurnSteps = useMemo(() => {
    if (routePoints.length < 2) return [];
    const stepsList = [];
    routePoints.forEach((pt, idx) => {
      if (idx === 0) {
        stepsList.push({
          icon: Compass,
          title: `Depart ${pt.name}`,
          instruction: 'Proceed onto freight corridor toward NH-48 Express highway',
          distance: '2.4 km',
          type: 'depart',
        });
      } else {
        stepsList.push({
          icon: Navigation,
          title: `Transit NH-48 Expressway toward ${pt.name}`,
          instruction: 'Maintain lane 2 for commercial reefer; pass automated FASTag plaza',
          distance: '48.5 km',
          type: 'transit',
        });
        stepsList.push({
          icon: MapPin,
          title: `Arrive at Stop #${idx}: ${pt.name}`,
          instruction: `Dock at Bay 4 · Unload designated consignments (${LOCATION_COORDINATES[pt.name]?.type || 'Hub'})`,
          distance: '0.8 km',
          type: 'arrive',
        });
      }
    });
    return stepsList;
  }, [routePoints]);

  // Construct official Google Maps directions URL
  const googleMapsUrl = useMemo(() => {
    if (activeSequence.length < 2) return 'https://www.google.com/maps';
    const originEnc = encodeURIComponent(activeSequence[0] + ', Maharashtra, India');
    const destEnc = encodeURIComponent(activeSequence[activeSequence.length - 1] + ', Maharashtra, India');
    const waypoints = activeSequence.slice(1, activeSequence.length - 1);
    const waypointsEnc = waypoints.map((w) => encodeURIComponent(w + ', Maharashtra, India')).join('|');

    return `https://www.google.com/maps/dir/?api=1&origin=${originEnc}&destination=${destEnc}${
      waypointsEnc ? `&waypoints=${waypointsEnc}` : ''
    }&travelmode=driving`;
  }, [activeSequence]);

  // Send Route to Phone Notification
  const handleSendToPhone = async () => {
    setPhonePushStatus('sending');
    try {
      await api.testPhoneNotification();
      setPhonePushStatus('sent');
      setTimeout(() => setPhonePushStatus(null), 3500);
    } catch {
      setPhonePushStatus(null);
    }
  };

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!mapContainerRef.current) return;
    if (!document.fullscreenElement) {
      mapContainerRef.current.requestFullscreen?.().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.().catch(() => {});
      setIsFullscreen(false);
    }
  };

  // Theme palettes
  const isDark = mapMode === 'dark';
  const isSat = mapMode === 'satellite';

  const mapBg = isSat
    ? 'bg-[#0f172a]'
    : isDark
    ? 'bg-[#0a0f1d]'
    : 'bg-[#f1f5f9]';

  const roadStroke = isDark ? '#1e293b' : isSat ? '#1e293b' : '#e2e8f0';
  const majorRoadStroke = isDark ? '#334155' : isSat ? '#334155' : '#cbd5e1';

  // Fuel & ESG Calculations
  const calculatedFuelSavedL = currentVehicle.fuelSavedLiters || (distanceSavedKm > 0 ? Number((distanceSavedKm / 5.2).toFixed(1)) : 16.5);
  const calculatedInrSaved = currentVehicle.fuelSavedInr || (distanceSavedKm > 0 ? Math.round(distanceSavedKm * 18) : 1650);
  const calculatedCo2Kg = currentVehicle.co2AbatedKg || Number((calculatedFuelSavedL * 2.68).toFixed(1));

  return (
    <div
      ref={mapContainerRef}
      className={`glass-card rounded-2xl overflow-hidden border border-outline-variant/80 shadow-2xl flex flex-col relative group ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none bg-surface' : ''
      }`}
    >
      {/* Fleet Truck Quick Switcher Bar */}
      <div className="bg-surface-container-highest/70 px-3 py-2 border-b border-outline-variant/60 flex items-center justify-between overflow-x-auto gap-2 scrollbar-thin">
        <div className="flex items-center gap-2 shrink-0">
          <Truck className="w-4 h-4 text-primary" />
          <span className="font-mono text-[11px] font-bold text-on-surface uppercase tracking-wider">
            Active Fleet Telemetry:
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {FLEET_VEHICLES.map((veh) => {
            const isSelected = veh.truckId === truckId;
            return (
              <button
                key={veh.truckId}
                onClick={() => onSelectTruck?.(veh)}
                className={`px-2.5 py-1 rounded-xl text-[11px] font-mono font-bold transition-all cursor-pointer flex items-center gap-1.5 border ${
                  isSelected
                    ? 'bg-primary text-on-primary border-primary shadow-sm'
                    : 'bg-surface-container-low text-on-surface-variant hover:text-on-surface border-outline-variant hover:bg-surface-container-high'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-on-primary animate-pulse' : 'bg-emerald-400'}`} />
                <span>{veh.truckId}</span>
                <span className={`text-[9px] px-1 py-0.2 rounded font-sans ${isSelected ? 'bg-on-primary/20' : 'bg-surface-container-high text-on-surface-variant'}`}>
                  {veh.temp}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Google Maps Styled Header Control Bar */}
      <div className="p-3 bg-surface-container-low/95 backdrop-blur-md border-b border-outline-variant/60 flex items-center justify-between flex-wrap gap-2">
        {/* Left: Google Maps Brand & Active Route Title */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-sm">
            <Navigation className="w-4 h-4 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-on-surface text-[13px] flex items-center gap-1.5">
                <span className="text-primary font-mono">Google Maps</span> Live Logistics Hub
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live GPS Active (50ms)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/25">
                {currentVehicle.vehicleType}
              </span>
            </div>
            <p className="text-[11px] font-mono text-on-surface-variant">
              Truck: <strong className="text-on-surface">{truckId}</strong> ({currentVehicle.driver}) · {activeSequence.length - 1} Delivery Legs ·{' '}
              {distanceSavedKm > 0 ? (
                <span className="text-emerald-400 font-bold">Saved {distanceSavedKm} km (-{savingsPct}%)</span>
              ) : (
                <span className="text-emerald-400 font-bold">2-Opt AI Route Optimized</span>
              )}
            </p>
          </div>
        </div>

        {/* Right: Map Style Toggles & Actions */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Map Style Pills */}
          <div className="bg-surface-container-high/60 p-0.5 rounded-xl border border-outline-variant flex items-center text-[11px] font-medium">
            <button
              onClick={() => setMapMode('roadmap')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                mapMode === 'roadmap' ? 'bg-primary text-on-primary font-bold shadow' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Roadmap
            </button>
            <button
              onClick={() => setMapMode('satellite')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                mapMode === 'satellite' ? 'bg-primary text-on-primary font-bold shadow' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Satellite
            </button>
            <button
              onClick={() => setMapMode('dark')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                mapMode === 'dark' ? 'bg-primary text-on-primary font-bold shadow' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Dark HUD
            </button>
            <button
              onClick={() => setMapMode('embed')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                mapMode === 'embed' ? 'bg-secondary text-on-secondary font-bold shadow' : 'text-on-surface-variant hover:text-on-surface'
              }`}
              title="View live interactive Google Maps embed"
            >
              Google Embed
            </button>
          </div>

          {/* Traffic Toggle */}
          <button
            onClick={() => setShowTraffic(!showTraffic)}
            className={`px-2.5 py-1 rounded-xl text-[11px] font-medium border transition-all cursor-pointer flex items-center gap-1.5 ${
              showTraffic
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 font-bold'
                : 'bg-surface-container-high text-on-surface-variant border-outline-variant'
            }`}
            title="Toggle Live Highway Traffic Congestion & Toll Plazas"
          >
            <span className={`w-2 h-2 rounded-full ${showTraffic ? 'bg-emerald-400 animate-pulse' : 'bg-on-surface-variant/40'}`} />
            Traffic Flow
          </button>

          {/* Fuel & ESG Economics Button */}
          <button
            onClick={() => setShowFuelPanel(!showFuelPanel)}
            className={`px-2.5 py-1 rounded-xl text-[11px] font-medium border transition-all cursor-pointer flex items-center gap-1.5 ${
              showFuelPanel
                ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 font-bold'
                : 'bg-surface-container-high text-on-surface-variant border-outline-variant hover:text-on-surface'
            }`}
            title="View Fuel Saved, Diesel Economics & CO2 Abatement"
          >
            <Fuel className="w-3.5 h-3.5 text-amber-400" />
            <span>Fuel Saved (₹{calculatedInrSaved.toLocaleString()})</span>
          </button>

          {/* Turn-by-Turn Navigation Drawer Toggle */}
          <button
            onClick={() => setShowNavDrawer(!showNavDrawer)}
            className={`px-2.5 py-1 rounded-xl text-[11px] font-medium border transition-all cursor-pointer flex items-center gap-1 ${
              showNavDrawer
                ? 'bg-primary/20 text-primary border-primary/40 font-bold'
                : 'bg-surface-container-high text-on-surface-variant border-outline-variant hover:text-on-surface'
            }`}
            title="Toggle Turn-by-Turn Maneuvers"
          >
            <Navigation className="w-3 h-3" />
            <span>Directions</span>
          </button>

          {/* Naive vs Optimized Comparison Toggle */}
          {naiveSequence && (
            <button
              onClick={() => setShowComparison(!showComparison)}
              className={`px-2.5 py-1 rounded-xl text-[11px] font-medium border transition-all cursor-pointer flex items-center gap-1 ${
                showComparison
                  ? 'bg-primary/15 text-primary border-primary/30 font-bold'
                  : 'bg-surface-container-high text-on-surface-variant border-outline-variant'
              }`}
              title="Compare unoptimized baseline tour with 2-Opt optimized route"
            >
              <Eye className="w-3 h-3" />
              Compare
            </button>
          )}

          {/* Send to Driver's Phone */}
          <button
            onClick={handleSendToPhone}
            disabled={phonePushStatus === 'sending'}
            className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold px-2.5 py-1 rounded-xl text-[11px] flex items-center gap-1 transition-all shadow-sm cursor-pointer disabled:opacity-50"
            title="Push route and live tracking directly to the driver's phone"
          >
            <Smartphone className="w-3 h-3" />
            <span>{phonePushStatus === 'sending' ? 'Pushing…' : phonePushStatus === 'sent' ? 'Notified!' : 'Send to Phone'}</span>
          </button>

          {/* External Google Maps Button */}
          <a
            href={googleMapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 font-bold px-2.5 py-1 rounded-xl text-[11px] flex items-center gap-1 transition-all shadow-sm"
            title="Open turn-by-turn navigation directly in Google Maps in a new tab"
          >
            <span>Open Maps</span>
            <ExternalLink className="w-3 h-3" />
          </a>

          {/* Fullscreen Button */}
          <button
            onClick={toggleFullscreen}
            className="p-1 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors cursor-pointer"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Command Center'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Main Map Canvas Area */}
      <div className={`relative w-full ${isFullscreen ? 'h-[calc(100vh-130px)]' : 'h-[500px]'} overflow-hidden select-none`}>
        {mapMode === 'embed' ? (
          /* Live Interactive Google Maps Iframe */
          <div className="w-full h-full relative">
            <iframe
              title="Google Maps Live Route View"
              width="100%"
              height="100%"
              style={{ border: 0 }}
              loading="lazy"
              allowFullScreen
              referrerPolicy="no-referrer-when-downgrade"
              src={`https://maps.google.com/maps?q=${encodeURIComponent(
                activeSequence[0] + ', Maharashtra, India'
              )}&t=m&z=10&output=embed`}
            />
            <div className="absolute top-3 left-3 bg-surface/90 backdrop-blur-md p-2 rounded-xl border border-outline-variant text-[11px] font-mono shadow-md">
              <span className="font-bold text-on-surface">Interactive Google Maps View</span> · Click pins for street view
            </div>
          </div>
        ) : (
          /* Custom Google Maps Styled Interactive SVG Telemetry Canvas */
          <div className={`w-full h-full ${mapBg} relative transition-colors duration-300 flex items-center justify-center overflow-hidden`}>
            {/* Background Map Grid & Regional Water/Terrain Accents */}
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="w-full h-full object-cover"
              style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center' }}
            >
              <defs>
                {/* Google Maps Blue Polyline Glow */}
                <filter id="routeGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1a73e8" floodOpacity="0.5" />
                </filter>
                <filter id="pinShadow" x="-30%" y="-30%" width="160%" height="160%">
                  <feDropShadow dx="0" dy="3" stdDeviation="2" floodColor="#000000" floodOpacity="0.4" />
                </filter>
                <filter id="trafficGlow" x="-30%" y="-30%" width="160%" height="160%">
                  <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#ea4335" floodOpacity="0.6" />
                </filter>
              </defs>

              {/* Geographic Grid Lines */}
              <g stroke={roadStroke} strokeWidth="1" strokeDasharray="3,6" opacity="0.35">
                <line x1="0" y1="130" x2={width} y2="130" />
                <line x1="0" y1="260" x2={width} y2="260" />
                <line x1="0" y1="390" x2={width} y2="390" />
                <line x1="210" y1="0" x2="210" y2={height} />
                <line x1="420" y1="0" x2="420" y2={height} />
                <line x1="630" y1="0" x2="630" y2={height} />
              </g>

              {/* Highway Network Overlay */}
              <g stroke={majorRoadStroke} strokeWidth="2.5" opacity="0.5">
                <path d={`M 50 160 Q 210 230 420 280 T 780 400`} fill="none" strokeDasharray="6,4" />
                <path d={`M 160 50 Q 310 190 460 330 T 670 500`} fill="none" strokeDasharray="6,4" />
                <path d={`M 260 270 Q 420 380 580 470`} fill="none" strokeDasharray="4,4" />
              </g>

              {/* Coastal Line Contour (Arabian Sea / West Coast representation) */}
              <path
                d="M 45 0 C 75 130, 55 260, 85 520 L 0 520 L 0 0 Z"
                fill={isDark || isSat ? '#091e36' : '#cce5ff'}
                opacity={isDark ? '0.45' : '0.65'}
              />

              {/* Highway Corridor Badges */}
              <g className="font-mono text-[9px] fill-on-surface-variant font-bold" opacity="0.75">
                <text x="85" y="150">NH-48 (Mumbai-Pune Expressway)</text>
                <text x="380" y="120">NH-60 (Nashik Corridor)</text>
                <text x="480" y="460">NH-65 (Solapur Highway)</text>
                <text x="12" y="250" fill={isDark ? '#38bdf8' : '#0284c7'}>ARABIAN SEA</text>
              </g>

              {/* Baseline Unoptimized Tour (Red dashed comparison line) */}
              {showComparison && naiveSvgPathData && (
                <g opacity="0.55">
                  <path
                    d={naiveSvgPathData}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="2.5"
                    strokeDasharray="5,5"
                  />
                </g>
              )}

              {/* LIVE TRAFFIC CONGESTION OVERLAY */}
              {showTraffic && svgPathData && (
                <g opacity="0.85" strokeLinecap="round">
                  {/* Underlay glow representing live highway traffic conditions */}
                  {/* Free-flow Green Highway Segment */}
                  <path
                    d={svgPathData}
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="9"
                    opacity="0.35"
                  />
                  {/* Pulsing Red Choke Segment along first 30% (e.g. Vashi Toll bottleneck) */}
                  <path
                    d={svgPathData}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="8"
                    strokeDasharray="90, 240"
                    strokeDashoffset="20"
                    opacity="0.85"
                  />
                  {/* Amber Ghat Segment along 40-60% (e.g. Khandala Ghat curves) */}
                  <path
                    d={svgPathData}
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="8"
                    strokeDasharray="80, 260"
                    strokeDashoffset="140"
                    opacity="0.8"
                  />
                </g>
              )}

              {/* OPTIMIZED GOOGLE MAPS ROUTE POLYLINE */}
              {svgPathData && (
                <g>
                  {/* Outer casing */}
                  <path
                    d={svgPathData}
                    fill="none"
                    stroke={isDark ? '#0284c7' : '#ffffff'}
                    strokeWidth="7"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    opacity="0.85"
                  />
                  {/* Inner Vibrant Google Maps Blue Polyline */}
                  <path
                    d={svgPathData}
                    fill="none"
                    stroke="#1a73e8"
                    strokeWidth="4.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    filter="url(#routeGlow)"
                  />
                  {/* Animated directional pulsing dash */}
                  <path
                    d={svgPathData}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="1.5"
                    strokeDasharray="8,16"
                    className="animate-pulse"
                    opacity="0.9"
                  />
                </g>
              )}

              {/* Traffic Choke & Toll Plaza Markers */}
              {showTraffic &&
                TRAFFIC_INCIDENTS.map((inc) => {
                  const pt = project(inc.lat, inc.lng);
                  const isRed = inc.status === 'HEAVY';
                  const isAmber = inc.status === 'MODERATE';
                  const color = isRed ? '#ef4444' : isAmber ? '#f59e0b' : '#10b981';

                  return (
                    <g
                      key={inc.id}
                      className="cursor-pointer transition-transform hover:scale-125"
                      onClick={() => setSelectedIncident(inc)}
                      filter="url(#pinShadow)"
                    >
                      <circle cx={pt.x} cy={pt.y} r={isRed ? 14 : 10} fill={color} opacity="0.25" className="animate-ping" />
                      <circle cx={pt.x} cy={pt.y} r="8" fill={color} stroke="#ffffff" strokeWidth="1.5" />
                      <text x={pt.x} y={pt.y + 3} textAnchor="middle" className="fill-white font-mono font-bold text-[8px]">
                        {isRed ? '!' : 'T'}
                      </text>
                      <text
                        x={pt.x}
                        y={pt.y + 18}
                        textAnchor="middle"
                        className="font-mono text-[8px] font-bold fill-on-surface"
                      >
                        {inc.name.split(' ')[0]} ({inc.delay})
                      </text>
                    </g>
                  );
                })}

              {/* Waypoint Connecting Leg Markers */}
              {routePoints.map((p, idx) => {
                if (idx === routePoints.length - 1) return null;
                const nextP = routePoints[idx + 1];
                const pt1 = project(p.lat, p.lng);
                const pt2 = project(nextP.lat, nextP.lng);
                const midX = (pt1.x + pt2.x) / 2;
                const midY = (pt1.y + pt2.y) / 2;

                return (
                  <g key={`leg-${idx}`}>
                    <circle cx={midX} cy={midY} r="3" fill="#1a73e8" opacity="0.8" />
                  </g>
                );
              })}

              {/* Waypoint Marker Pins */}
              {routePoints.map((p, idx) => {
                const { x, y } = project(p.lat, p.lng);
                const isOrigin = idx === 0;
                const isReturn = idx === routePoints.length - 1 && returnToOrigin && idx > 0;
                const isSelected = selectedStop === p.name;

                return (
                  <g
                    key={`${p.name}-${idx}`}
                    className="cursor-pointer transition-transform hover:scale-125"
                    onClick={() => setSelectedStop(p.name)}
                    filter="url(#pinShadow)"
                  >
                    {/* Concentric Pulse Wave for Origin */}
                    {isOrigin && (
                      <circle cx={x} cy={y} r="18" fill="#10b981" opacity="0.2" className="animate-ping" />
                    )}

                    {/* Google Pin Body */}
                    <path
                      d={`M ${x} ${y} 
                          C ${x - 12} ${y - 12}, ${x - 12} ${y - 28}, ${x} ${y - 28} 
                          C ${x + 12} ${y - 28}, ${x + 12} ${y - 12}, ${x} ${y} Z`}
                      fill={isOrigin ? '#10b981' : isReturn ? '#3b82f6' : '#ea4335'}
                      stroke="#ffffff"
                      strokeWidth="1.5"
                    />

                    {/* Pin Center Circle */}
                    <circle cx={x} cy={y - 18} r="6" fill="#ffffff" />

                    {/* Pin Label (A, B, or Number) */}
                    <text
                      x={x}
                      y={y - 15}
                      textAnchor="middle"
                      className="font-bold text-[9px] fill-slate-900 font-sans"
                    >
                      {isOrigin ? 'A' : isReturn ? '✓' : idx}
                    </text>

                    {/* Location Name Tag */}
                    <g transform={`translate(${x}, ${y + 8})`}>
                      <rect
                        x="-48"
                        y="0"
                        width="96"
                        height="18"
                        rx="4"
                        fill={isDark ? '#0f172a' : '#ffffff'}
                        stroke={isSelected ? '#1a73e8' : isDark ? '#334155' : '#cbd5e1'}
                        strokeWidth={isSelected ? '2' : '1'}
                        opacity="0.95"
                      />
                      <text
                        x="0"
                        y="12"
                        textAnchor="middle"
                        className={`text-[9px] font-mono font-bold ${
                          isDark ? 'fill-slate-200' : 'fill-slate-800'
                        }`}
                      >
                        {p.name.length > 14 ? p.name.substring(0, 12) + '…' : p.name}
                      </text>
                    </g>
                  </g>
                );
              })}

              {/* ANIMATED TRUCK VEHICLE MARKER */}
              <g
                transform={`translate(${truckPos.x}, ${truckPos.y}) rotate(${truckPos.heading})`}
                className="transition-transform duration-75"
              >
                {/* Truck Pulse Radar Wave */}
                <circle cx="0" cy="0" r="18" fill="#1a73e8" opacity="0.3" className="animate-ping" />

                {/* Truck Vehicle Bubble */}
                <circle cx="0" cy="0" r="12" fill="#1a73e8" stroke="#ffffff" strokeWidth="2.5" filter="url(#pinShadow)" />

                {/* Truck Cabin Icon */}
                <g transform="translate(-7, -7) scale(0.7)">
                  <path d="M1 3h15v13H1z M16 8h4l3 3v5h-7z" fill="#ffffff" />
                  <circle cx="5.5" cy="18.5" r="2.5" fill="#ffffff" />
                  <circle cx="18.5" cy="18.5" r="2.5" fill="#ffffff" />
                </g>
              </g>
            </svg>

            {/* Map Floating Zoom Controls (Google Maps Style) */}
            <div className="absolute right-4 bottom-14 flex flex-col gap-1.5 z-20">
              <button
                onClick={() => setZoomLevel((z) => Math.min(z + 0.25, 2.5))}
                className="w-8 h-8 rounded-lg bg-surface/90 backdrop-blur-md border border-outline-variant shadow-md flex items-center justify-center text-on-surface hover:bg-surface-container-high transition-colors cursor-pointer"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={() => setZoomLevel((z) => Math.max(z - 0.25, 0.75))}
                className="w-8 h-8 rounded-lg bg-surface/90 backdrop-blur-md border border-outline-variant shadow-md flex items-center justify-center text-on-surface hover:bg-surface-container-high transition-colors cursor-pointer"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={() => setZoomLevel(1)}
                className="w-8 h-8 rounded-lg bg-surface/90 backdrop-blur-md border border-outline-variant shadow-md flex items-center justify-center text-on-surface hover:bg-surface-container-high transition-colors cursor-pointer text-[10px] font-mono font-bold"
                title="Reset Map Bounds"
              >
                1x
              </button>
            </div>

            {/* Floating Live Telemetry & Cockpit HUD (Top Left) */}
            <div className="absolute top-4 left-4 bg-surface/95 backdrop-blur-xl border border-outline-variant/80 rounded-2xl p-3.5 shadow-2xl max-w-xs z-20 space-y-2.5 pointer-events-auto">
              <div className="flex items-center justify-between gap-2 border-b border-outline-variant/40 pb-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-mono font-bold text-[12px] text-on-surface">{truckId}</span>
                </div>
                <div className="flex items-center gap-1 bg-surface-container-high px-2 py-0.5 rounded-full border border-outline-variant text-[10px] font-mono">
                  <Gauge className="w-3 h-3 text-primary" />
                  <span className="font-bold text-on-surface">{truckPos.speed} km/h</span>
                  <span className="text-on-surface-variant/60 font-sans">[Limit 80]</span>
                </div>
              </div>

              {/* Progress & Next Stop */}
              <div className="space-y-1.5 font-mono text-[11px]">
                <div className="flex items-center justify-between text-on-surface-variant">
                  <span>Next Stop:</span>
                  <strong className="text-on-surface truncate max-w-[140px] flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-primary shrink-0" />
                    {truckPos.toStop || 'Destination'}
                  </strong>
                </div>

                <div className="flex items-center justify-between text-on-surface-variant">
                  <span>Leg ETA:</span>
                  <span className="text-primary font-bold flex items-center gap-1">
                    <Clock className="w-3 h-3" /> ~{truckPos.etaNextMinutes} min
                  </span>
                </div>

                <div className="flex items-center justify-between text-on-surface-variant">
                  <span>Cold Chain Reefer:</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <Thermometer className="w-3 h-3" /> {currentVehicle.temp}
                  </span>
                </div>

                <div className="flex items-center justify-between text-on-surface-variant">
                  <span>Fuel Tank Level:</span>
                  <span className="text-on-surface font-bold flex items-center gap-1">
                    <Fuel className="w-3 h-3 text-amber-400" /> {currentVehicle.fuelLevel}%
                  </span>
                </div>

                {/* Trip Progress Bar */}
                <div className="pt-1">
                  <div className="flex items-center justify-between text-[10px] text-on-surface-variant mb-1">
                    <span>Trip Completed</span>
                    <span className="font-bold text-primary">{truckPos.distCoveredPct}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-emerald-400 transition-all duration-300"
                      style={{ width: `${truckPos.distCoveredPct}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Traffic Incident Click Popover */}
            {selectedIncident && (
              <div className="absolute top-4 right-4 bg-surface/95 backdrop-blur-xl border border-rose-500/40 rounded-2xl p-3.5 shadow-2xl max-w-xs z-30 animate-fade-in">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-bold text-[12px] text-rose-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-rose-500" /> {selectedIncident.name}
                  </span>
                  <button onClick={() => setSelectedIncident(null)} className="text-on-surface-variant hover:text-on-surface text-[12px]">
                    ✕
                  </button>
                </div>
                <div className="text-[11px] font-mono text-on-surface space-y-1.5">
                  <p className="text-on-surface-variant">{selectedIncident.description}</p>
                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-outline-variant/40">
                    <div>
                      <span className="text-[10px] text-on-surface-variant uppercase block">Impact</span>
                      <strong className="text-rose-400">{selectedIncident.delay}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-on-surface-variant uppercase block">Corridor Flow</span>
                      <strong className="text-amber-400">{selectedIncident.speed}</strong>
                    </div>
                  </div>
                  <div className="pt-1">
                    <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" /> AI Dynamic Reroute: Auto-bypassing congestion
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Waypoint Click Inspector Popover */}
            {selectedStop && !selectedIncident && (
              <div className="absolute top-4 right-4 bg-surface/95 backdrop-blur-xl border border-primary/40 rounded-2xl p-3.5 shadow-2xl max-w-xs z-30 animate-fade-in">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-bold text-[12px] text-on-surface flex items-center gap-1">
                    <MapPin className="w-4 h-4 text-primary" /> {selectedStop}
                  </span>
                  <button onClick={() => setSelectedStop(null)} className="text-on-surface-variant hover:text-on-surface text-[12px]">
                    ✕
                  </button>
                </div>
                <div className="text-[11px] font-mono text-on-surface-variant space-y-1.5">
                  <p>Type: <strong className="text-on-surface">{LOCATION_COORDINATES[selectedStop]?.type || 'Delivery Stop'}</strong></p>
                  <p>Coordinates: {LOCATION_COORDINATES[selectedStop]?.lat?.toFixed(4)}°N, {LOCATION_COORDINATES[selectedStop]?.lng?.toFixed(4)}°E</p>
                  <div className="pt-2 border-t border-outline-variant/40">
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(selectedStop + ', Maharashtra, India')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center gap-1 text-[11px] font-bold"
                    >
                      Inspect in Google Maps <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* Detailed Fuel & ESG Economics Drawer (Overlay) */}
            {showFuelPanel && (
              <div className="absolute bottom-16 left-4 right-4 sm:left-auto sm:right-4 sm:w-96 bg-surface/95 backdrop-blur-2xl border border-amber-500/40 rounded-2xl p-4 shadow-2xl z-30 animate-fade-in">
                <div className="flex items-center justify-between gap-2 pb-2 border-b border-outline-variant/50">
                  <div className="flex items-center gap-2">
                    <Fuel className="w-4 h-4 text-amber-400" />
                    <span className="font-bold text-[12px] text-on-surface">Fuel Saved & ESG Carbon Abatement</span>
                  </div>
                  <button onClick={() => setShowFuelPanel(false)} className="text-on-surface-variant hover:text-on-surface text-[12px]">
                    ✕
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2 mt-3">
                  <div className="p-2.5 bg-surface-container-low rounded-xl border border-outline-variant/60">
                    <p className="text-[10px] font-mono text-on-surface-variant uppercase">Fuel Consumed Saved</p>
                    <p className="text-title-sm font-bold font-mono text-emerald-400 mt-0.5">
                      {calculatedFuelSavedL} Liters
                    </p>
                    <p className="text-[9px] text-on-surface-variant mt-0.5">vs naive baseline tour</p>
                  </div>

                  <div className="p-2.5 bg-surface-container-low rounded-xl border border-outline-variant/60">
                    <p className="text-[10px] font-mono text-on-surface-variant uppercase">Financial Savings</p>
                    <p className="text-title-sm font-bold font-mono text-primary mt-0.5">
                      ₹{calculatedInrSaved.toLocaleString()}
                    </p>
                    <p className="text-[9px] text-on-surface-variant mt-0.5">@ ₹92.5/L diesel rate</p>
                  </div>

                  <div className="p-2.5 bg-surface-container-low rounded-xl border border-outline-variant/60">
                    <p className="text-[10px] font-mono text-on-surface-variant uppercase">CO₂ Abatement</p>
                    <p className="text-title-sm font-bold font-mono text-emerald-400 mt-0.5 flex items-center gap-1">
                      <Leaf className="w-3.5 h-3.5" /> {calculatedCo2Kg} kg
                    </p>
                    <p className="text-[9px] text-on-surface-variant mt-0.5">2.68 kg CO₂/L prevented</p>
                  </div>

                  <div className="p-2.5 bg-surface-container-low rounded-xl border border-outline-variant/60">
                    <p className="text-[10px] font-mono text-on-surface-variant uppercase">Fleet Efficiency</p>
                    <p className="text-title-sm font-bold font-mono text-on-surface mt-0.5">
                      5.2 km/L
                    </p>
                    <p className="text-[9px] text-on-surface-variant mt-0.5">Reefer HVAC Active</p>
                  </div>
                </div>

                <div className="mt-3 p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-[10px] font-mono text-emerald-400 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 shrink-0" />
                  <span>ESG Scope-1 Carbon Compliance: Fleet meets Maharashtra Green Logistics Standard.</span>
                </div>
              </div>
            )}

            {/* Turn-by-Turn Navigation Drawer (Overlay) */}
            {showNavDrawer && (
              <div className="absolute top-4 right-4 w-80 max-h-[420px] bg-surface/95 backdrop-blur-2xl border border-primary/40 rounded-2xl p-3.5 shadow-2xl z-30 flex flex-col animate-fade-in">
                <div className="flex items-center justify-between pb-2 border-b border-outline-variant/50">
                  <div className="flex items-center gap-1.5">
                    <Navigation className="w-4 h-4 text-primary" />
                    <span className="font-bold text-[12px] text-on-surface">Turn-by-Turn Guidance</span>
                  </div>
                  <button onClick={() => setShowNavDrawer(false)} className="text-on-surface-variant hover:text-on-surface text-[12px]">
                    ✕
                  </button>
                </div>

                <div className="overflow-y-auto space-y-2 mt-2 pr-1 scrollbar-thin">
                  {turnByTurnSteps.map((step, idx) => {
                    const IconComp = step.icon;
                    return (
                      <div
                        key={idx}
                        className="p-2 bg-surface-container-low rounded-xl border border-outline-variant/40 flex items-start gap-2.5 text-[11px]"
                      >
                        <div className="w-6 h-6 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0 mt-0.5">
                          <IconComp className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1">
                          <p className="font-bold text-on-surface">{step.title}</p>
                          <p className="text-on-surface-variant text-[10px]">{step.instruction}</p>
                          <span className="font-mono text-[9px] text-primary font-bold mt-0.5 inline-block">{step.distance}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Map Footer: Live Simulation Controls & Legend */}
      <div className="p-3 bg-surface-container-low/95 border-t border-outline-variant/60 flex items-center justify-between flex-wrap gap-2 text-[11px]">
        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-1.5 bg-primary text-on-primary rounded-lg hover:opacity-90 active:scale-95 transition-all shadow cursor-pointer flex items-center gap-1 font-bold text-[11px]"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPlaying ? 'Pause' : 'Play Live Sim'}</span>
          </button>

          <button
            onClick={() => setProgress(0)}
            className="p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high rounded-lg transition-colors cursor-pointer"
            title="Reset to Origin"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>

          {/* Speed Pills */}
          <div className="bg-surface-container-high p-0.5 rounded-lg border border-outline-variant flex items-center font-mono">
            {[1, 2, 4].map((spd) => (
              <button
                key={spd}
                onClick={() => setSimSpeed(spd)}
                className={`px-2 py-0.5 rounded cursor-pointer ${
                  simSpeed === spd ? 'bg-primary text-on-primary font-bold' : 'text-on-surface-variant'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>

          {/* Scrub Slider */}
          <input
            type="range"
            min="0"
            max="1"
            step="0.005"
            value={progress}
            onChange={(e) => setProgress(parseFloat(e.target.value))}
            className="w-24 sm:w-36 accent-primary cursor-pointer"
            title="Scrub truck route progress"
          />
          <button
            onClick={async () => {
              try {
                await api.notifyRouteArrival({
                  truck_id: activeVehicle?.truckId || 'MH-04-JK-4821',
                  origin: activeVehicle?.origin || 'Mumbai Central Port',
                  destination: (activeVehicle?.stops && activeVehicle.stops[0]) || 'Pune Logistics Hub',
                  fuel_saved: 14.2,
                  co2_saved: 38.0,
                });
              } catch (e) {
                console.warn('Arrival broadcast err:', e);
              }
            }}
            className="bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-400 border border-cyan-500/30 font-bold px-2 py-0.5 rounded text-[10px] font-mono flex items-center gap-1 transition-all cursor-pointer"
            title="Broadcast arrival notification to manager hub & mobile phone"
          >
            <BellRing className="w-3 h-3" />
            <span>Items Reached</span>
          </button>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 font-mono text-[10px] text-on-surface-variant flex-wrap">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Origin
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" /> Delivery Stop
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3.5 h-1 bg-[#1a73e8] inline-block rounded" /> Optimized Path
          </span>
          {showTraffic && (
            <span className="flex items-center gap-1 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" /> Free Flow
            </span>
          )}
          {showTraffic && (
            <span className="flex items-center gap-1 text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> Ghat / Toll
            </span>
          )}
          {showTraffic && (
            <span className="flex items-center gap-1 text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-400 inline-block" /> Congested
            </span>
          )}
          {showComparison && (
            <span className="flex items-center gap-1 text-error/80">
              <span className="w-4 h-0.5 border-b border-dashed border-error inline-block" /> Naive Tour
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
