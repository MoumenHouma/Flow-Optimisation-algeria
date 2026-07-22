import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { CodReconciliationPage } from "@/features/cod/CodReconciliationPage";
import { AuditLogPage } from "@/features/settings/AuditLogPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { DriverPage } from "@/features/driver/DriverPage";
import { OptimizationPage } from "@/features/optimization/OptimizationPage";
import { ImportPage } from "@/features/import/ImportPage";
import { FleetPage } from "@/features/fleet/FleetPage";
import { DevelopersPage } from "@/features/settings/DevelopersPage";
import { TerritoriesPage } from "@/features/territories/TerritoriesPage";

// Public auth routes + a protected shell (Layout) wrapping the app (DESIGN §3).
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

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
        <Route path="/cod" element={<CodReconciliationPage />} />
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
