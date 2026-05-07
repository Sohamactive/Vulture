import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Clock, CheckCircle, Cpu, Lock, ArrowRight, GitBranch } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, useUser } from '@clerk/clerk-react';
import ThreatGlobe from '../components/3d/ThreatGlobe';
import FloatingTerminal from '../components/ui/FloatingTerminal';
import { useScanStore } from '../store/scanStore';
import ScanProgress from '../components/upload/ScanProgress';
import ReportView from '../components/report/ReportView';

export default function Landing() {
  const navigate = useNavigate();
  const { user, isLoaded, isSignedIn } = useUser();
  const { scanStatus, setScanStatus, resetScan } = useScanStore();
  const [repos, setRepos] = useState([]);
  const [repoUrl, setRepoUrl] = useState('');
  const [loadingRepos, setLoadingRepos] = useState(false);
  const scanSectionRef = React.useRef(null);

  useEffect(() => {
    if (isSignedIn && user) {
      // Debug user object
      console.log("Clerk User:", user);
      
      const externalAccount = user.externalAccounts?.find(a => a.provider === "oauth_github");
      // Sometimes Clerk uses different properties for the username depending on the account data
      const githubUsername = externalAccount?.username || user.username || user.primaryEmailAddress?.emailAddress?.split('@')[0];
      
      console.log("Found GitHub Username:", githubUsername);
      
      if (githubUsername) {
        setLoadingRepos(true);
        fetch(`https://api.github.com/users/${githubUsername}/repos?sort=updated&per_page=100`)
          .then(res => {
            console.log("GitHub API Status:", res.status);
            return res.json();
          })
          .then(data => {
            console.log("GitHub API Data:", data);
            if (Array.isArray(data)) {
              setRepos(data);
              if (data.length > 0) setRepoUrl(data[0].html_url);
            } else {
              console.error("Failed to parse repos or rate limited:", data);
              // Fallback to manual input or show error in dropdown
              setRepos([{ id: 'error', full_name: 'Error fetching repos (check console)', html_url: '' }]);
            }
          })
          .catch(err => {
            console.error("Fetch Error:", err);
            setRepos([{ id: 'error', full_name: 'Network error fetching repos', html_url: '' }]);
          })
          .finally(() => setLoadingRepos(false));
      } else {
        console.warn("No github username could be found on the Clerk user object.");
        setRepos([{ id: 'error', full_name: 'No GitHub username linked to account', html_url: '' }]);
      }
    }
  }, [isSignedIn, user]);

  // Reset scan state on mount
  useEffect(() => {
    resetScan();
  }, [resetScan]);

  const handleScan = (e) => {
    e.preventDefault();
    if (repoUrl.trim()) {
      setScanStatus('scanning');
      // Scroll to scan section
      setTimeout(() => {
        scanSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[var(--bg-primary)]">
      
      {/* Massive 3D Backdrop */}
      <div className="absolute right-[-40%] top-[-20%] w-[120%] h-[140%] opacity-60 pointer-events-none z-0">
        <ThreatGlobe />
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
                    <div className="flex-grow px-6 py-4 flex items-center gap-3 bg-transparent">
                      <GitBranch size={20} className="text-[var(--text-dim)]" />
                      {loadingRepos ? (
                        <span className="text-[var(--text-dim)] font-mono text-sm">Loading repositories...</span>
                      ) : repos.length > 0 && repos[0].id !== 'error' ? (
                        <select 
                          value={repoUrl}
                          onChange={(e) => setRepoUrl(e.target.value)}
                          className="w-full bg-transparent border-none text-[var(--text-primary)] outline-none font-mono text-sm appearance-none cursor-pointer"
                        >
                          {repos.map(repo => (
                            <option key={repo.id} value={repo.html_url} className="bg-[var(--bg-panel)]">
                              {repo.full_name} {repo.private ? '(Private)' : ''}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input 
                          type="text" 
                          value={repoUrl}
                          onChange={(e) => setRepoUrl(e.target.value)}
                          placeholder="https://github.com/username/repo"
                          className="flex-grow bg-transparent border-none text-[var(--text-primary)] outline-none font-mono text-sm placeholder:text-[var(--border)] w-full"
                        />
                      )}
                    </div>
                    <button 
                      type="submit" 
                      disabled={!repoUrl}
                      className="bg-[var(--cyan)] text-white font-bold px-8 py-4 flex items-center gap-2 hover:bg-[#00f5ff] hover:shadow-[0_0_20px_var(--color-cyber-cyan)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Scan <ArrowRight size={18} />
                    </button>
                  </form>
                  <p className="text-xs text-[var(--text-dim)] pl-6 mt-4">
                    {repos.length > 0 && repos[0].id !== 'error' 
                      ? "Select a repository from your GitHub account to analyze." 
                      : "Paste any public GitHub URL — we clone, scan, and report"}
                  </p>
                </SignedIn>
              </div>
              
              {/* Stats Row */}
              <div className="flex items-center gap-12 pt-8 border-t border-[var(--border)] max-w-xl">
                <div>
                  <div className="text-3xl font-bold text-white mb-1">15,000+</div>
                  <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-widest font-bold">Vulns Detected</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-white mb-1">99.2%</div>
                  <div className="text-[10px] text-[var(--text-dim)] uppercase tracking-widest font-bold">Accuracy</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-white mb-1">500+</div>
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
                <ReportView scanId="demo-123" />
              </div>
            )}
          </motion.div>
        </div>
      )}
    </div>
  );
}
