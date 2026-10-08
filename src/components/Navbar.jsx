import React, { useState } from 'react';
import { Search, Bell, Radio, HelpCircle } from 'lucide-react';

export default function Navbar() {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="flex justify-between items-center h-16 px-lg sticky top-0 z-50 bg-surface/80 backdrop-blur-xl border-b border-outline-variant shadow-sm">
      {/* Global Search Field */}
      <div className="flex items-center gap-lg">
        <div className="relative w-72 sm:w-96 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant group-focus-within:text-primary transition-colors" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search operations, assets, or agents..."
            className="w-full bg-surface-container-low border border-outline-variant rounded-full pl-10 pr-4 py-2 text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
          />
        </div>
      </div>

      {/* Right Controls & Profile */}
      <div className="flex items-center gap-md">
        <button className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high rounded-full transition-all relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full animate-pulse" />
        </button>

        <button className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high rounded-full transition-all">
          <Radio className="w-5 h-5 text-primary" />
        </button>

        <button className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high rounded-full transition-all">
          <HelpCircle className="w-5 h-5" />
        </button>

        <div className="h-8 w-px bg-outline-variant mx-xs hidden sm:block" />

        <div className="flex items-center gap-sm">
          <div className="text-right hidden sm:block">
            <p className="font-body-md text-body-md font-bold text-on-surface">Daksh Mehta</p>
            <p className="font-label-sm text-label-sm text-on-surface-variant">Operations Lead</p>
          </div>
          <img
            src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"
            alt="Daksh Mehta Profile"
            className="w-10 h-10 rounded-full border border-primary-container object-cover"
          />
        </div>
      </div>
    </header>
  );
}
