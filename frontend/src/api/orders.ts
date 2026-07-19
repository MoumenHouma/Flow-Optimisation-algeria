import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { BulkCreateResponse, Delivery, DeliveryDraft } from "@/types";

// Routable deliveries: geocoded and not yet assigned to a route.
export function useRoutableDeliveries() {
  return useQuery({
    queryKey: ["deliveries", "routable"],
    queryFn: () => apiFetch<Delivery[]>("/api/v1/orders"),
  });
}

// Bulk-create deliveries from an import (F1). The server geocodes address-only rows.
export function useCreateDeliveries() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items: DeliveryDraft[]) =>
      apiFetch<BulkCreateResponse>("/api/v1/orders", {
        method: "POST",
        body: JSON.stringify(items),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["deliveries", "routable"] }),
  });
}
