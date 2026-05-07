import React, { useRef } from 'react';
import { motion, useMotionValue, useTransform, useSpring } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';

export default function FloatingTerminal() {
  const ref = useRef(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const mouseXSpring = useSpring(x, { stiffness: 150, damping: 20 });
  const mouseYSpring = useSpring(y, { stiffness: 150, damping: 20 });

  const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ["10deg", "-10deg"]);
  const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ["-10deg", "10deg"]);

  const handleMouseMove = (e) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const xPct = mouseX / width - 0.5;
    const yPct = mouseY / height - 0.5;
    x.set(xPct);
    y.set(yPct);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <div style={{ perspective: 1000 }}>
      <motion.div
        ref={ref}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          rotateX,
          rotateY,
          transformStyle: "preserve-3d",
        }}
        className="w-full max-w-lg bg-[var(--bg-panel)] bg-opacity-60 backdrop-blur-xl border border-[var(--border)] rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden cursor-crosshair"
      >
        {/* Terminal Header */}
        <div className="bg-[#1e1f22] px-4 py-3 flex items-center justify-between border-b border-[var(--border)]" style={{ transform: "translateZ(20px)" }}>
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <div className="text-xs text-[var(--text-dim)] font-mono tracking-wider">scan_results.log</div>
          <div className="text-[10px] font-bold text-[var(--green)] border border-[var(--green)] px-2 py-0.5 rounded uppercase tracking-widest shadow-[0_0_10px_var(--color-cyber-green)]">Live</div>
        </div>
        
        {/* Terminal Body */}
        <div className="p-10 flex flex-col items-center justify-center min-h-[300px] text-center" style={{ transform: "translateZ(40px)" }}>
          <AlertTriangle size={48} className="text-[var(--text-primary)] mb-6 opacity-80" />
          <h3 className="text-2xl font-bold mb-3">Scan Failed</h3>
          <p className="text-[var(--text-dim)] text-xs mb-8 max-w-xs font-mono leading-relaxed">
            git clone failed: fatal: destination path 'C:\Users\Asus\Desktop\hackathon_cloned_repos' already exists and is not an empty directory.
          </p>
          <button className="border border-[var(--text-dim)] text-[var(--text-primary)] px-8 py-2.5 rounded-full text-sm font-bold hover:bg-white hover:text-black transition-colors">
            Try Again
          </button>
        </div>
      </motion.div>
    </div>
  );
}
