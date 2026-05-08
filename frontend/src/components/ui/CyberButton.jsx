export default function CyberButton({
  children,
  onClick,
  className = '',
  pulse = false,
  variant = 'cyan',
  type = 'button',
  disabled = false
}) {
  const colors = {
    cyan: 'border-[var(--cyan)] text-[var(--cyan)] hover:bg-[#00f5ff1a] hover:shadow-[var(--glow-cyan)]',
    red: 'border-[var(--red)] text-[var(--red)] hover:bg-[#ff2d551a] hover:shadow-[var(--glow-red)]',
    amber: 'border-[var(--amber)] text-[var(--amber)] hover:bg-[#ffaa001a] hover:shadow-[0_0_20px_#ffaa0066]',
    green: 'border-[var(--green)] text-[var(--green)] hover:bg-[#00ff871a] hover:shadow-[0_0_20px_#00ff8766]',
  };

  const borderColors = {
    cyan: 'var(--cyan)',
    red: 'var(--red)',
    amber: 'var(--amber)',
    green: 'var(--green)'
  }

  const selectedColor = colors[variant] || colors.cyan;
  const selectedBorderColor = borderColors[variant] || borderColors.cyan

  return (
    <div className="relative inline-block">
      {pulse && (
        <div className="pulse-ring w-full h-full" style={{ borderColor: selectedBorderColor }}></div>
      )}
      <button
        type={type}
        disabled={disabled}
        onClick={onClick}
        className={`relative px-6 py-3 border border-solid font-mono font-bold tracking-wider uppercase transition-all duration-300 z-10 bg-[var(--bg-primary)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:hover:bg-transparent ${selectedColor} ${className}`}
      >
        {children}
      </button>
    </div>
  );
}
