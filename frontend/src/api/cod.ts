import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { CodPayment, CodStatus, CodSummary } from "@/types";

// Driver × day reconciliation totals (F17).
export function useCodSummary() {
  return useQuery({
    queryKey: ["cod", "summary"],
    queryFn: () => apiFetch<CodSummary>("/api/v1/cod/summary"),
  });
}

// Individual COD records, newest first (F17).
export function useCodPayments() {
  return useQuery({
    queryKey: ["cod", "payments"],
    queryFn: () => apiFetch<CodPayment[]>("/api/v1/cod/payments"),
  });
}

// Mark a record reconciled or flag a discrepancy (F17).
export function useReconcileCod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: string;
      status: Extract<CodStatus, "reconciled" | "discrepancy">;
    }) =>
      apiFetch<CodPayment>(`/api/v1/cod/payments/${id}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cod"] });
    },
  });
}
