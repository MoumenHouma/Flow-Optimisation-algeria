import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Vehicle } from "@/types";

export function useVehicles() {
  return useQuery({
    queryKey: ["vehicles"],
    queryFn: () => apiFetch<Vehicle[]>("/api/v1/fleet/vehicles"),
  });
}
