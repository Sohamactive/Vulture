import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts';

export default function OWASPRadar({ scores }) {
  // Map raw scores object to array format needed by Recharts
  // Fallback to default 0s if no scores provided
  const rawScores = scores || {};
  
  const data = [
    { subject: 'A01 Access', A: rawScores['A01'] || 0 },
    { subject: 'A02 Crypto', A: rawScores['A02'] || 0 },
    { subject: 'A03 Inject', A: rawScores['A03'] || 0 },
    { subject: 'A04 Design', A: rawScores['A04'] || 0 },
    { subject: 'A05 Config', A: rawScores['A05'] || 0 },
    { subject: 'A06 Outdated', A: rawScores['A06'] || 0 },
    { subject: 'A07 Auth', A: rawScores['A07'] || 0 },
    { subject: 'A08 Integrity', A: rawScores['A08'] || 0 },
    { subject: 'A09 Logging', A: rawScores['A09'] || 0 },
    { subject: 'A10 SSRF', A: rawScores['A10'] || 0 },
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[var(--bg-panel)] border border-[var(--border)] p-3 font-mono text-sm shadow-[0_0_15px_rgba(0,0,0,0.5)]">
          <p className="font-bold text-[var(--cyan)] mb-1">
            {payload[0].payload.subject}
          </p>
          <p className="text-[var(--text-primary)]">
            {`Issues: ${payload[0].value}`}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-6 h-full flex flex-col">
      <h3 className="text-sm font-bold uppercase tracking-widest text-[var(--text-dim)] mb-4">OWASP Top 10 Coverage</h3>
      <div className="flex-grow w-full h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis 
              dataKey="subject" 
              tick={{ fill: 'var(--text-dim)', fontSize: 10, fontFamily: 'monospace' }} 
            />
            <Radar 
              name="Issues" 
              dataKey="A" 
              stroke="var(--cyan)" 
              fill="var(--cyan)" 
              fillOpacity={0.4} 
            />
            <Tooltip content={<CustomTooltip />} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
