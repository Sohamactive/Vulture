import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import ReportCard from './ReportCard';
import SeverityDonut from './SeverityDonut';
import OWASPRadar from './OWASPRadar';
import IssueList from './IssueList';
import GlitchText from '../ui/GlitchText';
import { useScanStore } from '../../store/scanStore';
import { getReport } from '../../lib/api';
import { useAuthToken } from '../../lib/useAuthToken';
import { mapReport } from '../../lib/reportMapper';

export default function ReportView({ scanId = 'demo-123' }) {
  const { report, setReport } = useScanStore();
  const { getToken } = useAuthToken();

  useEffect(() => {
    if (!scanId || report?.scan_id === scanId) return;

    let cancelled = false;

    (async () => {
      const token = await getToken();
      if (!token || cancelled) return;

      try {
        const data = await getReport(token, scanId);
        if (!cancelled) setReport(mapReport(data));
      } catch (err) {
        console.error('Failed to fetch report:', err);
      }
    })();

    return () => { cancelled = true; };
  }, [scanId, report, setReport, getToken]);

  const activeReport = report;

  if (!activeReport) {
    return (
      <div className="min-h-[400px] flex items-center justify-center font-mono">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-[var(--cyan)] border-t-transparent rounded-full animate-spin"></div>
          <span className="text-[var(--text-dim)]">Loading report data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="mb-8 border-b border-[var(--border)] pb-8">
        <motion.h2 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-3xl font-bold mb-2 flex items-center gap-4"
        >
          <GlitchText text="Vulnerability Report" />
          <span className="text-sm font-normal text-[var(--text-dim)] border border-[var(--border)] px-3 py-1 rounded-full uppercase tracking-widest">
            ID: {activeReport.scan_id}
          </span>
        </motion.h2>
        <p className="text-[var(--text-dim)] uppercase tracking-widest text-sm">Generated on {new Date().toLocaleDateString()}</p>
      </div>

      <motion.div 
        className="grid grid-cols-1 mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <ReportCard summary={activeReport.summary} />
      </motion.div>

      <motion.div 
        className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <SeverityDonut summary={activeReport.summary} />
        <OWASPRadar scores={activeReport.owasp_scores} />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <IssueList issues={activeReport.issues} />
      </motion.div>
    </div>
  );
}
