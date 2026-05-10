# Vulture

An intelligent, multi-stage code vulnerability scanning platform that combines traditional static application security testing (SAST) with advanced AI-driven contextual evaluation. 

Vulture uses tools like **Semgrep** and **Tree-sitter** for deep structural codebase analysis and orchestrates complex verification workflows using **LangGraph** and Large Language Models (LLMs) to reduce false positives and prioritize real security threats.

---

## 🏗️ Architecture

The project consists of a full-stack application separated into frontend and backend directories:

* **Frontend:** A modern, interactive React application built with Vite, Tailwind CSS, and Framer Motion. Uses Clerk for authentication and features rich data visualization for vulnerability reports.
* **Backend:** A FastAPI Python service that handles codebase parsing, AST generation, pattern matching, and AI-based vulnerability verification. It integrates LangGraph to manage complex, multi-agent workflows.

## ✨ Key Features

* **Multi-Engine Scanning**: Combines Tree-sitter for Abstract Syntax Tree (AST) analysis and Semgrep for fast security pattern matching.
* **AI-Assisted Verification**: Significantly reduces false positives by feeding static analysis results into an LLM (via AWS Bedrock or OpenAI) for contextual validation and exploitability scoring.
* **Rich Security Dashboard**: Detailed interactive visualizations for security scores, vulnerability breakdowns, and remediation priorities using Recharts.
* **Real-time Streaming**: Progressive streaming of scan progress and intermediate results via WebSockets.
* **Comprehensive Reporting**: Generates detailed, actionable vulnerability reports with suggested remediations and priority rankings.

## 💻 Tech Stack

### Frontend (`/frontend`)
* **Core:** React 19, Vite
* **Styling & UI:** Tailwind CSS v4, Framer Motion, React Three Fiber / Drei
* **Authentication:** Clerk
* **State Management:** Zustand
* **Data Visualization:** Recharts

### Backend (`/backend`)
* **Core:** Python 3.12+, FastAPI
* **AI & Orchestration:** LangGraph, LangChain, OpenAI / AWS Bedrock
* **Code Analysis:** Semgrep, Tree-sitter
* **Database:** SQLite, SQLAlchemy, Alembic

---

## 🚀 Getting Started

### Prerequisites
* Node.js (v18+)
* Python 3.12+
* [uv](https://github.com/astral-sh/uv) (recommended Python package manager)

### 1. Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create your environment variables file based on the example:
   ```bash
   cp .env.example .env
   ```
   *Configure your AWS Bedrock/OpenAI API keys and Clerk secret keys in `.env`.*
3. Install dependencies using `uv`:
   ```bash
   uv sync
   ```
4. Run database migrations:
   ```bash
   uv run alembic upgrade head
   ```
5. Start the backend server:
   ```bash
   uv run uvicorn main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

### 2. Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Create your environment variables file based on the example:
   ```bash
   cp .env.example .env
   ```
   *Add your `VITE_CLERK_PUBLISHABLE_KEY` here.*
3. Install dependencies:
   ```bash
   npm install
   ```
4. Start the development server:
   ```bash
   npm run dev
   ```
   The UI will be accessible at `http://localhost:5173`.

---

## 🛡️ Usage

1. **Log In:** Access the frontend application and authenticate using Clerk.
2. **Initiate Scan:** Provide a local repository path to the application to begin a security scan.
3. **Monitor Progress:** The dashboard will stream real-time updates as the backend runs code parsing, Semgrep rules, and AI evaluations.
4. **Review Report:** Once complete, review the comprehensive vulnerability report, check the priority scores, and begin remediation based on the provided fixes.
