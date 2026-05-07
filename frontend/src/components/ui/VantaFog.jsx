import { useEffect, useRef, useState } from 'react';

/**
 * Dynamically loads a script from a URL, returning a promise.
 * Skips loading if a script with the same src already exists.
 */
function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

export default function VantaFog() {
  const vantaRef = useRef(null);
  const effectRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function initVanta() {
      try {
        // Load Three.js r121 (required by Vanta)
        await loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r121/three.min.js');
        // Load Vanta fog
        await loadScript('https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.fog.min.js');

        if (cancelled || !vantaRef.current || !window.VANTA) return;

        effectRef.current = window.VANTA.FOG({
          el: vantaRef.current,
          THREE: window.THREE,
          mouseControls: true,
          touchControls: true,
          gyroControls: false,
          minHeight: 200.0,
          minWidth: 200.0,
          highlightColor: 0x00f5ff,
          midtoneColor: 0x0a0f1a,
          lowlightColor: 0x020409,
          baseColor: 0x020409,
          blurFactor: 0.6,
          speed: 1.2,
          zoom: 1.0,
        });
      } catch (err) {
        console.warn('Vanta.js failed to load:', err);
      }
    }

    initVanta();

    return () => {
      cancelled = true;
      if (effectRef.current) {
        effectRef.current.destroy();
        effectRef.current = null;
      }
    };
  }, []);

  return (
    <div
      ref={vantaRef}
      className="fixed inset-0 w-full h-full z-0 pointer-events-none"
      style={{ minHeight: '100vh' }}
    />
  );
}
