import { useState } from "react";
import { Truck, Plus, Pencil, Trash2, Package, Scale } from "lucide-react";

import { useAddDepot, useDeleteDepot, useDepots } from "@/api/depots";
import {
  useAddVehicle,
  useDeleteVehicle,
  useFleetSummary,
  useUpdateVehicle,
  useVehicles,
} from "@/api/fleet";
import { DepotPanel } from "@/features/fleet/DepotPanel";
import { VehicleForm } from "@/features/fleet/VehicleForm";
import { vehicleToForm } from "@/lib/vehicle-form";
import type { Vehicle, VehicleDraft } from "@/types";

// Fleet management — vehicles CRUD with plan quota (F7).
type Editing = { mode: "add" } | { mode: "edit"; vehicle: Vehicle } | null;

const TYPE_LABELS: Record<string, string> = {
  car: "Voiture",
  van: "Fourgon",
  truck: "Camion",
  motorcycle: "Moto",
};

export function FleetPage() {
  const vehicles = useVehicles();
  const summary = useFleetSummary();
  const depots = useDepots();
  const addDepot = useAddDepot();
  const deleteDepot = useDeleteDepot();
  const add = useAddVehicle();
  const update = useUpdateVehicle();
  const remove = useDeleteVehicle();
  const [editing, setEditing] = useState<Editing>(null);

  const max = summary.data?.max_vehicles ?? null;
  const count = summary.data?.vehicle_count ?? 0;
  const quotaReached = max !== null && count >= max;

  const submit = (draft: VehicleDraft) => {
    if (editing?.mode === "edit") {
      update.mutate({ id: editing.vehicle.id, draft }, { onSuccess: () => setEditing(null) });
    } else {
      add.mutate(draft, { onSuccess: () => setEditing(null) });
    }
  };

  const onDelete = (v: Vehicle) => {
    if (window.confirm(`Supprimer le véhicule « ${v.name} » ?`)) remove.mutate(v.id);
  };

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Flotte</h1>
        <div className="text-sm text-neutral-500">
          {summary.data && (
            <span>
              {count}
              {max !== null ? ` / ${max}` : ""} véhicules · plan {summary.data.plan}
            </span>
          )}
        </div>
      </header>

      {!editing && (
        <button
          onClick={() => setEditing({ mode: "add" })}
          disabled={quotaReached}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
        >
          <Plus className="h-4 w-4" aria-hidden="true" /> Ajouter un véhicule
        </button>
      )}
      {quotaReached && !editing && (
        <p className="mt-2 text-sm text-warning">
          Quota atteint pour le plan {summary.data?.plan}. Supprimez un véhicule ou passez à un plan
          supérieur.
        </p>
      )}

      {editing && (
        <div className="mt-4">
          <VehicleForm
            initial={editing.mode === "edit" ? vehicleToForm(editing.vehicle) : undefined}
            initialDepotId={editing.mode === "edit" ? editing.vehicle.depot_id : null}
            depots={depots.data ?? []}
            submitLabel={editing.mode === "edit" ? "Enregistrer" : "Ajouter"}
            submitting={add.isPending || update.isPending}
            onSubmit={submit}
            onCancel={() => setEditing(null)}
          />
          {(add.isError || update.isError) && (
            <p role="alert" className="mt-2 text-sm text-danger">
              Échec de l'enregistrement (quota atteint ou données invalides).
            </p>
          )}
        </div>
      )}

      <DepotPanel
        depots={depots.data ?? []}
        onAdd={(draft) => addDepot.mutate(draft)}
        onDelete={(id) => deleteDepot.mutate(id)}
        adding={addDepot.isPending}
      />

      <section className="mt-6 space-y-3">
        {vehicles.isLoading && <p className="text-neutral-500">Chargement…</p>}
        {vehicles.data?.length === 0 && !editing && (
          <p className="text-neutral-500">Aucun véhicule. Ajoutez-en un pour commencer.</p>
        )}
        {vehicles.data?.map((v) => (
          <article
            key={v.id}
            className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-4"
          >
            <div>
              <div className="flex items-center gap-2 font-semibold">
                <Truck className="h-5 w-5 text-neutral-500" aria-hidden="true" />
                {v.name}
                <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs font-normal text-neutral-600">
                  {TYPE_LABELS[v.vehicle_type] ?? v.vehicle_type}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-4 text-sm text-neutral-500">
                <span className="inline-flex items-center gap-1">
                  <Scale className="h-4 w-4" aria-hidden="true" /> {v.capacity_weight} kg
                </span>
                <span className="inline-flex items-center gap-1">
                  <Package className="h-4 w-4" aria-hidden="true" /> {v.capacity_volume} m³
                </span>
                <span>📍 {v.depot_address}</span>
              </div>
            </div>
            <div className="flex gap-1">
              <button
                onClick={() => setEditing({ mode: "edit", vehicle: v })}
                aria-label={`Modifier ${v.name}`}
                className="rounded p-2 hover:bg-neutral-100"
              >
                <Pencil className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                onClick={() => onDelete(v)}
                aria-label={`Supprimer ${v.name}`}
                className="rounded p-2 text-danger hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
