import { useState } from "react";

import { usePerformance, useTrends } from "@/api/analytics";
import { formatKm } from "@/lib/format";
import type { DriverStat, FailureReason, TrendPoint } from "@/types";

const RANGES = [
  { days: 7, label: "7 j" },
  { days: 30, label: "30 j" },
  { days: 90, label: "90 j" },
];

// Analytics & reports (F11): historical KPIs, trends, delivery performance.
export function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const trends = useTrends(days);
  const perf = usePerformance(days);

  return (
    <main className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-neutral-900">Analytics 📊</h1>
        <div className="inline-flex rounded-lg border border-neutral-200 bg-white p-0.5">
          {RANGES.map((r) => (
            <button
              key={r.days}
              onClick={() => setDays(r.days)}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                days === r.days ? "bg-primary text-white" : "text-neutral-600 hover:bg-neutral-100"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <section className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi
          label="Taux de réussite"
          value={perf.data ? `${Math.round(perf.data.success_rate * 100)}%` : "—"}
        />
        <Kpi label="Livrées" value={perf.data ? String(perf.data.delivered) : "—"} />
        <Kpi label="Échecs" value={perf.data ? String(perf.data.failed) : "—"} />
        <Kpi
          label="Distance / tournée"
          value={perf.data ? formatKm(perf.data.avg_distance_per_route_m) : "—"}
        />
      </section>

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Tendance des livraisons</h2>
          <Legend />
        </div>
        {trends.data ? (
          <TrendChart points={trends.data.points} />
        ) : (
          <p className="mt-4 text-sm text-neutral-500">Chargement…</p>
        )}
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="font-semibold">Motifs d'échec</h2>
          {perf.data && perf.data.failure_reasons.length > 0 ? (
            <FailureReasons reasons={perf.data.failure_reasons} />
          ) : (
            <p className="mt-4 text-sm text-neutral-500">Aucun échec sur la période 🎉</p>
          )}
        </section>

        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="font-semibold">Performance des livreurs</h2>
          {perf.data && perf.data.drivers.length > 0 ? (
            <DriverTable drivers={perf.data.drivers} />
          ) : (
            <p className="mt-4 text-sm text-neutral-500">Aucune activité livreur.</p>
          )}
        </section>
      </div>
    </main>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-sm text-neutral-500">{label}</p>
      <p className="mt-1 font-mono text-2xl font-bold text-neutral-900">{value}</p>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-neutral-500">
      <span className="inline-flex items-center gap-1">
        <span className="h-2.5 w-2.5 rounded-sm bg-success" aria-hidden="true" /> Livrées
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-2.5 w-2.5 rounded-sm bg-danger" aria-hidden="true" /> Échecs
      </span>
    </div>
  );
}

function TrendChart({ points }: { points: TrendPoint[] }) {
  const max = Math.max(1, ...points.map((p) => p.deliveries_completed + p.deliveries_failed));
  const total = points.reduce((n, p) => n + p.deliveries_completed + p.deliveries_failed, 0);

  return (
    <div
      role="img"
      aria-label={`Tendance des livraisons: ${total} livraisons sur ${points.length} jours`}
      className="mt-4 flex h-40 items-end gap-0.5 overflow-x-auto"
    >
      {points.map((p) => {
        const sum = p.deliveries_completed + p.deliveries_failed;
        return (
          <div
            key={p.date}
            className="flex min-w-[6px] flex-1 flex-col justify-end"
            style={{ height: "100%" }}
            title={`${p.date}: ${p.deliveries_completed} livrées, ${p.deliveries_failed} échecs`}
          >
            <div
              className="w-full rounded-sm bg-danger"
              style={{ height: `${(p.deliveries_failed / max) * 100}%` }}
            />
            <div
              className="w-full rounded-sm bg-success"
              style={{ height: `${(p.deliveries_completed / max) * 100}%` }}
            />
            {sum === 0 && <div className="h-px w-full bg-neutral-200" />}
          </div>
        );
      })}
    </div>
  );
}

function FailureReasons({ reasons }: { reasons: FailureReason[] }) {
  const max = Math.max(1, ...reasons.map((r) => r.count));
  return (
    <ul className="mt-4 space-y-2">
      {reasons.map((r) => (
        <li key={r.reason} className="text-sm">
          <div className="flex items-center justify-between">
            <span className="text-neutral-700">{r.reason}</span>
            <span className="font-mono text-neutral-500">{r.count}</span>
          </div>
          <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-neutral-100">
            <div
              className="h-full rounded-full bg-danger"
              style={{ width: `${(r.count / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function DriverTable({ drivers }: { drivers: DriverStat[] }) {
  return (
    <table className="mt-4 w-full text-sm">
      <thead>
        <tr className="text-left text-neutral-500">
          <th className="pb-2 font-medium">Livreur</th>
          <th className="pb-2 text-right font-medium">Livrées</th>
          <th className="pb-2 text-right font-medium">Échecs</th>
          <th className="pb-2 text-right font-medium">Réussite</th>
        </tr>
      </thead>
      <tbody>
        {drivers.map((d) => {
          const done = d.delivered + d.failed;
          const rate = done ? Math.round((d.delivered / done) * 100) : 0;
          return (
            <tr key={d.driver_id} className="border-t border-neutral-100">
              <td className="py-2 text-neutral-800">{d.driver_name}</td>
              <td className="py-2 text-right font-mono text-success">{d.delivered}</td>
              <td className="py-2 text-right font-mono text-danger">{d.failed}</td>
              <td className="py-2 text-right font-mono text-neutral-700">{rate}%</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
