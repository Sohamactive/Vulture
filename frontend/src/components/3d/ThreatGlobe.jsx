import React, { Suspense, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, useTexture } from '@react-three/drei';
import * as THREE from 'three';

// Convert lat/lng to 3D sphere coordinates
function latLngToVec3(lat, lng, radius = 1.02) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
     radius * Math.cos(phi),
     radius * Math.sin(phi) * Math.sin(theta)
  );
}

// Severity color map
const COLORS = { critical: '#ff2d55', high: 'var(--high-sev)', medium: '#ffaa00', low: '#00f5ff' };

function GlobeMesh() {
  return (
    <group>
      {/* Solid inner core to block background stars */}
      <mesh>
        <sphereGeometry args={[0.98, 64, 64]} />
        <meshStandardMaterial
          color="#020409"
          emissive="#020409"
          roughness={1}
          metalness={0}
        />
      </mesh>
      
      {/* Bright glowing wireframe overlay */}
      <mesh>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color="#00f5ff"
          emissive="#00f5ff"
          emissiveIntensity={0.6}
          wireframe={true}
          transparent={true}
          opacity={0.3}
        />
      </mesh>
    </group>
  );
}

function VulnNodes({ vulns }) {
  return vulns.map((v, i) => {
    const pos = latLngToVec3(v.lat, v.lng);
    return (
      <mesh key={i} position={pos}>
        <sphereGeometry args={[0.015, 8, 8]} />
        <meshStandardMaterial
          color={COLORS[v.severity] || COLORS.low}
          emissive={COLORS[v.severity] || COLORS.low}
          emissiveIntensity={2}
        />
      </mesh>
    );
  });
}

function OrbitRings() {
  const ringRef = useRef();
  
  useFrame((state) => {
    if (ringRef.current) {
      ringRef.current.rotation.z = state.clock.elapsedTime * 0.2;
    }
  });

  return (
    <group ref={ringRef}>
      <mesh rotation={[Math.PI / 4, 0, 0]}>
        <torusGeometry args={[1.4, 0.003, 8, 200]} />
        <meshStandardMaterial color="#00f5ff" emissive="#00f5ff" emissiveIntensity={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 5, Math.PI / 6, 0]}>
        <torusGeometry args={[1.7, 0.002, 8, 200]} />
        <meshStandardMaterial color="#ff2d55" emissive="#ff2d55" emissiveIntensity={1} />
      </mesh>
    </group>
  );
}

export default function ThreatGlobe({ vulns = [] }) {
  // Demo vulns if none provided
  const displayVulns = vulns.length > 0 ? vulns : [
    { lat: 40.7128, lng: -74.0060, severity: 'critical' },
    { lat: 51.5074, lng: -0.1278, severity: 'high' },
    { lat: 35.6895, lng: 139.6917, severity: 'medium' },
    { lat: -33.8688, lng: 151.2093, severity: 'low' },
    { lat: 48.8566, lng: 2.3522, severity: 'critical' },
  ];

  return (
    <div className="w-full h-full min-h-[500px]">
      <Canvas
        camera={{ position: [0, 0, 3.2], fov: 50 }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.1} />
        <pointLight position={[5, 5, 5]} color="#00f5ff" intensity={2} />
        
        <Suspense fallback={null}>
          <Stars radius={100} depth={50} count={3000} factor={3} fade />
          <GlobeMesh />
          {/* <VulnNodes vulns={displayVulns} /> */}
          <OrbitRings />
        </Suspense>
        
        <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.4} />
      </Canvas>
    </div>
  );
}
