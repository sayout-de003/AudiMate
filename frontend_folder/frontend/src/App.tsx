import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { EmailVerification } from './pages/EmailVerification';
import { Onboarding } from './pages/Onboarding';
import { Dashboard } from './pages/Dashboard';
import { Audits } from './pages/Audits';
import { AuditDetail } from './pages/AuditDetail';
import { Settings } from './pages/Settings';
import { Integrations } from './pages/Integrations';
import { Profile } from './pages/Profile';
import { Billing } from './pages/Billing';
import { GitHubCallback } from './pages/GitHubCallback';
import { AuthLayout } from './layouts/AuthLayout';
import { AppLayout } from './layouts/AppLayout';
import { Loader2 } from 'lucide-react';

const queryClient = new QueryClient();

function ProtectedRoutesWrapper() {
  const { isAuthenticated, isLoading, hasOrganizations } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // If on onboarding page, let them through (they're authenticated but have no org)
  if (location.pathname === '/onboarding') {
    return <Outlet />;
  }

  // Redirect to onboarding if user has no organizations
  if (!hasOrganizations) {
    return <Navigate to="/onboarding" replace />;
  }

  return <AppLayout />;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}


export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
              <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
              <Route path="/verify-email" element={<PublicRoute><EmailVerification /></PublicRoute>} />
              <Route path="/forgot-password" element={<PublicRoute><div className="text-center p-4">Forgot Password (Coming Soon) <br /><a href="/login" className="text-indigo-600">Back to Login</a></div></PublicRoute>} />
            </Route>

            <Route element={<ProtectedRoutesWrapper />}>
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/" element={<Dashboard />} />
              <Route path="/audits" element={<Audits />} />
              <Route path="/audits/:id" element={<AuditDetail />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/integrations" element={<Integrations />} />
              <Route path="/integrations/github/callback" element={<GitHubCallback />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/billing" element={<Billing />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
