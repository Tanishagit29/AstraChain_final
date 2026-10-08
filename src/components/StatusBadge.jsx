import React from 'react';

export default function StatusBadge({ status }) {
  const getBadgeStyle = () => {
    switch (status?.toUpperCase()) {
      case 'HIGH':
      case 'CRITICAL':
      case 'DELAYED':
        return 'bg-error/10 text-error border-error/20';
      case 'HEALTHY':
      case 'LOW':
      case 'OPTIMAL':
      case 'ACTIVE':
      case 'VERIFIED':
        return 'bg-primary/10 text-primary border-primary/20';
      case 'OVERSTOCK':
      case 'WARNING':
      case 'MEDIUM':
      case 'UNDER_REVIEW':
        return 'bg-tertiary/10 text-tertiary border-tertiary/20';
      case 'IN_TRANSIT':
      case 'REROUTED':
      case 'AI_REROUTED':
        return 'bg-secondary/10 text-secondary border-secondary/20';
      default:
        return 'bg-surface-variant text-on-surface-variant border-outline-variant';
    }
  };

  return (
    <span
      className={`px-3 py-1 rounded-full text-label-sm font-bold border ${getBadgeStyle()}`}
    >
      {status}
    </span>
  );
}
