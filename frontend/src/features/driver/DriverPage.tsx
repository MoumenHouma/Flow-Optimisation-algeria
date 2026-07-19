import { CheckCircle, Navigation, Phone, XCircle, Loader2, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { type DriverStatus, useMyRoute, useUpdateStatus } from "@/api/driver";
import { useAuthStore } from "@/stores/auth-store";
import type { DriverStop } from "@/types";

// Driver PWA (F8) — docs/DESIGN.md §3.4. Mobile-first; its own shell (no manager nav).
export function DriverPage() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const { data: route, isLoading } = useMyRoute();
  const update = useUpdateStatus();

  const logout = () => {
    clear();
    navigate("/login", { replace: true });
  };

  const current = route?.stops.find((s) => s.status !== "delivered" && s.status !== "failed");

  const act = async (stop: DriverStop, status: DriverStatus) => {
    const pos = await currentPosition();
    update.mutate({ deliveryId: stop.delivery_id, status, ...pos });
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col bg-neutral-50">
      <header className="sticky top-0 flex items-center justify-between bg-white px-4 py-3 shadow-sm">
        <span className="font-bold text-primary">RouteOpt 📦</span>
        <button onClick={logout} aria-label="Déconnexion" className="rounded p-1 text-neutral-500">
          <LogOut className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      <main className="flex-1 p-4">
        {isLoading && <p className="text-neutral-500">Chargement…</p>}

        {!isLoading && !route && (
          <p className="mt-8 text-center text-neutral-500">Aucune tournée assignée aujourd'hui.</p>
        )}

        {route && (
          <>
            <section className="rounded-lg bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h1 className="font-semibold">🚐 {route.vehicle_name ?? "Ma tournée"}</h1>
                <span className="font-mono text-sm text-neutral-500">
                  {route.delivered}/{route.total}
                </span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-neutral-200">
                <div
                  className="h-full bg-success transition-all"
                  style={{ width: `${route.total ? (route.delivered / route.total) * 100 : 0}%` }}
                />
              </div>
            </section>

            {current ? (
              <StopCard
                stop={current}
                pending={update.isPending}
                onDelivered={() => act(current, "delivered")}
                onFailed={() => act(current, "failed")}
              />
            ) : (
              <p className="mt-8 text-center text-lg font-semibold text-success">
                Tournée terminée 🎉
              </p>
            )}

            {update.isError && (
              <p role="alert" className="mt-3 text-center text-sm text-danger">
                Échec de la mise à jour. Réessayez.
              </p>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function StopCard({
  stop,
  pending,
  onDelivered,
  onFailed,
}: {
  stop: DriverStop;
  pending: boolean;
  onDelivered: () => void;
  onFailed: () => void;
}) {
  const tw =
    stop.time_window_start && stop.time_window_end
      ? `${stop.time_window_start}–${stop.time_window_end}`
      : null;
  const mapsHref = stop.lat != null && stop.lon != null ? `geo:${stop.lat},${stop.lon}` : undefined;

  return (
    <section className="mt-4 rounded-lg bg-white p-4 shadow-sm">
      <p className="text-sm text-neutral-400">Arrêt #{stop.sequence + 1}</p>
      <p className="mt-1 text-lg font-semibold text-neutral-900">📍 {stop.address}</p>
      {tw && <p className="mt-1 text-sm text-neutral-500">🕐 {tw}</p>}

      <div className="mt-4 grid grid-cols-2 gap-2">
        <a
          href={stop.customer_phone ? `tel:${stop.customer_phone}` : undefined}
          aria-disabled={!stop.customer_phone}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-neutral-300 py-3 font-medium text-neutral-700 aria-disabled:opacity-40"
        >
          <Phone className="h-5 w-5" aria-hidden="true" /> Appeler
        </a>
        <a
          href={mapsHref}
          aria-disabled={!mapsHref}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-neutral-300 py-3 font-medium text-neutral-700 aria-disabled:opacity-40"
        >
          <Navigation className="h-5 w-5" aria-hidden="true" /> Naviguer
        </a>
      </div>

      <div className="mt-3 space-y-2">
        <button
          onClick={onDelivered}
          disabled={pending}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-success py-4 text-lg font-semibold text-white disabled:opacity-50"
        >
          {pending ? (
            <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          ) : (
            <CheckCircle className="h-6 w-6" aria-hidden="true" />
          )}
          Livré
        </button>
        <button
          onClick={onFailed}
          disabled={pending}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-danger py-4 text-lg font-semibold text-white disabled:opacity-50"
        >
          <XCircle className="h-6 w-6" aria-hidden="true" /> Échec
        </button>
      </div>
    </section>
  );
}

// Best-effort geolocation for the status record; resolves to {} if unavailable/denied.
function currentPosition(): Promise<{ lat?: number; lon?: number }> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({});
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => resolve({}),
      { timeout: 5000 },
    );
  });
}
