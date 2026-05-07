import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import DropZone from '../components/upload/DropZone';
import ScanProgress from '../components/upload/ScanProgress';
import { useScanStore } from '../store/scanStore';
import GlitchText from '../components/ui/GlitchText';

export default function Scan() {
  const { scanStatus, setScanStatus, resetScan } = useScanStore();

  // Reset scan state on mount
  useEffect(() => {
    resetScan();
  }, [resetScan]);

  const handleUpload = () => {
    // Transition to scanning state
    setScanStatus('scanning');
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
            <GlitchText text="System Scan Initialization" />
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-[var(--text-dim)]"
          >
            Deploying neural threat analysis engine. Awaiting payload.
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          {scanStatus === 'idle' ? (
            <DropZone onUpload={handleUpload} />
          ) : (
            <ScanProgress />
          )}
        </motion.div>
        
      </div>
    </div>
  );
}
