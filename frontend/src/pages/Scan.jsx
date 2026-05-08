import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { GitBranch, ArrowRight, Search, Globe, Lock, Star, RefreshCw } from 'lucide-react';
import ScanProgress from '../components/upload/ScanProgress';
import { useScanStore } from '../store/scanStore';
import GlitchText from '../components/ui/GlitchText';
import { getRepos } from '../lib/api';
import { useAuthToken } from '../lib/useAuthToken';

export default function Scan() {
  const { scanStatus, setScanStatus, resetScan, setRepoUrl: setStoredRepoUrl } = useScanStore();
  const { getToken } = useAuthToken();
  const [repos, setRepos] = useState([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Reset scan state on mount
  useEffect(() => {
    resetScan();
  }, [resetScan]);

  // Fetch repos
  useEffect(() => {
    let cancelled = false;
    setLoadingRepos(true);

    (async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const data = await getRepos(token);
        if (!cancelled && Array.isArray(data)) {
          setRepos(data);
        }
      } catch {
        if (!cancelled) setRepos([]);
      } finally {
        if (!cancelled) setLoadingRepos(false);
      }
    })();

    return () => { cancelled = true; };
  }, [getToken]);

  const filteredRepos = repos.filter(repo =>
    repo.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    repo.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    repo.language?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleScan = () => {
    if (!selectedRepo) return;
    setStoredRepoUrl(selectedRepo.html_url);
    setScanStatus('scanning');
  };

  const handleRefresh = async () => {
    setLoadingRepos(true);
    try {
      const token = await getToken();
      if (!token) return;
      const data = await getRepos(token);
      if (Array.isArray(data)) setRepos(data);
    } catch {
      // ignore
    } finally {
      setLoadingRepos(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    const days = Math.floor(diff / 86400000);
    if (days === 0) return 'today';
    if (days === 1) return 'yesterday';
    if (days < 30) return `${days}d ago`;
    if (days < 365) return `${Math.floor(days / 30)}mo ago`;
    return `${Math.floor(days / 365)}y ago`;
  };

  return (
    <div className="relative min-h-screen pt-12 pb-24">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">

        <div className="text-center mb-12">
          <motion.h1
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl md:text-5xl font-bold mb-4"
          >
            <GlitchText text="Select Repository" />
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-[var(--text-dim)]"
          >
            Choose a repository from your GitHub account to scan for vulnerabilities.
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          {scanStatus === 'idle' ? (
            <div className="w-full">
              {/* Search & Refresh Bar */}
              <div className="flex items-center gap-3 mb-6">
                <div className="relative flex-grow">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Search size={16} className="text-[var(--text-dim)]" />
                  </div>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search repositories..."
                    className="w-full bg-[var(--bg-panel)] border border-[var(--border)] text-[var(--text-primary)] pl-11 pr-4 py-3 focus:outline-none focus:border-[var(--cyan)] transition-colors font-mono text-sm"
                  />
                </div>
                <button
                  onClick={handleRefresh}
                  disabled={loadingRepos}
                  className="flex items-center gap-2 border border-[var(--border)] px-4 py-3 text-[var(--text-dim)] hover:text-[var(--cyan)] hover:border-[var(--cyan)] transition-colors disabled:opacity-50"
                >
                  <RefreshCw size={16} className={loadingRepos ? 'animate-spin' : ''} />
                </button>
              </div>

              {/* Repo List */}
              <div className="bg-[var(--bg-surface)] border border-[var(--border)] max-h-[500px] overflow-y-auto">
                {loadingRepos ? (
                  <div className="p-12 flex flex-col items-center gap-4">
                    <div className="w-8 h-8 border-2 border-[var(--cyan)] border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-[var(--text-dim)] text-sm font-mono">Fetching repositories from GitHub...</span>
                  </div>
                ) : filteredRepos.length === 0 ? (
                  <div className="p-12 text-center text-[var(--text-dim)]">
                    {searchQuery ? 'No repositories match your search.' : 'No repositories found.'}
                  </div>
                ) : (
                  filteredRepos.map((repo) => (
                    <div
                      key={repo.id}
                      onClick={() => setSelectedRepo(repo)}
                      className={`px-5 py-4 border-b border-[var(--border)] last:border-0 cursor-pointer transition-all ${
                        selectedRepo?.id === repo.id
                          ? 'bg-[#00f5ff0a] border-l-2 border-l-[var(--cyan)]'
                          : 'hover:bg-[var(--bg-panel)] border-l-2 border-l-transparent'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-grow min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <GitBranch size={14} className="text-[var(--text-dim)] flex-shrink-0" />
                            <span className="font-bold text-[var(--text-primary)] truncate">{repo.full_name}</span>
                            {repo.visibility === 'private' ? (
                              <Lock size={12} className="text-[var(--amber)] flex-shrink-0" />
                            ) : (
                              <Globe size={12} className="text-[var(--text-dim)] flex-shrink-0" />
                            )}
                          </div>
                          {repo.description && (
                            <p className="text-xs text-[var(--text-dim)] truncate mb-1.5 pl-[22px]">{repo.description}</p>
                          )}
                          <div className="flex items-center gap-4 text-[10px] text-[var(--text-dim)] pl-[22px]">
                            {repo.language && (
                              <span className="flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-[var(--cyan)]"></span>
                                {repo.language}
                              </span>
                            )}
                            {repo.stars > 0 && (
                              <span className="flex items-center gap-1">
                                <Star size={10} /> {repo.stars}
                              </span>
                            )}
                            {repo.updated_at && (
                              <span>Updated {formatDate(repo.updated_at)}</span>
                            )}
                          </div>
                        </div>

                        {/* Selection indicator */}
                        <div className={`w-5 h-5 rounded-full border-2 flex-shrink-0 mt-0.5 flex items-center justify-center transition-all ${
                          selectedRepo?.id === repo.id
                            ? 'border-[var(--cyan)] bg-[var(--cyan)]'
                            : 'border-[var(--border)]'
                        }`}>
                          {selectedRepo?.id === repo.id && (
                            <div className="w-2 h-2 rounded-full bg-black"></div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Selected Repo & Scan Button */}
              <div className="mt-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
                <div className="flex-grow">
                  {selectedRepo ? (
                    <div className="bg-[var(--bg-panel)] border border-[var(--border)] px-5 py-3 flex items-center gap-3">
                      <GitBranch size={16} className="text-[var(--cyan)]" />
                      <div>
                        <div className="text-sm font-bold text-[var(--text-primary)]">{selectedRepo.full_name}</div>
                        <div className="text-[10px] text-[var(--text-dim)] font-mono">
                          Branch: {selectedRepo.default_branch || 'main'} • {selectedRepo.visibility}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-[var(--bg-panel)] border border-dashed border-[var(--border)] px-5 py-3 text-[var(--text-dim)] text-sm">
                      Select a repository above to begin scanning
                    </div>
                  )}
                </div>

                <button
                  onClick={handleScan}
                  disabled={!selectedRepo}
                  className="bg-[var(--cyan)] text-black font-bold px-8 py-3 flex items-center justify-center gap-2 hover:shadow-[0_0_20px_var(--color-cyber-cyan)] transition-all disabled:opacity-30 disabled:cursor-not-allowed text-sm uppercase tracking-wider"
                >
                  Start Scan <ArrowRight size={16} />
                </button>
              </div>
            </div>
          ) : (
            <ScanProgress />
          )}
        </motion.div>

      </div>
    </div>
  );
}
