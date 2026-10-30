import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle({ 
  showLabel = true, 
  variant = 'button', // 'button' | 'segmented'
  className = '' 
}) {
  const { theme, isDark, toggleTheme, setTheme } = useTheme();

  if (variant === 'segmented') {
    return (
      <div 
        className={`inline-flex items-center p-1 bg-surface-container-low border border-outline-variant rounded-full gap-1 shadow-inner select-none ${className}`}
        role="group"
        aria-label="Theme selector"
      >
        <button
          type="button"
          onClick={() => setTheme('light')}
          aria-label="Switch to Light mode"
          title="Light Mode"
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium transition-all duration-200 cursor-pointer ${
            !isDark 
              ? 'bg-amber-400/20 text-amber-500 font-bold shadow-sm border border-amber-400/30' 
              : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
          }`}
        >
          <Sun className="w-3.5 h-3.5 transition-transform duration-200 hover:rotate-45" />
          {showLabel && <span>Light</span>}
        </button>

        <button
          type="button"
          onClick={() => setTheme('dark')}
          aria-label="Switch to Dark mode"
          title="Dark Mode"
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium transition-all duration-200 cursor-pointer ${
            isDark 
              ? 'bg-primary/20 text-primary font-bold shadow-sm border border-primary/30' 
              : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
          }`}
        >
          <Moon className="w-3.5 h-3.5 transition-transform duration-200 hover:-rotate-12" />
          {showLabel && <span>Dark</span>}
        </button>
      </div>
    );
  }

  const buttonClasses = showLabel
    ? `group relative flex items-center gap-2 px-3 py-1.5 rounded-full border border-outline-variant bg-surface hover:bg-surface-variant transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/40 shadow-sm cursor-pointer select-none active:scale-95 ${className}`
    : `group relative w-10 h-10 flex items-center justify-center rounded-full border border-outline-variant bg-surface hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/40 shadow-sm cursor-pointer select-none active:scale-95 ${className}`;

  const iconClasses = showLabel ? 'w-4 h-4' : 'w-5 h-5';

  return (
    <button
      onClick={toggleTheme}
      type="button"
      aria-label={`Current theme: ${theme}. Click to switch to ${isDark ? 'light' : 'dark'} mode`}
      title={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
      className={buttonClasses}
    >
      <div className="relative flex items-center justify-center">
        {isDark ? (
          <Moon className={`${iconClasses} text-primary group-hover:-rotate-12 transition-transform duration-300`} />
        ) : (
          <Sun className={`${iconClasses} text-amber-500 group-hover:rotate-45 transition-transform duration-300`} />
        )}
      </div>

      {showLabel && (
        <span className="text-label-sm font-bold font-mono text-on-surface uppercase tracking-wider text-[11px]">
          {isDark ? 'Dark' : 'Light'}
        </span>
      )}
    </button>
  );
}
