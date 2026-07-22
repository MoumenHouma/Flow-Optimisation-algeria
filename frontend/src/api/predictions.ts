import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { ServiceTimeModel } from "@/types";

// Service-time ML model summary (F13).
export function useServiceTimeModel() {
  return useQuery({
    queryKey: ["predictions", "service-time"],
    queryFn: () => apiFetch<ServiceTimeModel>("/api/v1/predictions/service-time"),
  });
}

export function useTrainServiceTime() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<ServiceTimeModel>("/api/v1/predictions/service-time/train", { method: "POST" }),
    onSuccess: (data) => qc.setQueryData(["predictions", "service-time"], data),
  });
}
