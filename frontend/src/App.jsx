import './App.css'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/react'

function App() {
  return (
    <div className="app">
      <header className="site-header">
        <div className="brand">
          <span className="brand-mark">V</span>
          <span className="brand-text">Vulture</span>
        </div>
        <Show when="signed-out">
          <div className="auth-actions">
            <SignInButton>
              <button className="btn ghost" type="button">
                Sign in
              </button>
            </SignInButton>
            <SignUpButton>
              <button className="btn primary" type="button">
                Sign up
              </button>
            </SignUpButton>
          </div>
        </Show>
        <Show when="signed-in">
          <div className="user-shell">
            <UserButton />
          </div>
        </Show>
      </header>
      <main className="hero">
        <div className="hero-content">
          <p className="eyebrow">Github security scan</p>
          <h1>
            Ship faster. <span>Scan deeper.</span>
          </h1>
          <p className="lede">
            Vulture pulls your private repos, runs a hybrid scan, and delivers a
            clean, actionable vulnerability report.
          </p>
          <div className="hero-actions">
            <button className="btn primary" type="button">
              Start free scan
            </button>
            <button className="btn ghost" type="button">
              View docs
            </button>
          </div>
        </div>
        <div className="hero-panel" aria-hidden="true">
          <div className="pulse"></div>
          <div className="panel-grid">
            <div className="panel-card">
              <p className="panel-title">OWASP Coverage</p>
              <p className="panel-value">10 / 10</p>
            </div>
            <div className="panel-card">
              <p className="panel-title">Average scan</p>
              <p className="panel-value">4.6s</p>
            </div>
            <div className="panel-card">
              <p className="panel-title">Critical findings</p>
              <p className="panel-value">0</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App