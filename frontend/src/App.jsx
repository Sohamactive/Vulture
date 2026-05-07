import { Routes, Route } from 'react-router-dom'
import Navbar from './components/layout/Navbar'
import Landing from './pages/Landing'
import Scan from './pages/Scan'
import Report from './pages/Report'
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react'

// ProtectedRoute component requires auth
function ProtectedRoute({ children }) {
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut><RedirectToSignIn /></SignedOut>
    </>
  );
}

function App() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] font-mono flex flex-col">
      <Navbar />
      <div className="pt-16 flex-grow relative"> {/* Offset for fixed Navbar */}
        <Routes>
          {/* Public Route */}
          <Route path="/" element={<Landing />} />
          
          {/* Protected Routes */}
          <Route path="/scan" element={<ProtectedRoute><Scan /></ProtectedRoute>} />
          <Route path="/report/:scanId" element={<ProtectedRoute><Report /></ProtectedRoute>} />
        </Routes>
      </div>
    </div>
  )
}

export default App
