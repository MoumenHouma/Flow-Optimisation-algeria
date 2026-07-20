import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, apiUpload } from "@/lib/api-client";
import type { DriverRoute, ProofOfDelivery } from "@/types";

export type DriverStatus = "en_route" | "delivered" | "failed";

// The driver's active route (F8). Returns null when nothing is assigned today.
export function useMyRoute() {
  return useQuery({
    queryKey: ["driver", "route"],
    queryFn: () => apiFetch<DriverRoute | null>("/api/v1/driver/route"),
    refetchOnWindowFocus: true,
  });
}

interface StatusInput {
  deliveryId: string;
  status: DriverStatus;
  reason?: string;
  lat?: number;
  lon?: number;
}

export function useUpdateStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deliveryId, ...body }: StatusInput) =>
      apiFetch(`/api/v1/driver/deliveries/${deliveryId}/status`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["driver", "route"] }),
  });
}

interface ProofInput {
  deliveryId: string;
  photo?: Blob;
  signature?: Blob;
  lat?: number;
  lon?: number;
}

// Upload proof of delivery (photo/signature) for a stop (F8, SCHEMA §5.3).
export function useUploadProof() {
  return useMutation({
    mutationFn: ({ deliveryId, photo, signature, lat, lon }: ProofInput) => {
      const form = new FormData();
      if (photo) form.append("photo", photo, "photo.jpg");
      if (signature) form.append("signature", signature, "signature.png");
      if (lat != null) form.append("lat", String(lat));
      if (lon != null) form.append("lon", String(lon));
      return apiUpload<ProofOfDelivery>(`/api/v1/driver/deliveries/${deliveryId}/proof`, form);
    },
  });
}
