import { Link, useLocation, useParams } from 'react-router-dom';
import GlitchText from '../ui/GlitchText';
import { Terminal, FileDown, ExternalLink, LayoutDashboard } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
import { useAuthToken } from '../../lib/useAuthToken';
import { exportReport } from '../../lib/api';

export default function Navbar() {
  const location = useLocation();
  const isReportPage = location.pathname.includes('/report');
  const isDashboardPage = location.pathname === '/dashboard';
  const { getToken } = useAuthToken();

  // Extract scanId from report URL for export
  const scanIdMatch = location.pathname.match(/\/report\/(.+)/);
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

  return (
    <nav className="w-full border-b border-solid border-[var(--border)] bg-[var(--bg-surface)] bg-opacity-80 backdrop-blur-sm fixed top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center gap-2 text-[var(--cyan)] hover:text-[var(--cyan-dim)] transition-colors">
              <Terminal size={24} />
              <span className="font-bold text-xl tracking-wider">
                <GlitchText text="VultureAI" />
              </span>
            </Link>
          </div>
          
          <div className="flex items-center gap-6">
            {isReportPage ? (
              <>
                <button
                  onClick={handleExport}
                  className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase"
                >
                  <FileDown size={16} /> Export JSON
                </button>
              </>
            ) : (
              <>
                <a href="#docs" className="text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase">Docs</a>
                <a href="#api" className="text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase">API</a>
              </>
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

            <div className="h-6 w-px bg-[var(--border)] mx-2"></div>

            <SignedOut>
              <SignInButton mode="modal">
                <button className="border border-[var(--cyan)] text-[var(--cyan)] px-4 py-1.5 text-xs font-bold tracking-widest uppercase hover:bg-[#00f5ff1a] hover:shadow-[var(--glow-cyan)] transition-all">
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
    </nav>
  );
}
