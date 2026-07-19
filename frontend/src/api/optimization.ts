import { useMutation, useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { JobResult, OptimizeResponse, RouteResult } from "@/types";

interface OptimizeInput {
  deliveryIds?: string[];
  vehicleIds?: string[];
}

// Submit an optimization job (F3). Empty ids => all routable / all active.
export function useOptimize() {
  return useMutation({
    mutationFn: (input: OptimizeInput = {}) =>
      apiFetch<OptimizeResponse>("/api/v1/routes/optimize", {
        method: "POST",
        body: JSON.stringify({
          delivery_ids: input.deliveryIds ?? [],
          vehicle_ids: input.vehicleIds ?? [],
        }),
      }),
  });
}

// Poll a job until it completes/fails (docs/RULES.md §3.2 polling pattern).
export function useOptimizationJob(jobId: string | null) {
  return useQuery({
    queryKey: ["optimization-job", jobId],
    queryFn: () => apiFetch<JobResult>(`/api/v1/routes/jobs/${jobId}`),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2000;
    },
  });
}

export function useRoute(routeId: string | null) {
  return useQuery({
    queryKey: ["route", routeId],
    queryFn: () => apiFetch<RouteResult>(`/api/v1/routes/${routeId}`),
    enabled: Boolean(routeId),
  });
}
