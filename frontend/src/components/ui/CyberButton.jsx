import React from 'react';

export default function CyberButton({ children, onClick, className = '', pulse = false, variant = 'cyan' }) {
  const colors = {
    cyan: 'border-[var(--cyan)] text-[var(--cyan)] hover:bg-[#00f5ff1a] hover:shadow-[var(--glow-cyan)]',
    red: 'border-[var(--red)] text-[var(--red)] hover:bg-[#ff2d551a] hover:shadow-[var(--glow-red)]',
  };

  const selectedColor = colors[variant] || colors.cyan;

  return (
    <div className="relative inline-block">
      {pulse && (
        <div className={`pulse-ring w-full h-full border-${variant === 'cyan' ? '[var(--cyan)]' : '[var(--red)]'}`}></div>
      )}
      <button
        onClick={onClick}
        className={`relative px-6 py-3 border border-solid font-mono font-bold tracking-wider uppercase transition-all duration-300 z-10 bg-[var(--bg-primary)] ${selectedColor} ${className}`}
      >
        {children}
      </button>
    </div>
  );
}
