import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Depot, DepotDraft } from "@/types";

// Depots (F12 multi-dépôt).
export function useDepots() {
  return useQuery({
    queryKey: ["depots"],
    queryFn: () => apiFetch<Depot[]>("/api/v1/fleet/depots"),
  });
}

function useDepotInvalidation() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: ["depots"] });
}

export function useAddDepot() {
  const invalidate = useDepotInvalidation();
  return useMutation({
    mutationFn: (draft: DepotDraft) =>
      apiFetch<Depot>("/api/v1/fleet/depots", { method: "POST", body: JSON.stringify(draft) }),
    onSuccess: invalidate,
  });
}

export function useDeleteDepot() {
  const invalidate = useDepotInvalidation();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/api/v1/fleet/depots/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}
