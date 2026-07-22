import { Brain, Loader2, RefreshCw } from "lucide-react";

import { useServiceTimeModel, useTrainServiceTime } from "@/api/predictions";

// Service-time ML model summary + retrain (F13).
export function ServiceTimePanel() {
  const { data } = useServiceTimeModel();
  const train = useTrainServiceTime();

  const fmtMin = (s: number) => `${Math.round(s / 60)} min`;

  return (
    <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold">
          <Brain className="h-4 w-4 text-primary" aria-hidden="true" /> Temps de service (ML)
        </h2>
        <button
          onClick={() => train.mutate()}
          disabled={train.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-300 px-3 py-1.5 text-sm font-medium hover:bg-neutral-50 disabled:opacity-50"
        >
          {train.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          )}
          Ré-entraîner
        </button>
      </div>

      <p className="mt-1 text-sm text-neutral-500">
        Prédit le temps passé à chaque arrêt (quartier, créneau, priorité) à partir de l'historique,
        pour des tournées plus réalistes.
      </p>

      {data && !data.trained ? (
        <p className="mt-3 text-sm text-neutral-500">
          Modèle non entraîné — la valeur par défaut ({fmtMin(data.global_median_s)}) est utilisée.
          Lancez un entraînement une fois quelques livraisons terminées.
        </p>
      ) : (
        data && (
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <Stat label="Échantillons" value={String(data.sample_count)} />
            <Stat label="Cohortes" value={String(data.cohort_count)} />
            <Stat label="Médiane globale" value={fmtMin(data.global_median_s)} />
            <Stat
              label="Erreur moy. (MAE)"
              value={data.mae_seconds != null ? fmtMin(data.mae_seconds) : "—"}
            />
          </dl>
        )
      )}

      {train.isError && (
        <p role="alert" className="mt-2 text-sm text-danger">
          Échec de l'entraînement. Réessayez.
        </p>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-neutral-500">{label}</dt>
      <dd className="font-mono font-semibold">{value}</dd>
    </div>
  );
}
