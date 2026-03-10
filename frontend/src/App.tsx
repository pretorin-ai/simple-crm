import { lazy, Suspense } from 'react';
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute, AdminProtectedRoute } from "./components/ProtectedRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Loader2 } from "lucide-react";

// Lazy-loaded pages
const Login = lazy(() => import('./pages/Login'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ContactsList = lazy(() => import('./pages/ContactsList'));
const ContactDetail = lazy(() => import('./pages/ContactDetail'));
const AccountsList = lazy(() => import('./pages/AccountsList'));
const AccountDetail = lazy(() => import('./pages/AccountDetail'));
const OpportunitiesList = lazy(() => import('./pages/OpportunitiesList'));
const OpportunityDetail = lazy(() => import('./pages/OpportunityDetail'));
const Pipeline = lazy(() => import('./pages/Pipeline'));
const VehiclesList = lazy(() => import('./pages/VehiclesList'));
const VehicleDetail = lazy(() => import('./pages/VehicleDetail'));
const ComplianceList = lazy(() => import('./pages/ComplianceList'));
const UserManagement = lazy(() => import('./pages/UserManagement'));
const ApiSettings = lazy(() => import('./pages/ApiSettings'));
const NotFound = lazy(() => import('./pages/NotFound'));

function PageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

const App = () => (
  <ErrorBoundary>
    <TooltipProvider>
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/pipeline" element={<ProtectedRoute><Pipeline /></ProtectedRoute>} />
              <Route path="/opportunities" element={<ProtectedRoute><OpportunitiesList /></ProtectedRoute>} />
              <Route path="/opportunities/:id" element={<ProtectedRoute><OpportunityDetail /></ProtectedRoute>} />
              <Route path="/accounts" element={<ProtectedRoute><AccountsList /></ProtectedRoute>} />
              <Route path="/accounts/:id" element={<ProtectedRoute><AccountDetail /></ProtectedRoute>} />
              <Route path="/contacts" element={<ProtectedRoute><ContactsList /></ProtectedRoute>} />
              <Route path="/contacts/:id" element={<ProtectedRoute><ContactDetail /></ProtectedRoute>} />
              <Route path="/vehicles" element={<ProtectedRoute><VehiclesList /></ProtectedRoute>} />
              <Route path="/vehicles/:id" element={<ProtectedRoute><VehicleDetail /></ProtectedRoute>} />
              <Route path="/compliance" element={<ProtectedRoute><ComplianceList /></ProtectedRoute>} />
              <Route path="/users" element={<AdminProtectedRoute><UserManagement /></AdminProtectedRoute>} />
              <Route path="/api-settings" element={<ProtectedRoute><ApiSettings /></ProtectedRoute>} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </ErrorBoundary>
);

export default App;
