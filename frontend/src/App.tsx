import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { OptimizationPage } from "@/features/optimization/OptimizationPage";
import { ImportPage } from "@/features/import/ImportPage";
import { FleetPage } from "@/features/fleet/FleetPage";

// Route map mirrors the flows in docs/DESIGN.md §3. Public: /login, /register.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/import"
        element={
          <ProtectedRoute>
            <ImportPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/optimize"
        element={
          <ProtectedRoute>
            <OptimizationPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/fleet"
        element={
          <ProtectedRoute>
            <FleetPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
