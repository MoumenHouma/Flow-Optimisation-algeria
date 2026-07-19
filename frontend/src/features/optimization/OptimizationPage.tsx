import { useState } from "react";
import { Truck, Package, Play, Loader2 } from "lucide-react";

import { useOptimize, useOptimizationJob } from "@/api/optimization";
import { useVehicles } from "@/api/fleet";
import { useRoutableDeliveries } from "@/api/orders";
import { RouteResultPanel } from "@/features/optimization/RouteResultPanel";

// Optimization screen — docs/DESIGN.md §3.3 (params, launch, result).
export function OptimizationPage() {
  const vehicles = useVehicles();
  const deliveries = useRoutableDeliveries();
  const optimize = useOptimize();
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useOptimizationJob(jobId);

  const vehicleCount = vehicles.data?.length ?? 0;
  const deliveryCount = deliveries.data?.length ?? 0;
  const canOptimize = vehicleCount > 0 && deliveryCount > 0 && !optimize.isPending;

  const launch = () =>
    optimize.mutate({}, { onSuccess: (res) => setJobId(res.job_id) });

  const running = job.data
    ? job.data.status === "pending" || job.data.status === "running"
    : Boolean(jobId);

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="text-2xl font-bold">Optimisation</h1>

      <section className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Stat icon={<Package className="h-5 w-5" />} label="Livraisons à router" value={deliveryCount} />
        <Stat icon={<Truck className="h-5 w-5" />} label="Véhicules actifs" value={vehicleCount} />
      </section>

      <button
        onClick={launch}
        disabled={!canOptimize}
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
      >
        {optimize.isPending || running ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <Play className="h-4 w-4" aria-hidden="true" />
        )}
        {running ? "Optimisation en cours…" : "Optimiser la tournée"}
      </button>

      {deliveryCount === 0 && (
        <p className="mt-3 text-sm text-neutral-500">
          Aucune livraison à router — importez des livraisons d'abord.
        </p>
      )}

      {job.data?.status === "failed" && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-danger">
          ⚠️ Optimisation impossible : {job.data.error_message ?? "contraintes incompatibles"}
        </p>
      )}

      {job.data?.status === "completed" && <RouteResultPanel job={job.data} />}
    </main>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="flex items-center gap-2 text-neutral-500">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <p className="mt-1 font-mono text-2xl font-semibold">{value}</p>
    </div>
  );
}
