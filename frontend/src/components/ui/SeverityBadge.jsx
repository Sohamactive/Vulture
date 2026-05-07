import React from 'react';

const config = {
  critical: { label: 'CRITICAL', color: 'var(--red)', icon: '●', className: 'badge-critical text-[var(--red)]' },
  high:     { label: 'HIGH',     color: 'var(--high-sev)', icon: '●', className: 'badge-high text-[var(--high-sev)]' },
  medium:   { label: 'MEDIUM',   color: 'var(--amber)', icon: '●', className: 'badge-medium text-[var(--amber)]' },
  low:      { label: 'LOW',      color: 'var(--cyan)', icon: '●', className: 'badge-low text-[var(--cyan)]' },
};

export default function SeverityBadge({ level }) {
  const badgeConfig = config[level?.toLowerCase()] || config.low;
  
  return (
    <span 
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border border-solid bg-[var(--bg-surface)] ${badgeConfig.className}`}
    >
      <span className="mr-1.5">{badgeConfig.icon}</span>
      {badgeConfig.label}
    </span>
  );
}
