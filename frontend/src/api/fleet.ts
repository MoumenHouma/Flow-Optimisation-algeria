import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { FleetSummary, Vehicle, VehicleDraft } from "@/types";

export function useVehicles() {
  return useQuery({
    queryKey: ["vehicles"],
    queryFn: () => apiFetch<Vehicle[]>("/api/v1/fleet/vehicles"),
  });
}

export function useFleetSummary() {
  return useQuery({
    queryKey: ["fleet", "summary"],
    queryFn: () => apiFetch<FleetSummary>("/api/v1/fleet/summary"),
  });
}

function useFleetInvalidation() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    void queryClient.invalidateQueries({ queryKey: ["fleet", "summary"] });
  };
}

export function useAddVehicle() {
  const invalidate = useFleetInvalidation();
  return useMutation({
    mutationFn: (draft: VehicleDraft) =>
      apiFetch<Vehicle>("/api/v1/fleet/vehicles", {
        method: "POST",
        body: JSON.stringify(draft),
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateVehicle() {
  const invalidate = useFleetInvalidation();
  return useMutation({
    mutationFn: ({ id, draft }: { id: string; draft: VehicleDraft }) =>
      apiFetch<Vehicle>(`/api/v1/fleet/vehicles/${id}`, {
        method: "PUT",
        body: JSON.stringify(draft),
      }),
    onSuccess: invalidate,
  });
}

export function useDeleteVehicle() {
  const invalidate = useFleetInvalidation();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/fleet/vehicles/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}
