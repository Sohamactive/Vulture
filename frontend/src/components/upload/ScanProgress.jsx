import React, { useEffect } from 'react';
import TerminalLine from '../ui/TerminalLine';
import { useScanStore } from '../../store/scanStore';
import { useNavigate } from 'react-router-dom';

export default function ScanProgress() {
  const { scanProgress, scanLogs, scanStatus, addLog, setProgress, setScanStatus } = useScanStore();
  const navigate = useNavigate();

  // Mock scan simulation for frontend dev
  useEffect(() => {
    if (scanStatus !== 'scanning') return;

    const mockLogs = [
      "Initializing VulnBot Core...",
      "Cloning target repository...",
      "Extracting AST and control flow graphs...",
      "Running semantic analysis rules...",
      "Checking against OWASP Top 10 A01-A10...",
      "Querying global CVE database...",
      "Analyzing dependencies for outdated packages...",
      "Generating vulnerability map...",
      "Compiling final security report...",
      "Scan complete ✓"
    ];

    let currentLog = 0;
    
    const interval = setInterval(() => {
      if (currentLog < mockLogs.length) {
        addLog(mockLogs[currentLog]);
        setProgress(Math.floor((currentLog / mockLogs.length) * 100));
        currentLog++;
      } else {
        clearInterval(interval);
        setProgress(100);
        setTimeout(() => {
          setScanStatus('complete');
          // No longer navigating away, Landing.jsx will handle rendering the report inline
        }, 1500);
      }
    }, 800); // 800ms between lines for effect

    return () => clearInterval(interval);
  }, [scanStatus, addLog, setProgress, setScanStatus]);

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
        </div>
      </div>
    </div>
  );
}
