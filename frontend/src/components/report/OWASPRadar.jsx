import { useMemo } from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip
} from 'recharts';

const OWASP_AXES = [
  { key: 'A01', label: 'Access Control' },
  { key: 'A02', label: 'Crypto Failures' },
  { key: 'A03', label: 'Injection' },
  { key: 'A04', label: 'Insecure Design' },
  { key: 'A05', label: 'Misconfiguration' },
  { key: 'A06', label: 'Outdated Components' },
  { key: 'A07', label: 'Auth Failures' },
  { key: 'A08', label: 'Integrity Failures' },
  { key: 'A09', label: 'Logging & Monitor' },
  { key: 'A10', label: 'SSRF' },
];

function getDomainMax(maxValue) {
  if (maxValue <= 1) return 2;
  if (maxValue <= 3) return 4;
  if (maxValue <= 6) return 8;
  if (maxValue <= 12) return 15;
  return Math.ceil(maxValue / 10) * 10;
}

function OwaspTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;

  return (
    <div className="bg-[var(--bg-panel)] border border-[var(--border)] p-3 font-mono text-xs shadow-[0_0_20px_rgba(0,0,0,0.45)]">
      <p className="font-bold text-[var(--cyan)] mb-1">{row.code} {row.label}</p>
      <p className="text-[var(--text-primary)]">Findings: {row.value}</p>
    </div>
  );
}

export default function OWASPRadar({ scores }) {
  const chartState = useMemo(() => {
    const rawScores = scores || {};
    const values = OWASP_AXES.map((axis) => {
      const count = Number(rawScores[axis.key] || 0);
      return {
        code: axis.key,
        label: axis.label,
        shortLabel: axis.key,
        value: Number.isFinite(count) ? Math.max(0, count) : 0
      };
    });

    const totalIssues = values.reduce((sum, item) => sum + item.value, 0);
    const coveredCategories = values.filter((item) => item.value > 0).length;
    const maxValue = values.reduce((max, item) => Math.max(max, item.value), 0);
    const domainMax = getDomainMax(maxValue);

    return {
      values: values.map((item) => ({ ...item, baseline: domainMax })),
      totalIssues,
      coveredCategories,
      domainMax,
      hasCoverage: totalIssues > 0
    };
  }, [scores]);

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-6 h-full flex flex-col overflow-hidden relative">
      <div className="pointer-events-none absolute right-[-80px] top-[-100px] w-56 h-56 rounded-full bg-[radial-gradient(circle,rgba(0,245,255,0.18),transparent_65%)]" />

      <div className="relative flex items-start justify-between mb-4 gap-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-widest text-[var(--text-dim)]">OWASP Top 10 Coverage</h3>
          <p className="text-xs text-[var(--text-dim)] mt-1">Category footprint from current scan report.</p>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold text-[var(--cyan)] leading-none">{chartState.coveredCategories}/10</div>
          <div className="text-[10px] uppercase tracking-widest text-[var(--text-dim)]">Categories Hit</div>
        </div>
      </div>

      {!chartState.hasCoverage ? (
        <div className="flex-1 flex items-center justify-center border border-dashed border-[var(--border)] bg-[var(--bg-panel)]">
          <p className="text-[var(--text-dim)] text-sm font-mono">No OWASP category signals in this scan.</p>
        </div>
      ) : (
        <>
          <div className="relative flex-grow w-full h-[280px]">
            <ResponsiveContainer width="100%" height="100%" minWidth={280} debounce={180}>
              <RadarChart
                data={chartState.values}
                cx="50%"
                cy="52%"
                outerRadius="73%"
                margin={{ top: 8, right: 14, bottom: 8, left: 14 }}
              >
                <PolarGrid stroke="var(--border)" strokeOpacity={0.75} />
                <PolarAngleAxis
                  dataKey="shortLabel"
                  tick={{ fill: 'var(--text-dim)', fontSize: 11, fontFamily: 'Share Tech Mono, monospace' }}
                />
                <PolarRadiusAxis
                  axisLine={false}
                  tick={false}
                  domain={[0, chartState.domainMax]}
                  tickCount={5}
                />
                <Radar
                  dataKey="baseline"
                  stroke="none"
                  fill="var(--cyan)"
                  fillOpacity={0.04}
                  isAnimationActive={false}
                />
                <Radar
                  name="Findings"
                  dataKey="value"
                  stroke="var(--cyan)"
                  strokeWidth={2}
                  fill="var(--cyan)"
                  fillOpacity={0.35}
                  isAnimationActive={false}
                />
                <Tooltip cursor={false} content={<OwaspTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
            {chartState.values.map((item) => (
              <div
                key={item.code}
                className="border border-[var(--border)] bg-[var(--bg-panel)] px-2.5 py-2 text-[10px] font-mono text-[var(--text-dim)]"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="uppercase">{item.code}</span>
                  <span className={`font-bold ${item.value > 0 ? 'text-[var(--cyan)]' : 'text-[var(--text-dim)]'}`}>
                    {item.value}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
