import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch, apiUpload } from "@/lib/api-client";
import { enqueueProof, enqueueStatus, flushQueue, type StatusBody } from "@/lib/offline-queue";
import type { DeliveryStatus, DriverRoute, ProofOfDelivery } from "@/types";

export type DriverStatus = "en_route" | "delivered" | "failed";

// The driver's active route (F8). Returns null when nothing is assigned today.
export function useMyRoute() {
  return useQuery({
    queryKey: ["driver", "route"],
    queryFn: () => apiFetch<DriverRoute | null>("/api/v1/driver/route"),
    refetchOnWindowFocus: true,
  });
}

export type CodMethod = "cash" | "baridimob" | "ccp" | "none";

interface StatusInput {
  deliveryId: string;
  status: DriverStatus;
  reason?: string;
  lat?: number;
  lon?: number;
  // F17: cash collected on a delivered COD stop.
  cod_collected?: number;
  cod_method?: CodMethod;
}

// A connectivity failure (offline / network drop) rather than a server rejection.
// ApiError means the server responded, so it is a real error, not an offline case.
function isConnectivityError(err: unknown): boolean {
  return !(err instanceof ApiError);
}

// Optimistically apply a stop's new status to the cached route so the driver can
// advance immediately, whether the update went to the server or the offline queue.
function optimisticRoute(route: DriverRoute | null, deliveryId: string, status: DriverStatus): DriverRoute | null {
  if (!route) return route;
  const stops = route.stops.map((s) =>
    s.delivery_id === deliveryId ? { ...s, status: status as DeliveryStatus } : s,
  );
  const delivered = stops.filter((s) => s.status === "delivered").length;
  return { ...route, stops, delivered };
}

// Phase D: update a stop's status, falling back to the offline queue when there
// is no connectivity so a driver can finish a route with no signal.
export function useUpdateStatus() {
  const queryClient = useQueryClient();
  return useMutation<{ queued: boolean }, unknown, StatusInput, { prev?: DriverRoute | null }>({
    mutationFn: async ({ deliveryId, ...rest }) => {
      const body = rest as StatusBody;
      if (typeof navigator !== "undefined" && navigator.onLine === false) {
        await enqueueStatus(deliveryId, body);
        return { queued: true };
      }
      try {
        await apiFetch(`/api/v1/driver/deliveries/${deliveryId}/status`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
        return { queued: false };
      } catch (err) {
        if (isConnectivityError(err)) {
          await enqueueStatus(deliveryId, body);
          return { queued: true };
        }
        throw err;
      }
    },
    onMutate: async ({ deliveryId, status }) => {
      await queryClient.cancelQueries({ queryKey: ["driver", "route"] });
      const prev = queryClient.getQueryData<DriverRoute | null>(["driver", "route"]);
      queryClient.setQueryData<DriverRoute | null>(["driver", "route"], (r) =>
        optimisticRoute(r ?? null, deliveryId, status),
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx) queryClient.setQueryData(["driver", "route"], ctx.prev);
    },
    onSuccess: (res) => {
      // Online: pull server truth. Queued: keep the optimistic state until sync.
      if (!res.queued) queryClient.invalidateQueries({ queryKey: ["driver", "route"] });
    },
  });
}

// Report the driver's GPS position for live tracking (F18). Fire-and-forget and
// intentionally NOT queued offline — a stale position has no value.
export function useReportLocation() {
  return useMutation({
    mutationFn: ({ lat, lon }: { lat: number; lon: number }) =>
      apiFetch("/api/v1/driver/location", {
        method: "POST",
        body: JSON.stringify({ lat, lon }),
      }),
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
// Phase D: queued offline (before its status update, preserving replay order).
export function useUploadProof() {
  return useMutation<{ queued: boolean } | ProofOfDelivery, unknown, ProofInput>({
    mutationFn: async ({ deliveryId, photo, signature, lat, lon }) => {
      const enqueue = () => enqueueProof({ deliveryId, photo, signature, lat, lon });
      if (typeof navigator !== "undefined" && navigator.onLine === false) {
        await enqueue();
        return { queued: true };
      }
      const form = new FormData();
      if (photo) form.append("photo", photo, "photo.jpg");
      if (signature) form.append("signature", signature, "signature.png");
      if (lat != null) form.append("lat", String(lat));
      if (lon != null) form.append("lon", String(lon));
      try {
        return await apiUpload<ProofOfDelivery>(`/api/v1/driver/deliveries/${deliveryId}/proof`, form);
      } catch (err) {
        if (isConnectivityError(err)) {
          await enqueue();
          return { queued: true };
        }
        throw err;
      }
    },
  });
}

// Re-exported so callers can nudge a sync (e.g. after a successful online action).
export { flushQueue };
