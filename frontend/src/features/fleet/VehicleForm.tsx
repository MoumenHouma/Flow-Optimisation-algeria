import { type FormEvent, useState } from "react";

import {
  EMPTY_VEHICLE_FORM,
  FUEL_TYPES,
  parseVehicleForm,
  VEHICLE_TYPES,
  type VehicleFormErrors,
  type VehicleFormValues,
} from "@/lib/vehicle-form";
import type { Depot, VehicleDraft } from "@/types";

interface VehicleFormProps {
  initial?: VehicleFormValues;
  initialDepotId?: string | null;
  depots?: Depot[];
  submitLabel: string;
  submitting?: boolean;
  onSubmit: (draft: VehicleDraft) => void;
  onCancel: () => void;
}

const TYPE_LABELS: Record<string, string> = {
  car: "Voiture",
  van: "Fourgon",
  truck: "Camion",
  motorcycle: "Moto",
};

const FUEL_LABELS: Record<string, string> = {
  essence: "Essence",
  diesel: "Diesel",
  gpl: "GPL / Sirghaz",
  electric: "Électrique",
};

// Reused for both add and edit (docs/DESIGN.md §2.4 form patterns).
export function VehicleForm({
  initial = EMPTY_VEHICLE_FORM,
  initialDepotId = null,
  depots = [],
  submitLabel,
  submitting = false,
  onSubmit,
  onCancel,
}: VehicleFormProps) {
  const [values, setValues] = useState<VehicleFormValues>(initial);
  const [errors, setErrors] = useState<VehicleFormErrors>({});
  const [depotId, setDepotId] = useState<string>(initialDepotId ?? "");

  const set = (key: keyof VehicleFormValues) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  // Picking a saved depot fills the coordinates (so the form validates) and
  // makes that depot the source of truth on submit (F12).
  const onPickDepot = (id: string) => {
    setDepotId(id);
    const depot = depots.find((d) => d.id === id);
    if (depot) {
      setValues((v) => ({
        ...v,
        lat: String(depot.location.lat),
        lon: String(depot.location.lon),
        depot_address: depot.address,
      }));
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const { draft, errors: errs } = parseVehicleForm(values);
    setErrors(errs);
    if (draft) onSubmit(depotId ? { ...draft, depot_id: depotId } : draft);
  };

  const usingDepot = depotId !== "";

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nom" error={errors.name}>
          <input className={inputCls} value={values.name} onChange={set("name")} />
        </Field>
        <Field label="Type">
          <select
            className={inputCls}
            value={values.vehicle_type}
            onChange={(e) => setValues((v) => ({ ...v, vehicle_type: e.target.value }))}
          >
            {VEHICLE_TYPES.map((t) => (
              <option key={t} value={t}>
                {TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Immatriculation">
          <input
            className={inputCls}
            value={values.license_plate}
            onChange={set("license_plate")}
          />
        </Field>
        <Field label="Capacité poids (kg)" error={errors.capacity_weight}>
          <input
            type="number"
            className={inputCls}
            value={values.capacity_weight}
            onChange={set("capacity_weight")}
          />
        </Field>
        <Field label="Capacité volume (m³)" error={errors.capacity_volume}>
          <input
            type="number"
            className={inputCls}
            value={values.capacity_volume}
            onChange={set("capacity_volume")}
          />
        </Field>
        <Field label="Carburant" error={errors.fuel_type}>
          <select
            className={inputCls}
            value={values.fuel_type}
            onChange={(e) => setValues((v) => ({ ...v, fuel_type: e.target.value }))}
          >
            {FUEL_TYPES.map((t) => (
              <option key={t} value={t}>
                {FUEL_LABELS[t]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Autonomie (km, vide = illimitée)" error={errors.fuel_range_km}>
          <input
            type="number"
            className={inputCls}
            value={values.fuel_range_km}
            onChange={set("fuel_range_km")}
            placeholder="ex. 400"
          />
        </Field>
        {depots.length > 0 && (
          <Field label="Dépôt enregistré">
            <select
              className={inputCls}
              value={depotId}
              aria-label="Dépôt enregistré"
              onChange={(e) => onPickDepot(e.target.value)}
            >
              <option value="">— Saisie manuelle —</option>
              {depots.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Adresse du dépôt" error={errors.depot_address}>
          <input
            className={inputCls}
            value={values.depot_address}
            onChange={set("depot_address")}
            disabled={usingDepot}
          />
        </Field>
        <Field label="Dépôt — latitude" error={errors.lat}>
          <input
            className={inputCls}
            value={values.lat}
            onChange={set("lat")}
            placeholder="36.7538"
            disabled={usingDepot}
          />
        </Field>
        <Field label="Dépôt — longitude" error={errors.lon}>
          <input
            className={inputCls}
            value={values.lon}
            onChange={set("lon")}
            placeholder="3.0588"
            disabled={usingDepot}
          />
        </Field>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
        >
          {submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-neutral-300 px-4 py-2 font-medium hover:bg-neutral-50"
        >
          Annuler
        </button>
      </div>
    </form>
  );
}

const inputCls = "mt-1 w-full rounded-lg border border-neutral-300 p-2";

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="font-medium text-neutral-700">{label}</span>
      {children}
      {error && (
        <span role="alert" className="mt-1 block text-xs text-danger">
          {error}
        </span>
      )}
    </label>
  );
}
