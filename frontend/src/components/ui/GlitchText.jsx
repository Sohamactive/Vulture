import { useState, useEffect, useRef } from 'react';

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+{}|:<>?';

export default function GlitchText({ text, className = '' }) {
  const [displayText, setDisplayText] = useState(text);
  const intervalRef = useRef(null);

  const triggerGlitch = () => {
    let iterations = 0;
    const maxIterations = 20;
    
    if (intervalRef.current) clearInterval(intervalRef.current);
    
    intervalRef.current = setInterval(() => {
      setDisplayText((prev) => 
        prev.split('').map((char, index) => {
          if (index < iterations / (maxIterations / text.length)) {
            return text[index];
          }
          return CHARS[Math.floor(Math.random() * CHARS.length)];
        }).join('')
      );
      
      if (iterations >= maxIterations) {
        clearInterval(intervalRef.current);
        setDisplayText(text);
      }
      
      iterations += 1;
    }, 60); // 60ms * 20 = 1.2s
  };

  useEffect(() => {
    triggerGlitch();
    return () => clearInterval(intervalRef.current);
  }, [text]);

  return (
    <span 
      className={`relative inline-block glitch-text ${className}`}
      data-text={text}
      onMouseEnter={triggerGlitch}
    >
      {displayText}
    </span>
  );
}
