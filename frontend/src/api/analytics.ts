import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Performance, Trends } from "@/types";

// Daily delivered/failed + routes/distance over the window (F11).
export function useTrends(days: number) {
  return useQuery({
    queryKey: ["analytics", "trends", days],
    queryFn: () => apiFetch<Trends>(`/api/v1/analytics/trends?days=${days}`),
  });
}

// Success rate, failure reasons and per-driver leaderboard (F11).
export function usePerformance(days: number) {
  return useQuery({
    queryKey: ["analytics", "performance", days],
    queryFn: () => apiFetch<Performance>(`/api/v1/analytics/performance?days=${days}`),
  });
}
