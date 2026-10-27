import { BarChart3, CheckCircle, Clock, MapPin, Truck } from "lucide-react";
import { Link } from "react-router-dom";

import { useDashboard } from "@/api/dashboard";
import { OnboardingChecklist } from "@/features/dashboard/OnboardingChecklist";
import { formatDuration, formatKm } from "@/lib/format";
import type { DashboardSummary } from "@/types";

// Manager dashboard — docs/DESIGN.md §3.2 (KPIs first, then breakdown + week).
const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  geocoded: "Géocodée",
  assigned: "Assignée",
  en_route: "En route",
  delivered: "Livrée",
  failed: "Échec",
  cancelled: "Annulée",
};

export function DashboardPage() {
  const { data, isLoading, isError } = useDashboard();

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold">Tableau de bord</h1>
        {data && <span className="text-sm text-neutral-500">{data.date}</span>}
      </header>

      {isLoading && <p className="mt-6 text-neutral-500">Chargement…</p>}
      {isError && (
        <p role="alert" className="mt-6 rounded-lg bg-red-50 p-3 text-sm text-danger">
          Impossible de charger les statistiques.
        </p>
      )}

      {data && <DashboardContent data={data} />}
    </main>
  );
}

function DashboardContent({ data }: { data: DashboardSummary }) {
  const delivered = data.deliveries_by_status.delivered ?? 0;

  return (
    <>
      <OnboardingChecklist data={data} />

      <section className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi
          icon={<MapPin className="h-5 w-5" />}
          label="Distance (aujourd'hui)"
          value={formatKm(data.today_distance_m)}
        />
        <Kpi
          icon={<Clock className="h-5 w-5" />}
          label="Temps (aujourd'hui)"
          value={formatDuration(data.today_time_s)}
        />
        <Kpi
          icon={<CheckCircle className="h-5 w-5" />}
          label="Livrées"
          value={`${delivered}/${data.deliveries_total}`}
        />
        <Kpi
          icon={<Truck className="h-5 w-5" />}
          label="Véhicules actifs"
          value={`${data.vehicles_active}/${data.vehicles_total}`}
        />
      </section>

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-neutral-700">Livraisons par statut</h2>
        {data.deliveries_total === 0 ? (
          <p className="mt-2 text-sm text-neutral-500">
            Aucune livraison.{" "}
            <Link to="/import" className="text-primary hover:underline">
              Importer un fichier →
            </Link>
          </p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(data.deliveries_by_status).map(([status, count]) => (
              <span
                key={status}
                className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-3 py-1 text-sm"
              >
                <span className="font-medium">{STATUS_LABELS[status] ?? status}</span>
                <span className="font-mono text-neutral-600">{count}</span>
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-neutral-700">
          <BarChart3 className="h-4 w-4" aria-hidden="true" /> Cette semaine
        </h2>
        <dl className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Metric label="Optimisations" value={String(data.week_optimizations)} />
          <Metric label="Distance planifiée" value={formatKm(data.week_distance_m)} />
          <Metric label="Tournées (aujourd'hui)" value={String(data.today_routes)} />
        </dl>
      </section>

      <div className="mt-6">
        <Link
          to="/optimize"
          className="inline-block rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark"
        >
          Planifier une tournée →
        </Link>
      </div>
    </>
  );
}

function Kpi({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="flex items-center gap-2 text-neutral-500">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="mt-2 font-mono text-2xl font-semibold text-neutral-900">{value}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-neutral-500">{label}</dt>
      <dd className="font-mono text-lg font-semibold">{value}</dd>
    </div>
  );
}
