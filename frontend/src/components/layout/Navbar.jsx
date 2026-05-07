import { Link, useLocation } from 'react-router-dom';
import GlitchText from '../ui/GlitchText';
import { Terminal, FileDown, ExternalLink } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';

export default function Navbar() {
  const location = useLocation();
  const isReportPage = location.pathname.includes('/report');

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
            {!isReportPage ? (
              <>
                <a href="#docs" className="text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase">Docs</a>
                <a href="#api" className="text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase">API</a>
              </>
            ) : (
              <>
                <button className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase">
                  <FileDown size={16} /> Export PDF
                </button>
                <button className="flex items-center gap-2 text-sm font-bold tracking-wider text-[var(--text-dim)] hover:text-[var(--cyan)] transition-colors uppercase">
                  <ExternalLink size={16} /> Open Jira
                </button>
              </>
            )}

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
