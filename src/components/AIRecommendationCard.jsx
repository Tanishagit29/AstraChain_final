import React from 'react';
import { Sparkles, ArrowRight } from 'lucide-react';

export default function AIRecommendationCard({ recommendation, onExecute }) {
  const { product, riskText, actionText, actionClass, type } = recommendation;

  return (
    <div className="p-md rounded-lg glass-card ai-border flex gap-md items-start">
      <div className="w-10 h-10 rounded-lg bg-primary-container/20 flex items-center justify-center shrink-0 border border-primary/30">
        <Sparkles className="w-5 h-5 text-primary" />
      </div>

      <div className="flex-1">
        <h5 className="font-body-md text-body-md font-bold text-on-surface mb-xs">{product}</h5>
        <p className="font-label-sm text-label-sm text-on-surface-variant mb-sm">{riskText}</p>

        <button
          onClick={() => onExecute && onExecute(recommendation)}
          className={`mt-xs w-full py-xs rounded font-label-md text-label-md transition-all flex items-center justify-center gap-xs font-bold ${
            actionClass || 'bg-primary text-on-primary hover:opacity-90'
          }`}
        >
          <span>{actionText}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
