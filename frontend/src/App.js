import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";

// Pages
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import SetupWizard from "@/pages/SetupWizard";
import Dashboard from "@/pages/Dashboard";
import TransactionsPage from "@/pages/TransactionsPage";
import MileagePage from "@/pages/MileagePage";
import ChargingPage from "@/pages/ChargingPage";
import SisterModule from "@/pages/SisterModule";
import SettingsPage from "@/pages/SettingsPage";
import TaxProjectionPage from "@/pages/TaxProjectionPage";
import Layout from "@/components/Layout";

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading, setupCompleted } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Redirect to setup wizard if setup not completed
  if (!setupCompleted && window.location.pathname !== "/setup") {
    return <Navigate to="/setup" replace />;
  }

  return children;
}

// Auth Route - Redirect to dashboard if already logged in
function AuthRoute({ children }) {
  const { isAuthenticated, loading, setupCompleted } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    if (!setupCompleted) {
      return <Navigate to="/setup" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<AuthRoute><LoginPage /></AuthRoute>} />
      <Route path="/register" element={<AuthRoute><RegisterPage /></AuthRoute>} />
      
      {/* Setup Wizard (after auth, before dashboard) */}
      <Route path="/setup" element={<ProtectedRoute><SetupWizard /></ProtectedRoute>} />
      
      {/* Protected Routes with Layout */}
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="mileage" element={<MileagePage />} />
        <Route path="charging" element={<ChargingPage />} />
        <Route path="sister" element={<SisterModule />} />
        <Route path="tax-projection" element={<TaxProjectionPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      
      {/* Catch all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App dark">
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
