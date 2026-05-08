import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Clock, CheckCircle, Cpu, Lock, ArrowRight, GitBranch, ChevronDown } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, useUser } from '@clerk/clerk-react';
import VantaFog from '../components/ui/VantaFog';
import { useScanStore } from '../store/scanStore';
import ScanProgress from '../components/upload/ScanProgress';
import ReportView from '../components/report/ReportView';
import { getRepos, getAuthMe, getScanHistory } from '../lib/api';
import { useAuthToken } from '../lib/useAuthToken';

const EMPTY_LIVE_STATS = {
  totalVulns: 0,
  projectsSecured: 0,
}

function countSummaryVulns(summary) {
  if (!summary || typeof summary !== 'object') return 0
  const keys = ['critical', 'high', 'medium', 'low', 'info']
  return keys.reduce((acc, key) => acc + Number(summary[key] || 0), 0)
}

function formatCount(value) {
  const safe = Number.isFinite(value) ? value : 0
  return new Intl.NumberFormat('en-US').format(safe)
}

export default function Landing() {
  const { isSignedIn } = useUser();
  const { getToken } = useAuthToken();
  const { scanStatus, setScanStatus, resetScan, scanId, setRepoUrl: setStoredRepoUrl } = useScanStore();
  const [repos, setRepos] = useState([]);
  const [repoUrl, setRepoUrl] = useState('');
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [liveStats, setLiveStats] = useState(EMPTY_LIVE_STATS);
  const scanSectionRef = useRef(null);

  useEffect(() => {
    if (!isSignedIn) return;

    let cancelled = false;

    (async () => {
      setLoadingRepos(true);
      try {
        const token = await getToken();
        if (!token || cancelled) return;

        await getAuthMe(token);
        const data = await getRepos(token);

        if (cancelled) return;

        if (Array.isArray(data)) {
          setRepos(data);
          if (data.length > 0) setRepoUrl(data[0].html_url || '');
        } else {
          setRepos([{ id: 'error', full_name: 'Error fetching repos', html_url: '' }]);
        }
      } catch {
        if (!cancelled) {
          setRepos([{ id: 'error', full_name: 'Failed to fetch repos', html_url: '' }]);
        }
      } finally {
        if (!cancelled) setLoadingRepos(false);
      }
    })();

    return () => { cancelled = true; };
  }, [isSignedIn, getToken]);

  useEffect(() => {
    if (!isSignedIn) return;

    let cancelled = false;

    const refreshLiveStats = async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const scans = await getScanHistory(token);
        if (!Array.isArray(scans) || cancelled) return;

        const completed = scans.filter((scan) => scan?.status === 'completed');

        const totalVulns = completed.reduce(
          (sum, scan) => sum + countSummaryVulns(scan?.summary),
          0
        );

        const securedSet = new Set(
          completed
            .filter((scan) => Number(scan?.security_score || 0) >= 70)
            .map((scan) => scan?.repo_full_name)
            .filter(Boolean)
        );

        setLiveStats({
          totalVulns,
          projectsSecured: securedSet.size,
        });
      } catch {
        if (!cancelled) setLiveStats(EMPTY_LIVE_STATS);
      }
    };

    refreshLiveStats();
    const timer = setInterval(refreshLiveStats, 15000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [isSignedIn, getToken]);

  // Reset scan state on mount
  useEffect(() => {
    resetScan();
  }, [resetScan]);

  const handleScan = (e) => {
    e.preventDefault();
    if (repoUrl.trim()) {
      setStoredRepoUrl(repoUrl.trim());
      setScanStatus('scanning');
      // Scroll to scan section
      setTimeout(() => {
        scanSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  const displayedStats = isSignedIn ? liveStats : EMPTY_LIVE_STATS;

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[var(--bg-primary)]">
      
      {/* Vanta.js Fog Backdrop */}
      <VantaFog />

      {/* Hero Background Image — bright, layered over fog */}
      <div className="fixed inset-0 w-full h-full z-[1] pointer-events-none" style={{ mixBlendMode: 'screen' }}>
        <img 
          src="/hero-bg.png" 
          alt="" 
          className="w-full h-full object-cover object-center"
          style={{ opacity: 1, filter: 'brightness(1.3) saturate(1.4)' }}
        />
      </div>

      {/* Hero Section */}
      <div className="min-h-screen flex flex-col justify-center">
        {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full relative z-10 pt-20">
        <div className="flex flex-col lg:flex-row items-center justify-between gap-16">
          
          {/* Left Column: Typography & Input */}
          <div className="w-full lg:w-1/2 flex flex-col justify-center">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <h1 className="text-6xl lg:text-8xl font-black leading-[1.1] mb-6 tracking-tight">
                <span className="block text-white">Analyze.</span>
                <span className="block text-white">Detect.</span>
                <span className="block text-[var(--cyan)]">Secure.</span>
              </h1>
              
              <p className="text-lg lg:text-xl text-[var(--text-dim)] mb-10 max-w-lg font-body leading-relaxed">
                AI-powered vulnerability detection and automated patching for your codebase.
              </p>

              {/* GitHub Repo Selector */}
              <div className="w-full max-w-xl mb-16">
                <SignedOut>
                  <SignInButton mode="modal">
                    <button className="flex items-center gap-3 w-full bg-[var(--bg-panel)] rounded-full border border-[var(--border)] px-6 py-4 text-[var(--text-primary)] font-bold hover:border-[var(--cyan)] hover:shadow-[0_0_20px_var(--color-cyber-cyan)] transition-all">
                      <GitBranch size={24} />
                      Sign in with GitHub to select a repository
                    </button>
                  </SignInButton>
                </SignedOut>

                <SignedIn>
                  <form onSubmit={handleScan} className="flex items-center w-full bg-[var(--bg-panel)] rounded-full border border-[var(--border)] overflow-hidden shadow-2xl group hover:border-[var(--text-dim)] transition-colors">
                    <div className="flex-grow px-6 py-4 flex items-center gap-3 bg-transparent relative">
                      <GitBranch size={20} className="text-[var(--text-dim)] flex-shrink-0" />
                      {loadingRepos ? (
                        <div className="flex items-center gap-2 text-[var(--text-dim)] font-mono text-sm">
                          <div className="w-4 h-4 border-2 border-[var(--cyan)] border-t-transparent rounded-full animate-spin"></div>
                          Loading repositories...
                        </div>
                      ) : repos.length > 0 && repos[0].id !== 'error' ? (
                        <div className="relative w-full">
                          <select 
                            value={repoUrl}
                            onChange={(e) => setRepoUrl(e.target.value)}
                            className="w-full bg-transparent border-none text-[var(--text-primary)] outline-none font-mono text-sm appearance-none cursor-pointer pr-8"
                          >
                            {repos.map(repo => (
                              <option key={repo.id} value={repo.html_url} className="bg-[var(--bg-panel)] text-[var(--text-primary)]">
                                {repo.full_name}{repo.language ? ` · ${repo.language}` : ''}{repo.visibility === 'private' ? ' 🔒' : ''}
                              </option>
                            ))}
                          </select>
                          <ChevronDown size={16} className="absolute right-0 top-1/2 -translate-y-1/2 text-[var(--text-dim)] pointer-events-none" />
                        </div>
                      ) : (
                        <span className="text-[var(--text-dim)] font-mono text-sm">No repositories found</span>
                      )}
                    </div>
                    <button 
                      type="submit" 
                      disabled={!repoUrl || loadingRepos || repos.length === 0 || repos[0]?.id === 'error'}
                      className="bg-[var(--cyan)] text-white font-bold px-8 py-4 flex items-center gap-2 hover:bg-[#00f5ff] hover:shadow-[0_0_20px_var(--color-cyber-cyan)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Scan <ArrowRight size={18} />
                    </button>
                  </form>
                  <p className="text-xs text-[var(--text-dim)] pl-6 mt-4">
                    {repos.length > 0 && repos[0].id !== 'error' 
                      ? `${repos.length} repositories available — select one to analyze.` 
                      : "We couldn't load your repositories. Please try again later."}
                  </p>
                </SignedIn>
              </div>
              
              {/* Stats Row */}
              <div className="flex items-center gap-14 pt-8 border-t border-[var(--border)] max-w-xl">
                <div>
                  <div className="text-3xl font-bold text-white mb-1">{formatCount(displayedStats.totalVulns)}</div>
                  <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-widest font-bold">Vulns Detected</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-white mb-1">{formatCount(displayedStats.projectsSecured)}</div>
                  <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-widest font-bold">Projects Secured</div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Column: 3D Terminal & Features */}
          <div className="w-full lg:w-1/2 flex flex-col items-center lg:items-end justify-center perspective-[2000px]">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
              className="w-full flex justify-end mb-16"
            >
              {/* <FloatingTerminal /> */}
            </motion.div>

            {/* 4 Feature Icons */}
            <motion.div 
              className="grid grid-cols-4 gap-4 w-full max-w-lg mt-8"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
            >
              <div className="text-center flex flex-col items-center">
                <Clock className="text-[var(--text-dim)] mb-3" size={28} strokeWidth={1.5} />
                <div className="text-[10px] font-bold text-white uppercase tracking-wider mb-1">AI-Powered</div>
                <div className="text-[10px] text-[var(--text-dim)] leading-tight">Smart analysis &<br/>context awareness</div>
              </div>
              <div className="text-center flex flex-col items-center">
                <CheckCircle className="text-[var(--text-dim)] mb-3" size={28} strokeWidth={1.5} />
                <div className="text-[10px] font-bold text-white uppercase tracking-wider mb-1">Accurate</div>
                <div className="text-[10px] text-[var(--text-dim)] leading-tight">Multi-layer detection<br/>with high precision</div>
              </div>
              <div className="text-center flex flex-col items-center">
                <Cpu className="text-[var(--text-dim)] mb-3" size={28} strokeWidth={1.5} />
                <div className="text-[10px] font-bold text-white uppercase tracking-wider mb-1">Automated</div>
                <div className="text-[10px] text-[var(--text-dim)] leading-tight">AI-generated patches<br/>& fix suggestions</div>
              </div>
              <div className="text-center flex flex-col items-center">
                <Lock className="text-[var(--text-dim)] mb-3" size={28} strokeWidth={1.5} />
                <div className="text-[10px] font-bold text-white uppercase tracking-wider mb-1">Secure</div>
                <div className="text-[10px] text-[var(--text-dim)] leading-tight">Enterprise-grade<br/>security</div>
              </div>
            </motion.div>
          </div>

        </div>
      </div>
      </div>

      {/* Inline Scan & Report Section */}
      {scanStatus !== 'idle' && (
        <div ref={scanSectionRef} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full relative z-10 py-24 min-h-screen">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            {scanStatus === 'scanning' && (
              <div className="flex flex-col items-center mb-12">
                <h2 className="text-3xl md:text-5xl font-bold mb-4">
                  <span className="text-[var(--cyan)]">Scanning Repository...</span>
                </h2>
                <p className="text-[var(--text-dim)]">Deploying neural threat analysis engine. Awaiting payload.</p>
                <ScanProgress />
              </div>
            )}
            
            {scanStatus === 'complete' && (
              <div className="w-full">
                <ReportView scanId={scanId || 'unknown'} />
              </div>
            )}

            {scanStatus === 'error' && (
              <div className="flex flex-col items-center mb-12">
                <h2 className="text-3xl md:text-5xl font-bold mb-4">
                  <span className="text-[var(--red)]">Scan Failed</span>
                </h2>
                <p className="text-[var(--text-dim)] mb-6">{useScanStore.getState().scanError || 'An unexpected error occurred.'}</p>
                <button
                  onClick={() => resetScan()}
                  className="border border-[var(--cyan)] text-[var(--cyan)] px-6 py-2 font-bold uppercase tracking-widest text-sm hover:bg-[#00f5ff1a] transition-all"
                >
                  Try Again
                </button>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </div>
  );
}
