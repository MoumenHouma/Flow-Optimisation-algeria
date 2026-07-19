import { Route, Routes } from "react-router-dom";

import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { OptimizationPage } from "@/features/optimization/OptimizationPage";
import { ImportPage } from "@/features/import/ImportPage";
import { FleetPage } from "@/features/fleet/FleetPage";

// Route map mirrors the flows in docs/DESIGN.md §3.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/import" element={<ImportPage />} />
      <Route path="/optimize" element={<OptimizationPage />} />
      <Route path="/fleet" element={<FleetPage />} />
    </Routes>
  );
}
