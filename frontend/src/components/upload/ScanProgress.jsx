import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageCircle, FileText } from 'lucide-react';
import TerminalLine from '../ui/TerminalLine';
import { useScanStore } from '../../store/scanStore';
import { createScan, getReport, getScan } from '../../lib/api';
import { useAuthToken } from '../../lib/useAuthToken';
import { mapReport } from '../../lib/reportMapper';

export default function ScanProgress() {
  const navigate = useNavigate();
  const {
    uploadedFile,
    repoUrl,
    scanProgress,
    scanLogs,
    scanStatus,
    scanId,
    scanError,
    addLog,
    setProgress,
    setScanStatus,
    setReport,
    setScanId,
    setScanError
  } = useScanStore();
  const { getToken } = useAuthToken();
  const hasStarted = useRef(false);
  const lastStatus = useRef(null);
  const progressRef = useRef(0);

  const logStatus = (status) => {
    if (!status || lastStatus.current === status) return;
    lastStatus.current = status;

    const messages = {
      pending: 'Queued scan request...',
      cloning: 'Cloning target repository...',
      semgrep_scanning: 'Running Semgrep security rules...',
      parsing: 'Extracting AST and control flow graphs...',
      analyzing: 'Running AI semantic analysis...',
      completed: 'Scan complete ✓',
      failed: 'Scan failed ✗'
    };

    if (messages[status]) {
      addLog(messages[status]);
    }
  };

  const getProgressForStatus = (status) => {
    const map = {
      pending: 10,
      cloning: 25,
      semgrep_scanning: 40,
      parsing: 55,
      analyzing: 75,
      completed: 100,
      failed: 100
    };

    return map[status] ?? 20;
  };

  const updateProgress = (value) => {
    const nextValue = Math.max(progressRef.current, value);
    progressRef.current = nextValue;
    setProgress(nextValue);
  };

  const parseRepoUrl = (url) => {
    try {
      const parsed = new URL(url);
      const parts = parsed.pathname.replace(/\.git$/, '').split('/').filter(Boolean);
      if (parts.length < 2) return null;
      return { owner: parts[0], name: parts[1] };
    } catch (error) {
      return null;
    }
  };

  const startBackendScan = async () => {
    if (hasStarted.current) return;
    hasStarted.current = true;
    progressRef.current = 0;

    const token = await getToken();
    if (!token) {
      addLog('Missing auth token. Please sign in again.');
      setScanError('Missing auth token');
      setScanStatus('error');
      return;
    }

    if (!repoUrl) {
      if (uploadedFile) {
        addLog('File uploads are not supported by the backend yet.');
      } else {
        addLog('Repository URL is required to start a scan.');
      }
      setScanError('Missing repository URL');
      setScanStatus('error');
      return;
    }

    const repoInfo = parseRepoUrl(repoUrl);
    if (!repoInfo) {
      addLog('Invalid repository URL. Use https://github.com/owner/repo');
      setScanError('Invalid repository URL');
      setScanStatus('error');
      return;
    }

    addLog('Initializing VulnBot Core...');
    updateProgress(5);

    const payload = {
      repo_url: repoUrl,
      repo_owner: repoInfo.owner,
      repo_name: repoInfo.name,
      branch: 'main'
    };

    try {
      const summary = await createScan(token, payload);
      if (!summary?.id) {
        throw new Error('Scan creation did not return an id');
      }
      setScanId(summary.id);
      logStatus(summary?.status || 'pending');
      updateProgress(getProgressForStatus(summary?.status || 'pending'));

      let cancelled = false;

      const poll = async () => {
        if (cancelled) return;
        try {
          // Refresh token on each poll in case it expires
          const freshToken = await getToken();
          if (!freshToken || cancelled) return;

          const scan = await getScan(freshToken, summary.id);
          logStatus(scan?.status);
          updateProgress(getProgressForStatus(scan?.status));

          if (scan?.status === 'completed') {
            const report = await getReport(freshToken, summary.id);
            setReport(mapReport(report));
            setScanStatus('complete');
            return;
          }

          if (scan?.status === 'failed') {
            addLog('Scan failed on the server.');
            setScanError('Scan failed');
            setScanStatus('error');
            return;
          }

          setTimeout(poll, 2500);
        } catch (error) {
          addLog('Failed to fetch scan status.');
          setScanError(error?.message || 'Scan status error');
          setScanStatus('error');
        }
      };

      setTimeout(poll, 1500);

      return () => {
        cancelled = true;
      };
    } catch (error) {
      addLog(`Failed to start scan: ${error?.message || 'Unknown error'}`);
      setScanError(error?.message || 'Scan start error');
      setScanStatus('error');
    }
  };

  // Backend-driven scan state
  useEffect(() => {
    if (scanStatus !== 'scanning') return;
    startBackendScan();
  }, [scanStatus]);

  const progressBarColor = 
    scanProgress < 30 ? 'bg-[var(--cyan)]' : 
    scanProgress < 70 ? 'bg-[var(--amber)]' : 
    'bg-[var(--red)]';

  return (
    <div className="w-full max-w-3xl mx-auto mt-12 relative">
      {/* Scanner Beam */}
      <div className="absolute -top-4 -left-4 -right-4 h-full pointer-events-none overflow-hidden z-20">
        <div className="scanner-beam"></div>
      </div>

      <div className="bg-[var(--bg-panel)] border border-[var(--border)] p-1 rounded-sm relative z-10 shadow-lg">
        {/* Terminal Header */}
        <div className="bg-[var(--bg-surface)] px-4 py-2 border-b border-[var(--border)] flex items-center justify-between">
          <div className="text-xs text-[var(--text-dim)] uppercase tracking-widest font-bold">Terminal Output</div>
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[var(--border)]"></div>
            <div className="w-3 h-3 rounded-full bg-[var(--border)]"></div>
            <div className="w-3 h-3 rounded-full bg-[var(--border)]"></div>
          </div>
        </div>

        {/* Terminal Body */}
        <div className="p-6 h-[300px] overflow-y-auto font-mono text-sm">
          <TerminalLine lines={scanLogs} />
        </div>
        
        {/* Progress Bar Footer */}
        <div className="border-t border-[var(--border)] p-4 bg-[var(--bg-surface)]">
          <div className="flex justify-between text-xs mb-2 uppercase tracking-wider text-[var(--text-dim)] font-bold">
            <span>Overall Progress</span>
            <span className={
              scanProgress < 30 ? 'text-[var(--cyan)]' : 
              scanProgress < 70 ? 'text-[var(--amber)]' : 
              'text-[var(--red)]'
            }>{scanProgress}%</span>
          </div>
          <div className="w-full h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden border border-[var(--border)]">
            <div 
              className={`h-full transition-all duration-300 ease-out ${progressBarColor}`}
              style={{ width: `${scanProgress}%` }}
            ></div>
          </div>

          {scanStatus === 'complete' && (
            <div className="mt-4 flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate(`/report/${scanId}`)}
                className="flex items-center justify-center gap-2 border border-[var(--border)] px-4 py-2 text-sm font-bold uppercase tracking-widest text-[var(--text-dim)] hover:text-[var(--cyan)] hover:border-[var(--cyan)] transition-colors"
              >
                <FileText size={16} /> View Report
              </button>
              <button
                onClick={() => navigate(`/chat/${scanId}`)}
                className="flex items-center justify-center gap-2 border border-[var(--cyan)] px-4 py-2 text-sm font-bold uppercase tracking-widest text-[var(--cyan)] hover:bg-[var(--cyan)] hover:text-black transition-colors"
              >
                <MessageCircle size={16} /> Talk to DevSecOps
              </button>
            </div>
          )}
        </div>

        {/* Error Footer */}
        {scanError && (
          <div className="border-t border-[var(--red)] p-4 bg-[#ff2d5511]">
            <div className="flex items-center justify-between">
              <span className="text-[var(--red)] text-sm font-bold uppercase tracking-wider">
                ✗ {scanError}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
