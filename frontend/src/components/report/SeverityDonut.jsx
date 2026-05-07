import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

export default function SeverityDonut({ summary }) {
  const { critical = 0, high = 0, medium = 0, low = 0 } = summary || {};
  
  const data = [
    { name: 'Critical', value: critical },
    { name: 'High', value: high },
    { name: 'Medium', value: medium },
    { name: 'Low', value: low }
  ].filter(item => item.value > 0);

  const COLORS = {
    'Critical': 'var(--red)',
    'High': 'var(--high-sev)',
    'Medium': 'var(--amber)',
    'Low': 'var(--cyan)'
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[var(--bg-panel)] border border-[var(--border)] p-3 font-mono text-sm shadow-[0_0_15px_rgba(0,0,0,0.5)]">
          <p className="font-bold mb-1" style={{ color: payload[0].payload.fill }}>
            {`${payload[0].name} Severity`}
          </p>
          <p className="text-[var(--text-primary)]">
            {`Issues: ${payload[0].value}`}
          </p>
        </div>
      );
    }
    return null;
  };

  if (data.length === 0) {
    return (
      <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-6 h-full flex items-center justify-center">
        <p className="text-[var(--text-dim)] font-mono">No vulnerabilities found</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-6 h-full flex flex-col">
      <h3 className="text-sm font-bold uppercase tracking-widest text-[var(--text-dim)] mb-4">Severity Distribution</h3>
      <div className="flex-grow w-full h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie 
              data={data} 
              innerRadius={70} 
              outerRadius={100} 
              paddingAngle={2}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
