import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Truck, Package, Play, Loader2 } from "lucide-react";

import { useOptimize, useOptimizationJob } from "@/api/optimization";
import { useVehicles } from "@/api/fleet";
import { useRoutableDeliveries } from "@/api/orders";
import { RouteResultPanel } from "@/features/optimization/RouteResultPanel";

// Objective presets (F14): weighting of distance / time / fuel / CO2.
const OBJECTIVES = [
  { id: "distance", label: "Distance", weights: { distance: 1, time: 0, fuel: 0, co2: 0 } },
  { id: "balanced", label: "Équilibré", weights: { distance: 1, time: 1, fuel: 1, co2: 0.5 } },
  { id: "eco", label: "Écologique", weights: { distance: 0.2, time: 0.2, fuel: 3, co2: 2 } },
] as const;

// Optimization screen — docs/DESIGN.md §3.3 (params, launch, result).
export function OptimizationPage() {
  const vehicles = useVehicles();
  const deliveries = useRoutableDeliveries();
  const optimize = useOptimize();
  const [jobId, setJobId] = useState<string | null>(null);
  const [objectiveId, setObjectiveId] = useState<string>("distance");
  const [useMlServiceTime, setUseMlServiceTime] = useState(true);
  const job = useOptimizationJob(jobId);

  // Deep-link a job launched elsewhere (e.g. "Optimiser cette zone" — F1).
  const [searchParams] = useSearchParams();
  const jobParam = searchParams.get("job");
  useEffect(() => {
    if (jobParam) setJobId(jobParam);
  }, [jobParam]);

  const vehicleCount = vehicles.data?.length ?? 0;
  const deliveryCount = deliveries.data?.length ?? 0;
  const canOptimize = vehicleCount > 0 && deliveryCount > 0 && !optimize.isPending;

  const launch = () => {
    const objective = OBJECTIVES.find((o) => o.id === objectiveId)?.weights;
    optimize.mutate(
      { objective, applyServiceTimePrediction: useMlServiceTime },
      { onSuccess: (res) => setJobId(res.job_id) },
    );
  };

  const running = job.data
    ? job.data.status === "pending" || job.data.status === "running"
    : Boolean(jobId);

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="text-2xl font-bold">Optimisation</h1>

      <section className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Stat
          icon={<Package className="h-5 w-5" />}
          label="Livraisons à router"
          value={deliveryCount}
        />
        <Stat icon={<Truck className="h-5 w-5" />} label="Véhicules actifs" value={vehicleCount} />
      </section>

      <div className="mt-6">
        <p className="text-sm font-medium text-neutral-700">Objectif</p>
        <div className="mt-2 inline-flex rounded-lg border border-neutral-200 bg-white p-0.5">
          {OBJECTIVES.map((o) => (
            <button
              key={o.id}
              onClick={() => setObjectiveId(o.id)}
              aria-pressed={objectiveId === o.id}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                objectiveId === o.id
                  ? "bg-primary text-white"
                  : "text-neutral-600 hover:bg-neutral-100"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
        <p className="mt-1 text-xs text-neutral-500">
          « Écologique » privilégie le carburant et les émissions (préfère les véhicules propres).
        </p>
      </div>

      <label className="mt-4 flex items-center gap-2 text-sm text-neutral-700">
        <input
          type="checkbox"
          checked={useMlServiceTime}
          onChange={(e) => setUseMlServiceTime(e.target.checked)}
          className="h-4 w-4 rounded border-neutral-300"
        />
        Temps de service estimé par ML
        <span className="text-xs text-neutral-500">
          (décochez pour utiliser le temps saisi par livraison)
        </span>
      </label>

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
