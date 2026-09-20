import React from 'react';
import { Calendar, Zap, Download, Sparkles } from 'lucide-react';

export default function PageHeader({ title, subtitle, actions }) {
  return (
    <section className="flex flex-col md:flex-row md:items-end justify-between gap-md mb-lg">
      <div className="space-y-xs">
        <h2 className="font-headline-lg text-headline-lg text-on-surface tracking-tight font-bold">
          {title}
        </h2>
        {subtitle && (
          <p className="text-on-surface-variant font-body-lg text-body-lg">
            {subtitle}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex gap-sm flex-wrap">
          {actions}
        </div>
      )}
    </section>
  );
}
