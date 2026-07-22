import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Driver, Territory } from "@/types";

export function useTerritories() {
  return useQuery({
    queryKey: ["territories"],
    queryFn: () => apiFetch<Territory[]>("/api/v1/territories"),
  });
}

export function useDrivers() {
  return useQuery({
    queryKey: ["drivers"],
    queryFn: () => apiFetch<Driver[]>("/api/v1/fleet/drivers"),
  });
}

function useTerritoryInvalidation() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: ["territories"] });
}

export function useAutoGenerate() {
  const invalidate = useTerritoryInvalidation();
  return useMutation({
    mutationFn: (zones?: number) =>
      apiFetch<Territory[]>("/api/v1/territories/auto-generate", {
        method: "POST",
        body: JSON.stringify(zones ? { zones } : {}),
      }),
    onSuccess: invalidate,
  });
}

export function useAssignDriver() {
  const invalidate = useTerritoryInvalidation();
  return useMutation({
    mutationFn: ({ id, driverId }: { id: string; driverId: string | null }) =>
      apiFetch<Territory>(`/api/v1/territories/${id}`, {
        method: "PUT",
        body: JSON.stringify({ driver_user_id: driverId }),
      }),
    onSuccess: invalidate,
  });
}

export function useDeleteTerritory() {
  const invalidate = useTerritoryInvalidation();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/api/v1/territories/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}
