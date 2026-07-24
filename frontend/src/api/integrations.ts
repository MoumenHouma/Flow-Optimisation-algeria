import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { ApiKey, ApiKeyCreated, Webhook, WebhookCreated } from "@/types";

// ---- API keys (F10) ----
export function useApiKeys() {
  return useQuery({
    queryKey: ["api-keys"],
    queryFn: () => apiFetch<ApiKey[]>("/api/v1/integrations/api-keys"),
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; scope: string }) =>
      apiFetch<ApiKeyCreated>("/api/v1/integrations/api-keys", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/integrations/api-keys/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

// ---- Webhooks (F10) ----
export function useWebhooks() {
  return useQuery({
    queryKey: ["webhooks"],
    queryFn: () => apiFetch<Webhook[]>("/api/v1/integrations/webhooks"),
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { url: string; events: string[] }) =>
      apiFetch<WebhookCreated>("/api/v1/integrations/webhooks", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/integrations/webhooks/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}
