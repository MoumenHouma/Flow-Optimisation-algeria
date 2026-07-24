import { Loader2, MapPin, Play, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useOptimize } from "@/api/optimization";
import {
  useAssignDriver,
  useAutoGenerate,
  useDeleteTerritory,
  useDrivers,
  useTerritories,
} from "@/api/territories";
import type { Driver, Territory } from "@/types";

// Territory management (F15): auto-cluster deliveries into zones + assign drivers.
export function TerritoriesPage() {
  const { data: territories } = useTerritories();
  const { data: drivers } = useDrivers();
  const generate = useAutoGenerate();
  const [zones, setZones] = useState("");

  const list = territories ?? [];

  return (
    <main className="mx-auto max-w-4xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Territoires</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Divise automatiquement les livraisons en zones géographiques et affecte un livreur à
            chaque zone.
          </p>
        </div>
        <div className="flex items-end gap-2">
          <label className="text-sm">
            <span className="block text-xs font-medium text-neutral-500">Zones</span>
            <input
              value={zones}
              onChange={(e) => setZones(e.target.value)}
              placeholder="auto"
              aria-label="Nombre de zones"
              className="mt-1 w-20 rounded-lg border border-neutral-300 px-2 py-1.5 text-sm"
            />
          </label>
          <button
            onClick={() => generate.mutate(zones ? Number(zones) : undefined)}
            disabled={generate.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-50"
          >
            {generate.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Sparkles className="h-4 w-4" aria-hidden="true" />
            )}
            Générer automatiquement
          </button>
        </div>
      </div>

      {generate.isError && (
        <p role="alert" className="mt-3 text-sm text-danger">
          Génération impossible — importez des livraisons géocodées d'abord.
        </p>
      )}

      <section className="mt-6 space-y-3">
        {list.length === 0 ? (
          <p className="text-neutral-500">
            Aucun territoire. Lancez « Générer automatiquement » pour créer des zones.
          </p>
        ) : (
          list.map((t) => <TerritoryCard key={t.id} territory={t} drivers={drivers ?? []} />)
        )}
      </section>
    </main>
  );
}

function TerritoryCard({ territory, drivers }: { territory: Territory; drivers: Driver[] }) {
  const assign = useAssignDriver();
  const remove = useDeleteTerritory();
  const optimize = useOptimize();
  const navigate = useNavigate();

  // F1: route this zone with its assigned driver's vehicle. Needs a driver + stops.
  const canOptimize =
    Boolean(territory.driver_user_id) && territory.delivery_count > 0 && !optimize.isPending;
  const optimizeZone = () =>
    optimize.mutate(
      { territoryId: territory.id },
      { onSuccess: (res) => navigate(`/optimization?job=${res.job_id}`) },
    );

  return (
    <article className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white p-4">
      <div className="flex items-center gap-3">
        <span
          className="inline-block h-4 w-4 rounded-full"
          style={{ backgroundColor: territory.color }}
          aria-hidden="true"
        />
        <div>
          <p className="font-semibold">{territory.name}</p>
          <p className="text-sm text-neutral-500">
            <MapPin className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" />
            {territory.delivery_count} livraison(s)
            {territory.centroid && (
              <span className="ml-2 font-mono text-xs">
                {territory.centroid.lat.toFixed(3)}, {territory.centroid.lon.toFixed(3)}
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <select
          aria-label={`Livreur pour ${territory.name}`}
          value={territory.driver_user_id ?? ""}
          onChange={(e) => assign.mutate({ id: territory.id, driverId: e.target.value || null })}
          className="rounded-lg border border-neutral-300 px-2 py-1.5 text-sm"
        >
          <option value="">— Sans livreur —</option>
          {drivers.map((d) => (
            <option key={d.id} value={d.id}>
              {d.full_name}
            </option>
          ))}
        </select>
        <button
          onClick={optimizeZone}
          disabled={!canOptimize}
          title={
            territory.driver_user_id
              ? "Optimiser la tournée de cette zone"
              : "Affectez d'abord un livreur"
          }
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary px-2.5 py-1.5 text-sm font-medium text-primary hover:bg-primary/5 disabled:opacity-40"
        >
          {optimize.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Play className="h-4 w-4" aria-hidden="true" />
          )}
          Optimiser
        </button>
        <button
          onClick={() => remove.mutate(territory.id)}
          aria-label={`Supprimer ${territory.name}`}
          className="rounded p-2 text-danger hover:bg-red-50"
        >
          <Trash2 className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </article>
  );
}
