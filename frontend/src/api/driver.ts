import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { DriverRoute } from "@/types";

export type DriverStatus = "en_route" | "delivered" | "failed";

// The driver's active route (F8). Returns null when nothing is assigned today.
export function useMyRoute() {
  return useQuery({
    queryKey: ["driver", "route"],
    queryFn: () => apiFetch<DriverRoute | null>("/api/v1/driver/route"),
    refetchOnWindowFocus: true,
  });
}

interface StatusInput {
  deliveryId: string;
  status: DriverStatus;
  reason?: string;
  lat?: number;
  lon?: number;
}

export function useUpdateStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deliveryId, ...body }: StatusInput) =>
      apiFetch(`/api/v1/driver/deliveries/${deliveryId}/status`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["driver", "route"] }),
  });
}
