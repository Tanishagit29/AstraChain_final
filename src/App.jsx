import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import LiveToastContainer from './components/LiveToastContainer';
import { NotificationProvider } from './context/NotificationContext';

import Dashboard from './pages/Dashboard';
import DataIntelligenceAgent from './pages/DataIntelligenceAgent';
import DemandForecast from './pages/DemandForecast';
import InventoryIntelligence from './pages/InventoryIntelligence';
import WastageManagement from './pages/WastageManagement';
import RouteOptimization from './pages/RouteOptimization';

export default function App() {
  return (
    <NotificationProvider>
      <div className="min-h-screen bg-[var(--bg-main,#0B1120)] text-[var(--text-main,#dee3e8)] flex flex-col font-sans transition-colors duration-200">
        {/* Floating Live Real-Time Toast Notifications */}
        <LiveToastContainer />

        {/* Side Navigation */}
        <Sidebar />

        {/* Main Content Body */}
        <div className="flex-1 md:ml-[280px] min-h-screen flex flex-col">
          {/* Top Navbar */}
          <Navbar />

          {/* Dynamic Page Router Canvas */}
          <main className="flex-1 px-lg pt-lg pb-2xl">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/data-collection" element={<DataIntelligenceAgent />} />
              <Route path="/forecast" element={<DemandForecast />} />
              <Route path="/inventory" element={<InventoryIntelligence />} />
              <Route path="/routes" element={<RouteOptimization />} />
              <Route path="/wastage" element={<WastageManagement />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </NotificationProvider>
  );
}
