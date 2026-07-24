import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { BillingPage } from "@/features/billing/BillingPage";
import { CodReconciliationPage } from "@/features/cod/CodReconciliationPage";
import { FuelPage } from "@/features/fuel/FuelPage";
import { AuditLogPage } from "@/features/settings/AuditLogPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { DriverPage } from "@/features/driver/DriverPage";
import { OptimizationPage } from "@/features/optimization/OptimizationPage";
import { ImportPage } from "@/features/import/ImportPage";
import { FleetPage } from "@/features/fleet/FleetPage";
import { DevelopersPage } from "@/features/settings/DevelopersPage";
import { TerritoriesPage } from "@/features/territories/TerritoriesPage";
import { LiveTrackingPage } from "@/features/tracking/LiveTrackingPage";
import { TrackPage } from "@/features/track/TrackPage";

// Public auth routes + a protected shell (Layout) wrapping the app (DESIGN §3).
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      {/* F18: public customer tracking link — no auth, its own bare shell. */}
      <Route path="/track/:token" element={<TrackPage />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/import" element={<ImportPage />} />
        <Route path="/optimize" element={<OptimizationPage />} />
        <Route path="/fleet" element={<FleetPage />} />
        <Route path="/territories" element={<TerritoriesPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/tracking" element={<LiveTrackingPage />} />
        <Route path="/cod" element={<CodReconciliationPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/fuel" element={<FuelPage />} />
        <Route path="/developers" element={<DevelopersPage />} />
        <Route path="/audit-log" element={<AuditLogPage />} />
      </Route>

      {/* Driver PWA (F8) — mobile, its own shell, outside the manager layout. */}
      <Route
        path="/driver"
        element={
          <ProtectedRoute>
            <DriverPage />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
