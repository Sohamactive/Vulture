import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, ShieldAlert, ShieldCheck, Clock, ArrowRight, RefreshCw, Plus, GitBranch, Activity } from 'lucide-react';
import GlitchText from '../components/ui/GlitchText';
import SeverityBadge from '../components/ui/SeverityBadge';
import { getScanHistory, rerunScan } from '../lib/api';
import { useAuthToken } from '../lib/useAuthToken';
import { useScanStore } from '../store/scanStore';

function StatusBadge({ status }) {
  const styles = {
    completed: 'text-[var(--green)] border-[var(--green)] bg-[#00ff8711]',
    failed: 'text-[var(--red)] border-[var(--red)] bg-[#ff2d5511]',
    pending: 'text-[var(--amber)] border-[var(--amber)] bg-[#ffaa0011]',
    cloning: 'text-[var(--cyan)] border-[var(--cyan)] bg-[#00f5ff11]',
    semgrep_scanning: 'text-[var(--cyan)] border-[var(--cyan)] bg-[#00f5ff11]',
    parsing: 'text-[var(--cyan)] border-[var(--cyan)] bg-[#00f5ff11]',
    analyzing: 'text-[var(--amber)] border-[var(--amber)] bg-[#ffaa0011]',
  };

  const labels = {
    completed: 'Completed',
    failed: 'Failed',
    pending: 'Pending',
    cloning: 'Cloning',
    semgrep_scanning: 'Scanning',
    parsing: 'Parsing',
    analyzing: 'Analyzing',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest border px-2 py-0.5 ${styles[status] || styles.pending}`}>
      {['cloning', 'parsing', 'analyzing', 'semgrep_scanning', 'pending'].includes(status) && (
        <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"></span>
      )}
      {labels[status] || status}
    </span>
  );
}

function SeveritySummaryBar({ summary }) {
  if (!summary) return null;
  const { critical = 0, high = 0, medium = 0, low = 0 } = summary;
  const total = critical + high + medium + low;
  if (total === 0) return <span className="text-[var(--text-dim)] text-xs">No issues found</span>;

  return (
    <div className="flex items-center gap-3 text-xs font-mono">
      {critical > 0 && <span className="text-[var(--red)] font-bold">{critical} CRIT</span>}
      {high > 0 && <span className="text-[var(--high-sev)] font-bold">{high} HIGH</span>}
      {medium > 0 && <span className="text-[var(--amber)]">{medium} MED</span>}
      {low > 0 && <span className="text-[var(--cyan)]">{low} LOW</span>}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { getToken } = useAuthToken();
  const { scanHistory, setScanHistory, loadingScanHistory, setLoadingScanHistory } = useScanStore();
  const [rerunningId, setRerunningId] = useState(null);

  const fetchHistory = async () => {
    setLoadingScanHistory(true);
    try {
      const token = await getToken();
      if (!token) return;
      const data = await getScanHistory(token);
      setScanHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch scan history:', err);
    } finally {
      setLoadingScanHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleRerun = async (e, scanId) => {
    e.stopPropagation();
    setRerunningId(scanId);
    try {
      const token = await getToken();
      if (!token) return;
      await rerunScan(token, scanId);
      // Refresh the history
      await fetchHistory();
    } catch (err) {
      console.error('Failed to rerun scan:', err);
    } finally {
      setRerunningId(null);
    }
  };

  const handleViewReport = (scan) => {
    if (scan.status === 'completed') {
      navigate(`/report/${scan.id}`);
    }
  };

  // Stats from history
  const totalScans = scanHistory.length;
  const completedScans = scanHistory.filter(s => s.status === 'completed').length;
  const totalVulns = scanHistory.reduce((sum, s) => {
    if (!s.summary) return sum;
    return sum + (s.summary.critical || 0) + (s.summary.high || 0) + (s.summary.medium || 0) + (s.summary.low || 0);
  }, 0);
  const avgScore = completedScans > 0
    ? Math.round(scanHistory.filter(s => s.security_score != null).reduce((sum, s) => sum + s.security_score, 0) / completedScans)
    : null;

  return (
    <div className="relative min-h-screen pt-12 pb-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-10">
          <div>
            <motion.h1
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-3xl md:text-4xl font-bold mb-2"
            >
              <GlitchText text="Security Dashboard" />
            </motion.h1>
            <p className="text-[var(--text-dim)] uppercase tracking-widest text-sm">Scan history & analytics</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchHistory}
              disabled={loadingScanHistory}
              className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase border border-[var(--border)] px-4 py-2 hover:border-[var(--cyan)] disabled:opacity-50"
            >
              <RefreshCw size={14} className={loadingScanHistory ? 'animate-spin' : ''} /> Refresh
            </button>
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-sm font-bold tracking-wider bg-[var(--cyan)] text-black px-4 py-2 hover:shadow-[0_0_20px_var(--color-cyber-cyan)] transition-all"
            >
              <Plus size={14} /> New Scan
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-5">
            <div className="text-xs font-bold uppercase tracking-widest text-[var(--text-dim)] mb-2 flex items-center gap-2">
              <Activity size={14} /> Total Scans
            </div>
            <div className="text-3xl font-bold text-[var(--text-primary)]">{totalScans}</div>
          </div>
          <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-5">
            <div className="text-xs font-bold uppercase tracking-widest text-[var(--text-dim)] mb-2 flex items-center gap-2">
              <ShieldCheck size={14} /> Completed
            </div>
            <div className="text-3xl font-bold text-[var(--green)]">{completedScans}</div>
          </div>
          <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-5">
            <div className="text-xs font-bold uppercase tracking-widest text-[var(--text-dim)] mb-2 flex items-center gap-2">
              <ShieldAlert size={14} /> Total Vulns
            </div>
            <div className="text-3xl font-bold text-[var(--red)]">{totalVulns}</div>
          </div>
          <div className="bg-[var(--bg-surface)] border border-[var(--border)] p-5">
            <div className="text-xs font-bold uppercase tracking-widest text-[var(--text-dim)] mb-2 flex items-center gap-2">
              <Shield size={14} /> Avg Score
            </div>
            <div className="text-3xl font-bold text-[var(--cyan)]">{avgScore != null ? avgScore : '—'}</div>
          </div>
        </motion.div>

        {/* Scan History List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="bg-[var(--bg-surface)] border border-[var(--border)]">
            {/* List Header */}
            <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between">
              <h3 className="text-lg font-bold text-[var(--text-primary)]">Scan History</h3>
              <span className="text-xs text-[var(--text-dim)] font-mono">{totalScans} scans</span>
            </div>

            {/* Loading */}
            {loadingScanHistory && scanHistory.length === 0 && (
              <div className="p-12 flex flex-col items-center gap-4">
                <div className="w-8 h-8 border-2 border-[var(--cyan)] border-t-transparent rounded-full animate-spin"></div>
                <span className="text-[var(--text-dim)] text-sm">Loading scan history...</span>
              </div>
            )}

            {/* Empty State */}
            {!loadingScanHistory && scanHistory.length === 0 && (
              <div className="p-12 flex flex-col items-center gap-4">
                <Shield size={48} className="text-[var(--border)]" />
                <p className="text-[var(--text-dim)] text-center">
                  No scans yet. Start your first security audit!
                </p>
                <button
                  onClick={() => navigate('/')}
                  className="flex items-center gap-2 text-sm font-bold tracking-wider bg-[var(--cyan)] text-black px-6 py-2.5 hover:shadow-[0_0_20px_var(--color-cyber-cyan)] transition-all mt-2"
                >
                  <Plus size={14} /> Start Scanning
                </button>
              </div>
            )}

            {/* Scan Items */}
            {scanHistory.map((scan, index) => (
              <motion.div
                key={scan.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`px-6 py-5 border-b border-[var(--border)] last:border-0 hover:bg-[var(--bg-panel)] transition-colors ${
                  scan.status === 'completed' ? 'cursor-pointer' : ''
                }`}
                onClick={() => handleViewReport(scan)}
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  {/* Left: Repo Info */}
                  <div className="flex-grow min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <GitBranch size={16} className="text-[var(--text-dim)] flex-shrink-0" />
                      <span className="font-bold text-[var(--text-primary)] truncate">{scan.repo_full_name}</span>
                      <StatusBadge status={scan.status} />
                    </div>
                    <div className="flex items-center gap-4 text-xs text-[var(--text-dim)]">
                      <span className="font-mono">{scan.branch}</span>
                      <span>•</span>
                      <SeveritySummaryBar summary={scan.summary} />
                    </div>
                  </div>

                  {/* Right: Score + Actions */}
                  <div className="flex items-center gap-4 flex-shrink-0">
                    {scan.security_score != null && (
                      <div className={`text-2xl font-bold ${
                        scan.security_score >= 80 ? 'text-[var(--green)]' :
                        scan.security_score >= 50 ? 'text-[var(--amber)]' :
                        'text-[var(--red)]'
                      }`}>
                        {scan.security_score}
                      </div>
                    )}

                    <button
                      onClick={(e) => handleRerun(e, scan.id)}
                      disabled={rerunningId === scan.id}
                      className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors border border-[var(--border)] px-3 py-1.5 hover:border-[var(--cyan)] disabled:opacity-50"
                      title="Re-scan this repository"
                    >
                      <RefreshCw size={12} className={rerunningId === scan.id ? 'animate-spin' : ''} />
                      Rescan
                    </button>

                    {scan.status === 'completed' && (
                      <button
                        className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-[var(--cyan)] border border-[var(--cyan)] px-3 py-1.5 hover:bg-[#00f5ff1a] transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/report/${scan.id}`);
                        }}
                      >
                        Report <ArrowRight size={12} />
                      </button>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

      </div>
    </div>
  );
}
