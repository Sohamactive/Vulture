import { useState, useEffect } from 'react';

export default function TerminalLine({ lines }) {
  const [displayedLines, setDisplayedLines] = useState([]);
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [currentCharIndex, setCurrentCharIndex] = useState(0);

  useEffect(() => {
    if (!lines || lines.length === 0) return;
    
    if (currentLineIndex < lines.length) {
      const currentLineText = lines[currentLineIndex];
      
      if (currentCharIndex < currentLineText.length) {
        const timer = setTimeout(() => {
          setCurrentCharIndex((prev) => prev + 1);
        }, 40);
        return () => clearTimeout(timer);
      } else {
        const timer = setTimeout(() => {
          setDisplayedLines((prev) => [...prev, currentLineText]);
          setCurrentLineIndex((prev) => prev + 1);
          setCurrentCharIndex(0);
        }, 100);
        return () => clearTimeout(timer);
      }
    }
  }, [lines, currentLineIndex, currentCharIndex]);

  return (
    <div className="font-mono text-[var(--text-primary)]">
      {displayedLines.map((line, i) => (
        <div key={i} className="mb-1">
          <span className="text-[var(--cyan)] mr-2">&gt;</span>
          <span>{line}</span>
        </div>
      ))}
      
      {currentLineIndex < lines.length && (
        <div className="mb-1">
          <span className="text-[var(--cyan)] mr-2">&gt;</span>
          <span>{lines[currentLineIndex].substring(0, currentCharIndex)}</span>
          <span className="inline-block w-[8px] h-[1em] bg-[var(--text-primary)] ml-1 align-middle cursor"></span>
        </div>
      )}
      
      {currentLineIndex >= lines.length && (
        <div className="mb-1">
          <span className="text-[var(--cyan)] mr-2">&gt;</span>
          <span className="inline-block w-[8px] h-[1em] bg-[var(--text-primary)] ml-1 align-middle cursor"></span>
        </div>
      )}
    </div>
  );
}
