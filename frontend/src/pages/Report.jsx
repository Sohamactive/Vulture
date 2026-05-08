import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import ReportCard from '../components/report/ReportCard';
import SeverityDonut from '../components/report/SeverityDonut';
import OWASPRadar from '../components/report/OWASPRadar';
import IssueList from '../components/report/IssueList';
import GlitchText from '../components/ui/GlitchText';
import { useScanStore } from '../store/scanStore';
import { getReport, exportReport } from '../lib/api';
import { useAuthToken } from '../lib/useAuthToken';
import { mapReport } from '../lib/reportMapper';
import { FileDown } from 'lucide-react';

export default function Report() {
  const { scanId } = useParams();
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

  const handleExport = async (format) => {
    const token = await getToken();
    if (!token) return;

    try {
      const data = await exportReport(token, scanId, format);
      let blob;
      let fileName;

      if (format === 'docx' && data?.content_base64) {
        const byteCharacters = atob(data.content_base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i += 1) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        blob = new Blob([byteArray], { type: data.mime_type || 'application/octet-stream' });
        fileName = data.filename || `vulture-report-${scanId}.docx`;
      } else {
        blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        fileName = `vulture-report-${scanId}.json`;
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export report:', err);
    }
  };

  const activeReport = report;

  if (!activeReport) {
    return (
      <div className="min-h-screen flex items-center justify-center font-mono">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-[var(--cyan)] border-t-transparent rounded-full animate-spin"></div>
          <span className="text-[var(--text-dim)]">Loading report data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen pt-12 pb-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="mb-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <motion.h1 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-3xl font-bold mb-2 flex items-center gap-4"
            >
              <GlitchText text="Vulnerability Report" />
              <span className="text-sm font-normal text-[var(--text-dim)] border border-[var(--border)] px-3 py-1 rounded-full uppercase tracking-widest">
                ID: {activeReport.scan_id}
              </span>
            </motion.h1>
            <p className="text-[var(--text-dim)] uppercase tracking-widest text-sm">Generated on {new Date().toLocaleDateString()}</p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('docx')}
              className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase border border-[var(--border)] px-4 py-2 hover:border-[var(--cyan)]"
            >
              <FileDown size={16} /> Download DOCX
            </button>
            <button
              onClick={() => handleExport('json')}
              className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase border border-[var(--border)] px-4 py-2 hover:border-[var(--cyan)]"
            >
              <FileDown size={16} /> Export JSON
            </button>
          </div>
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
    </div>
  );
}
