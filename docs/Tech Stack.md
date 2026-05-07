# Vulture — Complete Technology Stack

> **Version:** 1.0  
> **Last Updated:** 2026-05-07  
> **Architecture:** AWS Bedrock + FastAPI + React + PostgreSQL

---

## Table of Contents

1. [Frontend Stack](#frontend-stack)
2. [Backend Stack](#backend-stack)
3. [Code Analysis Stack](#code-analysis-stack)
4. [AI & Vulnerability Detection](#ai--vulnerability-detection)
5. [Data Storage](#data-storage)
6. [Authentication & Security](#authentication--security)
7. [DevOps & Deployment Stack](#devops--deployment-stack)
8. [Development Tools](#development-tools)
9. [Testing Stack](#testing-stack)
10. [Performance & Optimization](#performance--optimization)
11. [Development Workflow](#development-workflow)
12. [Production Deployment Checklist](#production-deployment-checklist)

---

## Frontend Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Runtime** | Node.js | 18+ | JavaScript runtime |
| **Build Tool** | Vite | 5.x | Lightning-fast bundler & dev server |
| **Framework** | React | 18.x | UI component library |
| **Routing** | React Router | v6 | Client-side routing |
| **3D Graphics** | Three.js | r128+ | 3D globe & particle effects |
| **3D React Binding** | @react-three/fiber | 8.x | React abstraction for Three.js |
| **3D Utilities** | @react-three/drei | 9.x | Ready-made 3D components |
| **State Management** | Zustand | 4.x | Lightweight global state store |
| **Animation** | Framer Motion | 10.x | Declarative animations |
| **Charts** | Recharts | 2.x | Responsive severity & OWASP charts |
| **UI Components** | Lucide React | 0.x | Icon library (200+ icons) |
| **Styling** | Tailwind CSS | 3.x | Utility-first CSS framework |
| **Syntax Highlighting** | Prism.js | 1.x | Code snippet rendering |
| **HTTP Client** | Axios / Fetch | native | API communication |
| **Form Validation** | React Hook Form | 7.x | Lightweight form handling |
| **Auth Integration** | @clerk/clerk-react | 4.x | Clerk SDK for auth UI |
| **WebSocket** | Socket.IO Client | 4.x | Real-time scan progress |
| **Code Quality** | ESLint | 9.x | Linting rules |
| **Code Quality** | Prettier | 3.x | Code formatting |
| **Package Manager** | npm / pnpm | 9.x+ | Dependency management |

### Frontend `package.json` Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "zustand": "^4.4.0",
    "framer-motion": "^10.16.0",
    "@react-three/fiber": "^8.13.0",
    "@react-three/drei": "^9.88.0",
    "three": "^r128",
    "recharts": "^2.10.0",
    "lucide-react": "^0.292.0",
    "tailwindcss": "^3.3.0",
    "prismjs": "^1.29.0",
    "axios": "^1.6.0",
    "react-hook-form": "^7.50.0",
    "@clerk/clerk-react": "^4.29.0",
    "socket.io-client": "^4.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "eslint": "^8.54.0",
    "prettier": "^3.1.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}



fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
pydantic==2.5.0
pydantic-settings==2.1.0
PyJWT==2.8.1
httpx==0.25.2
GitPython==3.13.0
tree-sitter==0.20.4
semgrep==1.46.0
boto3==1.34.0
python-dotenv==1.0.0
websockets==12.0
celery==5.3.4
redis==5.0.1
cryptography==41.0.7
python-multipart==0.0.6
email-validator==2.1.0