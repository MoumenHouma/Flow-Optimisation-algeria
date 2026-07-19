import { useMutation, useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { OptimizeResponse, RouteResult } from "@/types";

interface OptimizeInput {
  deliveryIds: string[];
  vehicleIds: string[];
}

// Submit an optimization job (F3).
export function useOptimize() {
  return useMutation({
    mutationFn: (input: OptimizeInput) =>
      apiFetch<OptimizeResponse>("/api/v1/routes/optimize", {
        method: "POST",
        body: JSON.stringify({
          delivery_ids: input.deliveryIds,
          vehicle_ids: input.vehicleIds,
        }),
      }),
  });
}

// Poll a job until completion (docs/RULES.md §3.2 pattern).
export function useOptimizationJob(jobId: string | null) {
  return useQuery({
    queryKey: ["optimization", jobId],
    queryFn: () => apiFetch<RouteResult>(`/api/v1/routes/${jobId}`),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2000;
    },
  });
}
