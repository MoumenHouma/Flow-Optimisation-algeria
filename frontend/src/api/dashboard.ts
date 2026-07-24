import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { DashboardSummary } from "@/types";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => apiFetch<DashboardSummary>("/api/v1/dashboard/summary"),
  });
}
