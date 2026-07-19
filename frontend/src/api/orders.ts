import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Delivery } from "@/types";

// Routable deliveries: geocoded and not yet assigned to a route.
export function useRoutableDeliveries() {
  return useQuery({
    queryKey: ["deliveries", "routable"],
    queryFn: () => apiFetch<Delivery[]>("/api/v1/orders"),
  });
}
