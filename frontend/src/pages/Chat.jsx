import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import GlitchText from '../components/ui/GlitchText';
import ReportChat from '../components/report/ReportChat';

export default function Chat() {
  const { scanId } = useParams();
  const navigate = useNavigate();

  return (
    <div className="relative min-h-screen pt-12 pb-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <motion.h1
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-3xl font-bold mb-2 flex items-center gap-4"
            >
              <GlitchText text="DevSecOps Chat" />
              <span className="text-sm font-normal text-[var(--text-dim)] border border-[var(--border)] px-3 py-1 rounded-full uppercase tracking-widest">
                ID: {scanId}
              </span>
            </motion.h1>
            <p className="text-[var(--text-dim)] uppercase tracking-widest text-sm">
              Ask what to do and what not to do for this scan
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`/report/${scanId}`)}
              className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase border border-[var(--border)] px-4 py-2 hover:border-[var(--cyan)]"
            >
              <ArrowLeft size={16} /> Back to Report
            </button>
            <div className="text-xs uppercase tracking-widest text-[var(--text-dim)] border border-[var(--border)] px-3 py-2 rounded-full flex items-center gap-2">
              <ShieldCheck size={14} /> Report-scoped
            </div>
          </div>
        </div>

        <ReportChat scanId={scanId} />
      </div>
    </div>
  );
}
