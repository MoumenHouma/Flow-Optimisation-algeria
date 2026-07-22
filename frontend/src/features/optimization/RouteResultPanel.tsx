import { useEffect, useState } from "react";
import { useQueries, useQueryClient } from "@tanstack/react-query";
import { FileText, RefreshCw, Sheet } from "lucide-react";

import { useOptimizationJob, useReoptimize } from "@/api/optimization";
import { RouteMap } from "@/components/RouteMap";
import { apiFetch } from "@/lib/api-client";
import { downloadRouteExport } from "@/lib/downloads";
import { formatKm } from "@/lib/format";
import { routeColor } from "@/lib/route-colors";
import type { JobResult, RouteResult } from "@/types";

// Best-effort geolocation; resolves to {} if unavailable/denied.
function currentPosition(): Promise<{ currentLat?: number; currentLon?: number }> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({});
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ currentLat: p.coords.latitude, currentLon: p.coords.longitude }),
      () => resolve({}),
      { timeout: 5000 },
    );
  });
}

// Optimized-result view: summary + map + per-route stop lists (docs/DESIGN.md §3.3).
export function RouteResultPanel({ job }: { job: JobResult }) {
  const results = useQueries({
    queries: job.route_ids.map((id) => ({
      queryKey: ["route", id],
      queryFn: () => apiFetch<RouteResult>(`/api/v1/routes/${id}`),
    })),
  });
  const routes = results.flatMap((r) => (r.data ? [r.data] : []));

  return (
    <section className="mt-6">
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <h2 className="text-lg font-semibold text-success">Tournée optimisée 🎉</h2>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          <Metric label="Distance totale" value={formatKm(job.total_distance_m)} />
          <Metric label="Tournées" value={String(job.route_ids.length)} />
          <Metric label="Stratégie" value={job.solver_strategy ?? "—"} />
        </dl>
      </div>

      {routes.length > 0 && (
        <div className="mt-4 h-80 overflow-hidden rounded-lg border border-neutral-200">
          <RouteMap routes={routes} />
        </div>
      )}

      <div className="mt-4 space-y-4">
        {routes.map((route, index) => (
          <RouteCard key={route.id} route={route} index={index} />
        ))}
      </div>
    </section>
  );
}

function RouteCard({ route, index }: { route: RouteResult; index: number }) {
  const [downloading, setDownloading] = useState<"pdf" | "xlsx" | null>(null);
  const queryClient = useQueryClient();
  const reoptimize = useReoptimize();
  const [reoptJobId, setReoptJobId] = useState<string | null>(null);
  const reoptJob = useOptimizationJob(reoptJobId);
  const reoptimizing = reoptimize.isPending || reoptJobId !== null;

  // When the re-optimization job settles, refetch this route (now re-sequenced).
  useEffect(() => {
    const status = reoptJob.data?.status;
    if (status === "completed" || status === "failed") {
      if (status === "completed") {
        void queryClient.invalidateQueries({ queryKey: ["route", route.id] });
      }
      setReoptJobId(null);
    }
  }, [reoptJob.data?.status, queryClient, route.id]);

  const download = async (format: "pdf" | "xlsx") => {
    setDownloading(format);
    try {
      await downloadRouteExport(route.id, format);
    } finally {
      setDownloading(null);
    }
  };

  const onReoptimize = async () => {
    const pos = await currentPosition();
    const res = await reoptimize.mutateAsync({ routeId: route.id, ...pos });
    setReoptJobId(res.job_id);
  };

  return (
    <article className="rounded-lg border border-neutral-200 bg-white p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 font-semibold">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: routeColor(index) }}
            aria-hidden="true"
          />
          🚐 Véhicule {index + 1}
        </h3>
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-neutral-500">
            {formatKm(route.total_distance_m)} · {route.stops.length} arrêts
          </span>
          <button
            onClick={onReoptimize}
            disabled={reoptimizing}
            className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-2 py-1 text-xs font-medium hover:bg-neutral-50 disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${reoptimizing ? "animate-spin" : ""}`}
              aria-hidden="true"
            />{" "}
            Ré-optimiser
          </button>
          <button
            onClick={() => download("pdf")}
            disabled={downloading !== null}
            className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-2 py-1 text-xs font-medium hover:bg-neutral-50 disabled:opacity-50"
          >
            <FileText className="h-3.5 w-3.5" aria-hidden="true" /> PDF
          </button>
          <button
            onClick={() => download("xlsx")}
            disabled={downloading !== null}
            className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-2 py-1 text-xs font-medium hover:bg-neutral-50 disabled:opacity-50"
          >
            <Sheet className="h-3.5 w-3.5" aria-hidden="true" /> Excel
          </button>
        </div>
      </header>
      <ol className="mt-3 space-y-1 text-sm">
        {route.stops.map((stop) => (
          <li key={stop.delivery_id} className="flex items-center gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-light font-mono text-xs text-primary-dark">
              {stop.sequence + 1}
            </span>
            <span className="text-neutral-700">
              {stop.address ?? `${stop.delivery_id.slice(0, 8)}…`}
            </span>
          </li>
        ))}
      </ol>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-neutral-500">{label}</dt>
      <dd className="font-mono font-semibold">{value}</dd>
    </div>
  );
}
