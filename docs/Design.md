# VulnBot — 3D React Web Page

## Project Overview

VulnBot is an AI-powered security audit assistant that lets users upload a codebase and receive a prioritized CVE + OWASP vulnerability report. This document covers the **complete 3D React frontend** — architecture, components, 3D scene design, styling philosophy, and implementation guide.

---

## Aesthetic Direction

**Theme:** Dark cyberpunk / terminal hacker aesthetic  
**Palette:** Deep black backgrounds (`#020409`), electric cyan (`#00f5ff`), neon red (`#ff2d55`), amber (`#ffaa00`)  
**Typography:** `"Share Tech Mono"` (display) + `"IBM Plex Mono"` (body) — pure monospace terminals, no softness  
**Motion:** Particle field, floating panels, scanning beam animations, glitch effects  
**3D:** Three.js scene with a rotating globe covered in glowing vulnerability nodes, orbiting threat rings, and real-time data streams  

The page must feel like a **mission control for security** — tense, precise, alive.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 18 + Vite |
| 3D Engine | Three.js (`r128`) via CDN or `npm i three` |
| 3D React Binding | `@react-three/fiber` + `@react-three/drei` |
| Animation | Framer Motion + CSS keyframes |
| Styling | Tailwind CSS + custom CSS variables |
| Icons | Lucide React |
| Charts | Recharts (severity donut, timeline) |
| State | Zustand |
| Routing | React Router v6 |

---

## File Structure

```
vulnbot-frontend/
├── public/
│   └── fonts/
│       └── ShareTechMono-Regular.ttf
├── src/
│   ├── assets/
│   │   └── globe-texture.jpg
│   ├── components/
│   │   ├── 3d/
│   │   │   ├── ThreatGlobe.jsx          ← Main 3D globe scene
│   │   │   ├── ParticleField.jsx        ← Background particle system
│   │   │   ├── OrbitRings.jsx           ← Rotating threat orbit rings
│   │   │   ├── VulnNodes.jsx            ← Glowing dots on globe surface
│   │   │   └── DataStream.jsx           ← Falling matrix-style data lines
│   │   ├── layout/
│   │   │   ├── Navbar.jsx
│   │   │   ├── ScannerBeam.jsx          ← Horizontal scan animation
│   │   │   └── StatusBar.jsx
│   │   ├── upload/
│   │   │   ├── DropZone.jsx             ← Drag-and-drop file uploader
│   │   │   └── ScanProgress.jsx         ← Real-time progress terminal
│   │   ├── report/
│   │   │   ├── ReportCard.jsx           ← "3 Critical, 7 High, 12 Medium"
│   │   │   ├── IssueList.jsx            ← Jira-style issue cards
│   │   │   ├── IssueDetail.jsx          ← Code snippet + remediation
│   │   │   ├── SeverityDonut.jsx        ← Recharts donut chart
│   │   │   └── OWASPRadar.jsx           ← OWASP Top 10 radar chart
│   │   └── ui/
│   │       ├── GlitchText.jsx
│   │       ├── TerminalLine.jsx
│   │       ├── SeverityBadge.jsx
│   │       └── CyberButton.jsx
│   ├── pages/
│   │   ├── Landing.jsx                  ← Hero + 3D globe + CTA
│   │   ├── Scan.jsx                     ← Upload + live scan terminal
│   │   └── Report.jsx                   ← Full vulnerability report
│   ├── store/
│   │   └── scanStore.js                 ← Zustand global state
│   ├── hooks/
│   │   ├── useScanWebSocket.js
│   │   └── useGlobeAnimation.js
│   ├── utils/
│   │   ├── severityColor.js
│   │   └── cvssParser.js
│   ├── styles/
│   │   ├── globals.css
│   │   └── animations.css
│   ├── App.jsx
│   └── main.jsx
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

---

## Pages

### 1. Landing Page (`/`)

**Purpose:** Wow-factor entry — immediately communicates the product  

**Layout:**
```
┌─────────────────────────────────────────┐
│  NAVBAR  [VulnBot]        [Docs] [API]  │
├─────────────────────────────────────────┤
│                                         │
│   GLITCH HEADLINE                       │
│   "Your Code Has Secrets."              │
│   "We Find Them First."                 │
│                                         │
│   [  3D ROTATING THREAT GLOBE  ]        │
│   ← floating vuln nodes, orbit rings → │
│                                         │
│   [── START FREE SCAN ──]              │
│                                         │
│   STAT COUNTERS (animated on scroll):  │
│   12,847 Vulns Found   98.3% Accuracy  │
│   4.2s Average Scan    OWASP Certified │
│                                         │
│   HOW IT WORKS  (3-step animated flow) │
│   Upload → Analyze → Report             │
│                                         │
└─────────────────────────────────────────┘
```

**Key Effects:**
- Background: Slow particle field (`ParticleField.jsx`) — 800 tiny cyan dots drifting
- Globe: `ThreatGlobe.jsx` — Earth mesh with 40+ glowing vulnerability nodes
- Headline: `GlitchText.jsx` — random character scramble on mount
- CTA button: Neon border with pulse ring animation
- Scroll: Sections fade/slide in with Framer Motion `useInView`

---

### 2. Scan Page (`/scan`)

**Purpose:** Upload interface + live scan progress terminal  

**Layout:**
```
┌──────────────────────────────────────────┐
│  NAVBAR                                  │
├──────────────────────────────────────────┤
│                                          │
│  ┌─────────────────┐  ┌───────────────┐ │
│  │                 │  │  TERMINAL     │ │
│  │   DROP ZONE     │  │  > Scanning.. │ │
│  │   [ Upload ]    │  │  > AST parse  │ │
│  │                 │  │  > OWASP check│ │
│  │  or paste URL   │  │  > CVE lookup │ │
│  └─────────────────┘  │  > Done ✓    │ │
│                        └───────────────┘ │
│                                          │
│  SCAN PROGRESS BAR  [████████░░] 78%    │
│  "Checking OWASP A03: Injection..."      │
│                                          │
│  SCANNER BEAM animation (horizontal)    │
│                                          │
└──────────────────────────────────────────┘
```

**Key Effects:**
- `DropZone.jsx`: Dashed border glows cyan on hover; drag ripple effect
- `ScanProgress.jsx`: Simulates terminal output line by line with typewriter cursor
- `ScannerBeam.jsx`: A horizontal glowing line sweeps left-to-right repeatedly
- Progress bar: Fills with gradient `cyan → amber → red` based on findings severity
- On scan complete: Screen flash + auto-redirect to Report page

---

### 3. Report Page (`/report/:scanId`)

**Purpose:** Full vulnerability report — the "wow" deliverable  

**Layout:**
```
┌────────────────────────────────────────────────┐
│  NAVBAR              [Export PDF] [Open Jira]  │
├────────────────────────────────────────────────┤
│                                                │
│  REPORT CARD:                                  │
│  ┌──────────┬──────────┬──────────┬─────────┐ │
│  │ CRITICAL │   HIGH   │  MEDIUM  │   LOW   │ │
│  │    3     │    7     │   12     │   24    │ │
│  │  🔴       │  🟠       │  🟡       │  🟢      │ │
│  └──────────┴──────────┴──────────┴─────────┘ │
│                                                │
│  ┌──────────────────┐  ┌────────────────────┐ │
│  │  SEVERITY DONUT  │  │  OWASP RADAR CHART │ │
│  │  (Recharts)      │  │  (Recharts Radar)  │ │
│  └──────────────────┘  └────────────────────┘ │
│                                                │
│  ISSUE LIST (Jira-style, filterable):          │
│  ┌──────────────────────────────────────────┐ │
│  │ 🔴 CRIT  SQL Injection in /api/users     │ │
│  │         OWASP A03 | CVE-2024-1337        │ │
│  │         [View Details ▼]                 │ │
│  ├──────────────────────────────────────────┤ │
│  │ 🔴 CRIT  Hardcoded AWS Secret Key        │ │
│  │         CWE-798 | Line 42: config.py     │ │
│  │         [View Details ▼]                 │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  EXPANDED ISSUE DETAIL:                        │
│  ┌──────────────────────────────────────────┐ │
│  │  CODE SNIPPET (syntax highlighted)       │ │
│  │  42 │ AWS_SECRET = "AKIAIOSFODNN7..."    │ │
│  │                                          │ │
│  │  REMEDIATION STEPS                       │ │
│  │  1. Move to env variables                │ │
│  │  2. Rotate the exposed key               │ │
│  │  3. Add .gitignore rule                  │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

---

## 3D Scene — `ThreatGlobe.jsx`

### Setup

```jsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'

export default function ThreatGlobe() {
  return (
    <Canvas
      camera={{ position: [0, 0, 3.5], fov: 50 }}
      style={{ background: 'transparent' }}
    >
      <ambientLight intensity={0.1} />
      <pointLight position={[5, 5, 5]} color="#00f5ff" intensity={2} />
      <Stars radius={100} depth={50} count={3000} factor={3} fade />
      <GlobeMesh />
      <VulnNodes />
      <OrbitRings />
      <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.4} />
    </Canvas>
  )
}
```

### Globe Mesh

```jsx
function GlobeMesh() {
  const texture = useTexture('/assets/globe-texture.jpg')
  return (
    <mesh>
      <sphereGeometry args={[1, 64, 64]} />
      <meshStandardMaterial
        map={texture}
        color="#001a2e"
        emissive="#003355"
        emissiveIntensity={0.3}
        wireframe={false}
      />
    </mesh>
  )
}
```

### Vulnerability Nodes (glowing dots on surface)

```jsx
// Convert lat/lng to 3D sphere coordinates
function latLngToVec3(lat, lng, radius = 1.02) {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lng + 180) * (Math.PI / 180)
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
     radius * Math.cos(phi),
     radius * Math.sin(phi) * Math.sin(theta)
  )
}

// Severity color map
const COLORS = { critical: '#ff2d55', high: '#ff6b00', medium: '#ffaa00', low: '#00f5ff' }

function VulnNodes({ vulns }) {
  return vulns.map((v, i) => {
    const pos = latLngToVec3(v.lat, v.lng)
    return (
      <mesh key={i} position={pos}>
        <sphereGeometry args={[0.015, 8, 8]} />
        <meshStandardMaterial
          color={COLORS[v.severity]}
          emissive={COLORS[v.severity]}
          emissiveIntensity={2}
        />
      </mesh>
    )
  })
}
```

### Orbit Rings

```jsx
function OrbitRings() {
  const ringRef = useRef()
  useFrame((state) => {
    ringRef.current.rotation.z = state.clock.elapsedTime * 0.2
  })
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
  )
}
```

---

## CSS Variables & Global Theme

```css
/* styles/globals.css */
:root {
  --bg-primary:    #020409;
  --bg-surface:    #0a0f1a;
  --bg-panel:      #0d1520;
  --border:        #1a2a3a;
  --border-glow:   #00f5ff33;

  --cyan:          #00f5ff;
  --cyan-dim:      #00a8b5;
  --red:           #ff2d55;
  --amber:         #ffaa00;
  --green:         #00ff87;

  --text-primary:  #e0f0ff;
  --text-dim:      #4a6a8a;
  --text-mono:     'Share Tech Mono', monospace;

  --glow-cyan:     0 0 20px #00f5ff66;
  --glow-red:      0 0 20px #ff2d5566;
}

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--text-mono);
  overflow-x: hidden;
}
```

---

## Key Animations (`animations.css`)

```css
/* Scanner beam sweep */
@keyframes scanBeam {
  0%   { left: -5%; opacity: 0; }
  10%  { opacity: 1; }
  90%  { opacity: 1; }
  100% { left: 105%; opacity: 0; }
}

.scanner-beam {
  position: absolute;
  width: 60px;
  height: 100%;
  background: linear-gradient(90deg, transparent, #00f5ff22, #00f5ff88, #00f5ff22, transparent);
  animation: scanBeam 3s ease-in-out infinite;
}

/* Glitch text effect */
@keyframes glitch1 {
  0%, 100% { clip-path: inset(0 0 95% 0); transform: translate(-4px, 0); }
  50%       { clip-path: inset(30% 0 50% 0); transform: translate(4px, 0); }
}

.glitch-text::before,
.glitch-text::after {
  content: attr(data-text);
  position: absolute;
  top: 0; left: 0;
  color: var(--cyan);
}
.glitch-text::before { animation: glitch1 3s infinite; color: var(--red); }
.glitch-text::after  { animation: glitch1 3s infinite 0.1s; }

/* Pulse ring on CTA */
@keyframes pulseRing {
  0%   { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.6); opacity: 0; }
}

.pulse-ring {
  position: absolute;
  border: 1px solid var(--cyan);
  border-radius: 4px;
  animation: pulseRing 2s ease-out infinite;
}

/* Terminal cursor blink */
@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}
.cursor { animation: blink 1s step-end infinite; }

/* Severity badge glow */
.badge-critical { box-shadow: var(--glow-red); border-color: var(--red); }
.badge-high     { box-shadow: 0 0 12px #ff6b0066; border-color: #ff6b00; }
.badge-medium   { box-shadow: 0 0 12px #ffaa0066; border-color: var(--amber); }
.badge-low      { box-shadow: var(--glow-cyan); border-color: var(--cyan); }
```

---

## Component Specifications

### `GlitchText.jsx`
- Accepts `text` prop
- On mount: scrambles characters with `setInterval`, resolves to real text after 1.2s
- Uses `::before`/`::after` pseudo-elements for RGB-split effect
- Re-triggers on hover

### `TerminalLine.jsx`
- Accepts `lines: string[]` prop
- Types each line character by character at 40ms/char
- Prefix: `> ` in cyan, content in white
- Cursor blinks at end of current line

### `SeverityBadge.jsx`
```jsx
const config = {
  critical: { label: 'CRITICAL', color: '#ff2d55', icon: '●' },
  high:     { label: 'HIGH',     color: '#ff6b00', icon: '●' },
  medium:   { label: 'MEDIUM',   color: '#ffaa00', icon: '●' },
  low:      { label: 'LOW',      color: '#00f5ff', icon: '●' },
}
```

### `IssueList.jsx`
- Filterable by: severity, OWASP category, file path
- Sortable by: CVSS score, severity, file name
- Each row: severity badge | title | OWASP tag | CVE link | file:line | `[Details ▼]`
- Expanded: code snippet (Prism.js highlighted) + remediation checklist

### `ReportCard.jsx`
- 4 counter cards with count-up animation (0 → final value over 1.2s)
- Critical card pulses red glow if count > 0
- Overall grade badge: `A` (0 critical) → `F` (5+ critical)

### `SeverityDonut.jsx`
```jsx
// Recharts PieChart — donut style
<PieChart>
  <Pie data={data} innerRadius={60} outerRadius={90} dataKey="value">
    {data.map((entry) => (
      <Cell key={entry.name} fill={COLORS[entry.name]} />
    ))}
  </Pie>
  <Tooltip contentStyle={{ background: '#0d1520', border: '1px solid #1a2a3a' }} />
</PieChart>
```

### `OWASPRadar.jsx`
```jsx
// Recharts RadarChart — one axis per OWASP Top 10 category
const owaspCategories = [
  'A01 Access Control', 'A02 Cryptography', 'A03 Injection',
  'A04 Insecure Design', 'A05 Misconfiguration', 'A06 Outdated Components',
  'A07 Auth Failures', 'A08 Integrity Failures', 'A09 Logging Failures', 'A10 SSRF'
]
```

---

## State Management (Zustand)

```js
// store/scanStore.js
import { create } from 'zustand'

export const useScanStore = create((set) => ({
  // Upload state
  uploadedFile: null,
  repoUrl: '',
  setUploadedFile: (file) => set({ uploadedFile: file }),

  // Scan state
  scanStatus: 'idle',   // idle | scanning | complete | error
  scanProgress: 0,
  scanLogs: [],
  addLog: (line) => set((s) => ({ scanLogs: [...s.scanLogs, line] })),
  setProgress: (p) => set({ scanProgress: p }),

  // Report state
  report: null,
  setReport: (r) => set({ report: r, scanStatus: 'complete' }),
}))
```

---

## WebSocket Live Scan (`useScanWebSocket.js`)

```js
export function useScanWebSocket(scanId) {
  const { addLog, setProgress, setReport } = useScanStore()

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/scan/${scanId}`)

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'log')      addLog(msg.text)
      if (msg.type === 'progress') setProgress(msg.value)
      if (msg.type === 'complete') setReport(msg.report)
    }

    return () => ws.close()
  }, [scanId])
}
```

---

## API Integration

```js
// Base URL
const API = 'http://localhost:8000'

// Upload codebase
POST /api/scan/upload
  Body: FormData { file: .zip | .tar.gz }
  Response: { scan_id: string }

// Scan from GitHub URL
POST /api/scan/url
  Body: { repo_url: string, branch?: string }
  Response: { scan_id: string }

// Get report
GET /api/report/:scan_id
  Response: {
    summary: { critical: 3, high: 7, medium: 12, low: 24 },
    issues: [
      {
        id: string,
        severity: 'critical' | 'high' | 'medium' | 'low',
        title: string,
        description: string,
        owasp_category: string,
        cve_id?: string,
        cwe_id: string,
        cvss_score: number,
        file: string,
        line: number,
        code_snippet: string,
        remediation: string[],
      }
    ],
    owasp_scores: { [category: string]: number },
    scan_duration_ms: number,
    scanned_files: number,
  }

// WebSocket live progress
WS /ws/scan/:scan_id
  Messages: { type: 'log' | 'progress' | 'complete', ... }
```

---

## Installation & Setup

```bash
# 1. Create Vite + React project
npm create vite@latest vulnbot-frontend -- --template react
cd vulnbot-frontend

# 2. Install dependencies
npm install \
  @react-three/fiber \
  @react-three/drei \
  three \
  framer-motion \
  zustand \
  react-router-dom \
  recharts \
  lucide-react \
  prismjs \
  tailwindcss postcss autoprefixer

# 3. Init Tailwind
npx tailwindcss init -p

# 4. Dev server
npm run dev
```

### `tailwind.config.js`
```js
export default {
  content: ['./src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'cyber-cyan':  '#00f5ff',
        'cyber-red':   '#ff2d55',
        'cyber-amber': '#ffaa00',
        'cyber-green': '#00ff87',
        'bg-dark':     '#020409',
        'bg-panel':    '#0d1520',
      },
      fontFamily: {
        mono: ['"Share Tech Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

### `index.html` — Import Google Fonts
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
```

---

## Vite Config

```js
// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws':  { target: 'ws://localhost:8000', ws: true },
    }
  }
})
```

---

## Performance Notes

- **Globe texture**: Use a compressed WebP at 1024×512px; lazy-load with `React.Suspense`
- **Particle field**: Cap at 800 particles; use `BufferGeometry` not individual `mesh`es
- **Code splitting**: Lazy-load `Report.jsx` and `ThreatGlobe.jsx` — they're heavy
- **Three.js cleanup**: Always `dispose()` geometries and materials in `useEffect` cleanup
- **Animation**: Prefer CSS keyframes over JS setInterval for visual-only effects

```jsx
// Lazy load the heavy 3D scene
const ThreatGlobe = React.lazy(() => import('./components/3d/ThreatGlobe'))

// In JSX:
<Suspense fallback={<div className="globe-placeholder" />}>
  <ThreatGlobe />
</Suspense>
```

---

## Accessibility

- All color indicators have text labels (never color alone for severity)
- `aria-live="polite"` on the scan terminal output
- Reduced motion: wrap all animations in `@media (prefers-reduced-motion: no-preference)`
- Keyboard nav: all interactive elements reachable and focusable
- Globe: `aria-hidden="true"` — it's decorative; content is in the report list

---

## Demo Flow (Pitch Script)

1. **Land on homepage** — Globe spins, particles drift, glitch text resolves: *"Your Code Has Secrets. We Find Them First."*
2. **Click "Start Free Scan"** — Drop zone appears; drag in a ZIP or paste a GitHub URL
3. **Watch the terminal** — Lines scroll: `> Cloning repo...` `> Running Semgrep AST analysis...` `> Checking CVE database...` `> Found 3 critical vulnerabilities`
4. **Progress bar fills red** — Screen flashes on complete
5. **Report page loads** — Report card animates in: `3 CRITICAL  7 HIGH  12 MEDIUM  24 LOW`
6. **Click a critical issue** — SQL injection, code snippet highlighted in red, 3-step remediation
7. **Export PDF** — One-click Jira-style report

---

## Folder Quick Reference

```
src/components/3d/       → All Three.js / R3F components
src/components/upload/   → File drop + scan terminal
src/components/report/   → Report card, issue list, charts
src/components/ui/       → Reusable design system atoms
src/pages/               → Route-level page components
src/store/               → Zustand global state
src/hooks/               → WebSocket, animation hooks
src/styles/              → CSS variables, keyframe animations
```

---

*VulnBot Frontend — Built for security teams who move fast and ship safe.*
