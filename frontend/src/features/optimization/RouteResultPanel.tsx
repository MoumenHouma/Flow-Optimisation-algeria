import { useRoute } from "@/api/optimization";
import { formatKm } from "@/lib/format";
import type { JobResult } from "@/types";

// Renders the optimized result summary + per-route stop list (docs/DESIGN.md §3.3).
export function RouteResultPanel({ job }: { job: JobResult }) {
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

      <div className="mt-4 space-y-4">
        {job.route_ids.map((id, index) => (
          <RouteCard key={id} routeId={id} index={index} />
        ))}
      </div>
    </section>
  );
}

function RouteCard({ routeId, index }: { routeId: string; index: number }) {
  const route = useRoute(routeId);
  if (!route.data) {
    return <div className="h-20 animate-pulse rounded-lg bg-neutral-100" />;
  }
  return (
    <article className="rounded-lg border border-neutral-200 bg-white p-4">
      <header className="flex items-center justify-between">
        <h3 className="font-semibold">🚐 Véhicule {index + 1}</h3>
        <span className="font-mono text-sm text-neutral-500">
          {formatKm(route.data.total_distance_m)} · {route.data.stops.length} arrêts
        </span>
      </header>
      <ol className="mt-3 space-y-1 text-sm">
        {route.data.stops.map((stop) => (
          <li key={stop.delivery_id} className="flex items-center gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-light font-mono text-xs text-primary-dark">
              {stop.sequence + 1}
            </span>
            <span className="text-neutral-700">{stop.delivery_id.slice(0, 8)}…</span>
            {stop.eta && <span className="text-neutral-400">{stop.eta}</span>}
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
