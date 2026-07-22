import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { FuelStation, FuelStatus, GeoPoint } from "@/types";

// Fuel stations for the company (F20).
export function useFuelStations() {
  return useQuery({
    queryKey: ["fuel", "stations"],
    queryFn: () => apiFetch<FuelStation[]>("/api/v1/fuel/stations"),
  });
}

interface StationDraft {
  name: string;
  location: GeoPoint;
  fuel_types?: string;
}

// Add a fuel station (manager) (F20).
export function useCreateStation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draft: StationDraft) =>
      apiFetch<FuelStation>("/api/v1/fuel/stations", {
        method: "POST",
        body: JSON.stringify(draft),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fuel"] }),
  });
}

// Update a station's live availability (F20).
export function useSetStationStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: FuelStatus }) =>
      apiFetch<FuelStation>(`/api/v1/fuel/stations/${id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["fuel"] }),
  });
}
