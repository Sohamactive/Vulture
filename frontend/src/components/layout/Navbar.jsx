import { Link, useLocation, useNavigate } from 'react-router-dom';
import GlitchText from '../ui/GlitchText';
import { Terminal, FileDown, LayoutDashboard, MessageCircle } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
import { useAuthToken } from '../../lib/useAuthToken';
import { exportReport } from '../../lib/api';

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const isReportPage = location.pathname.includes('/report');
  const isDashboardPage = location.pathname === '/dashboard';
  const { getToken } = useAuthToken();

  // Extract scanId from report/chat URL for export and navigation
  const scanIdMatch = location.pathname.match(/\/(?:report|chat)\/(.+)/);
  const currentScanId = scanIdMatch ? scanIdMatch[1] : null;

  const handleExport = async () => {
    if (!currentScanId) return;
    try {
      const token = await getToken();
      if (!token) return;
      const data = await exportReport(token, currentScanId, 'json');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vulture-report-${currentScanId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const handleChatNavigate = () => {
    if (currentScanId) {
      navigate(`/chat/${currentScanId}`);
      return;
    }

    const entered = window.prompt('Enter a scan ID to open DevSecOps chat:');
    const trimmed = entered ? entered.trim() : '';
    if (trimmed) navigate(`/chat/${trimmed}`);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 px-3 sm:px-6 pt-3">
      <div className="max-w-7xl mx-auto">
        <div className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[linear-gradient(135deg,rgba(13,21,32,0.95),rgba(10,15,26,0.9))] backdrop-blur-md shadow-[0_0_30px_rgba(0,245,255,0.08)]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(0,245,255,0.12),transparent_40%)]" />
          <div className="relative flex items-center justify-between h-16 px-4 sm:px-6">
            <Link to="/" className="flex items-center gap-2 text-[var(--cyan)] hover:text-[var(--cyan-dim)] transition-colors">
              <Terminal size={24} />
              <span className="font-bold text-xl tracking-wider">
                <GlitchText text="VultureAI" />
              </span>
            </Link>
            
            <div className="flex items-center gap-4 sm:gap-6">
              {isReportPage ? (
                <button
                  onClick={handleExport}
                  className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase"
                >
                  <FileDown size={16} /> Export JSON
                </button>
              ) : (
                <a href="#docs" className="text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase">Docs</a>
              )}

              <SignedIn>
                <Link
                  to="/dashboard"
                  className={`flex items-center gap-2 text-sm font-bold tracking-wider transition-colors uppercase ${
                    isDashboardPage
                      ? 'text-[var(--cyan)]'
                      : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
                  }`}
                >
                  <LayoutDashboard size={16} /> Dashboard
                </Link>
              </SignedIn>

              <div className="h-6 w-px bg-[var(--border)]"></div>
              <SignedIn>
                <button
                  onClick={handleChatNavigate}
                  className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase"
                >
                  <MessageCircle size={16} /> Chat
                </button>
              </SignedIn>

              <div className="h-6 w-px bg-[var(--border)] mx-2"></div>

              <SignedOut>
                <SignInButton mode="modal">
                  <button className="border border-[var(--cyan)] text-[var(--cyan)] px-4 py-1.5 text-xs font-bold tracking-widest uppercase rounded-full hover:bg-[#00f5ff1a] hover:shadow-[var(--glow-cyan)] transition-all">
                    GitHub Login
                  </button>
                </SignInButton>
              </SignedOut>
              <SignedIn>
                <UserButton 
                  appearance={{
                    elements: {
                      userButtonAvatarBox: "w-8 h-8 border border-[var(--cyan)] shadow-[var(--glow-cyan)]"
                    }
                  }}
                />
              </SignedIn>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
