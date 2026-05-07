import React, { useEffect, useState } from 'react';
import { ShieldAlert, ShieldCheck, Shield, ShieldHalf } from 'lucide-react';

function AnimatedCounter({ value }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const end = parseInt(value, 10);
    if (start === end) return;

    let totalDuration = 1200;
    let incrementTime = (totalDuration / end);
    
    let timer = setInterval(() => {
      start += 1;
      setCount(start);
      if (start === end) clearInterval(timer);
    }, incrementTime);

    return () => clearInterval(timer);
  }, [value]);

  return <span>{count}</span>;
}

export default function ReportCard({ summary }) {
  const { critical = 0, high = 0, medium = 0, low = 0 } = summary || {};
  
  const getGrade = () => {
    if (critical > 5) return 'F';
    if (critical > 0) return 'D';
    if (high > 5) return 'C';
    if (high > 0 || medium > 5) return 'B';
    return 'A';
  };

  const grade = getGrade();
  const total = critical + high + medium + low;

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-6 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute -right-10 -top-10 opacity-5 pointer-events-none">
        <ShieldAlert size={200} />
      </div>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8">
        <div>
          <h2 className="text-2xl font-bold uppercase tracking-widest text-[var(--text-primary)]">Security Audit Grade</h2>
          <p className="text-[var(--text-dim)]">Based on CVSS scores and OWASP impact</p>
        </div>
        
        <div className={`text-6xl font-black mt-4 md:mt-0 ${
          grade === 'A' ? 'text-[var(--green)]' : 
          grade === 'B' ? 'text-[var(--cyan)]' : 
          grade === 'C' ? 'text-[var(--amber)]' : 
          grade === 'D' ? 'text-[var(--high-sev)]' : 
          'text-[var(--red)]'
        } drop-shadow-[0_0_15px_currentColor]`}>
          {grade}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className={`p-4 border ${critical > 0 ? 'border-[var(--red)] bg-[#ff2d5511] shadow-[var(--glow-red)] pulse-ring-container' : 'border-[var(--border)] bg-[var(--bg-panel)]'}`}>
          <div className="text-[var(--red)] text-xs font-bold tracking-widest uppercase mb-2 flex items-center gap-2">
            <ShieldAlert size={14} /> Critical
          </div>
          <div className="text-4xl font-bold text-[var(--red)]"><AnimatedCounter value={critical} /></div>
        </div>

        <div className="p-4 border border-[var(--border)] bg-[var(--bg-panel)]">
          <div className="text-[var(--high-sev)] text-xs font-bold tracking-widest uppercase mb-2 flex items-center gap-2">
            <ShieldHalf size={14} /> High
          </div>
          <div className="text-4xl font-bold text-[var(--high-sev)]"><AnimatedCounter value={high} /></div>
        </div>

        <div className="p-4 border border-[var(--border)] bg-[var(--bg-panel)]">
          <div className="text-[var(--amber)] text-xs font-bold tracking-widest uppercase mb-2 flex items-center gap-2">
            <Shield size={14} /> Medium
          </div>
          <div className="text-4xl font-bold text-[var(--amber)]"><AnimatedCounter value={medium} /></div>
        </div>

        <div className="p-4 border border-[var(--border)] bg-[var(--bg-panel)]">
          <div className="text-[var(--cyan)] text-xs font-bold tracking-widest uppercase mb-2 flex items-center gap-2">
            <ShieldCheck size={14} /> Low
          </div>
          <div className="text-4xl font-bold text-[var(--cyan)]"><AnimatedCounter value={low} /></div>
        </div>
      </div>
    </div>
  );
}
