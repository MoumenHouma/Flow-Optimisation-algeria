import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Billing, Invoice, Plan } from "@/types";

// Current plan, price and usage-vs-quota (F19).
export function useBilling() {
  return useQuery({
    queryKey: ["billing"],
    queryFn: () => apiFetch<Billing>("/api/v1/billing"),
  });
}

// Billing history, newest period first (F19).
export function useInvoices() {
  return useQuery({
    queryKey: ["billing", "invoices"],
    queryFn: () => apiFetch<Invoice[]>("/api/v1/billing/invoices"),
  });
}

// Change the company plan (admin) — applies the tier's caps immediately (F19).
export function useChangePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (plan: Plan) =>
      apiFetch<Billing>("/api/v1/billing/plan", {
        method: "PUT",
        body: JSON.stringify({ plan }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing"] });
    },
  });
}
