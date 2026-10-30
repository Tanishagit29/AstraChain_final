import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  TrendingUp, 
  Boxes, 
  Trash2, 
  Settings, 
  User,
  Database,
  Route as RouteIcon
} from 'lucide-react';

const navItems = [
  { path: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { path: '/data-collection', label: 'Data Ingestion', icon: Database },
  { path: '/forecast', label: 'Demand Forecast', icon: TrendingUp },
  { path: '/inventory', label: 'Inventory Analysis', icon: Boxes },
  { path: '/routes', label: 'Route Optimization', icon: RouteIcon },
  { path: '/wastage', label: 'Wastage Control', icon: Trash2 },
];

export default function Sidebar() {
  return (
    <>
      {/* Desktop Side Navigation Shell */}
      <aside className="fixed left-0 top-0 h-full w-[280px] border-r border-outline-variant bg-background flex flex-col py-lg z-[60] hidden md:flex">
        {/* Brand Header */}
        <div className="px-lg mb-xl">
          <div className="flex items-center gap-md">
            <div className="w-10 h-10 bg-primary-container rounded-lg flex items-center justify-center shadow-lg shadow-primary/20">
              <span className="material-symbols-outlined text-on-primary-container font-black" style={{ fontVariationSettings: "'FILL' 1" }}>
                transit_enterexit
              </span>
            </div>
            <div>
              <h1 className="text-title-md font-bold text-primary leading-tight tracking-tight">AstraChain</h1>
              <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">Autonomous Pipeline</p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-md space-y-xs custom-scrollbar overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-md px-md py-sm rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-secondary-container text-on-secondary-container border-l-2 border-primary font-bold shadow-md'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50'
                  }`
                }
              >
                <Icon className="w-5 h-5 shrink-0" />
                <span className="font-label-md text-label-md">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom Utility Links */}
        <div className="mt-auto px-md space-y-xs pt-lg border-t border-outline-variant/30">
          <button className="w-full flex items-center gap-md px-md py-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-colors rounded-lg text-left cursor-pointer">
            <Settings className="w-5 h-5" />
            <span className="font-label-md text-label-md">Settings</span>
          </button>
          <button className="w-full flex items-center gap-md px-md py-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-colors rounded-lg text-left cursor-pointer">
            <User className="w-5 h-5" />
            <span className="font-label-md text-label-md">Profile</span>
          </button>
        </div>
      </aside>

      {/* Mobile Bottom Navigation Shell */}
      <nav className="fixed bottom-0 left-0 right-0 h-16 bg-surface/90 backdrop-blur-xl border-t border-outline-variant flex justify-around items-center md:hidden z-50 px-xs">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex flex-col items-center gap-1 ${
                  isActive ? 'text-primary font-bold' : 'text-on-surface-variant'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-label-sm">{item.label.split(' ')[0]}</span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}
