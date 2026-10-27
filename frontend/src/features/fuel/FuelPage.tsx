import { useState } from "react";

import { useCreateStation, useFuelStations, useSetStationStatus } from "@/api/fuel";
import type { FuelStation, FuelStatus } from "@/types";

const STATUSES: { value: FuelStatus; label: string }[] = [
  { value: "available", label: "Disponible" },
  { value: "shortage", label: "Pénurie" },
  { value: "closed", label: "Fermée" },
];

// Fuel-shortage management (F20): live station availability. PRD §4.1.
export function FuelPage() {
  const stations = useFuelStations();
  const setStatus = useSetStationStatus();

  return (
    <main className="p-4">
      <h1 className="text-xl font-bold text-neutral-900">Carburant ⛽</h1>

      <AddStationForm />

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">Stations</h2>
        {stations.data && stations.data.length > 0 ? (
          <ul className="mt-4 divide-y divide-neutral-100">
            {stations.data.map((s) => (
              <StationRow
                key={s.id}
                station={s}
                pending={setStatus.isPending}
                onStatus={(status) => setStatus.mutate({ id: s.id, status })}
              />
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-neutral-500">Aucune station enregistrée.</p>
        )}
      </section>
    </main>
  );
}

function AddStationForm() {
  const create = useCreateStation();
  const [name, setName] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !lat || !lon) return;
    create.mutate(
      { name, location: { lat: Number(lat), lon: Number(lon) } },
      {
        onSuccess: () => {
          setName("");
          setLat("");
          setLon("");
        },
      },
    );
  };

  return (
    <form
      onSubmit={submit}
      className="mt-4 flex flex-wrap items-end gap-2 rounded-lg border border-neutral-200 bg-white p-4"
    >
      <label className="flex-1">
        <span className="text-sm text-neutral-600">Nom</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2"
        />
      </label>
      <label>
        <span className="text-sm text-neutral-600">Latitude</span>
        <input
          value={lat}
          onChange={(e) => setLat(e.target.value)}
          inputMode="decimal"
          className="mt-1 w-28 rounded-lg border border-neutral-300 px-3 py-2 font-mono"
        />
      </label>
      <label>
        <span className="text-sm text-neutral-600">Longitude</span>
        <input
          value={lon}
          onChange={(e) => setLon(e.target.value)}
          inputMode="decimal"
          className="mt-1 w-28 rounded-lg border border-neutral-300 px-3 py-2 font-mono"
        />
      </label>
      <button
        type="submit"
        disabled={create.isPending}
        className="rounded-lg bg-primary px-4 py-2 font-medium text-white disabled:opacity-50"
      >
        Ajouter
      </button>
    </form>
  );
}

function StationRow({
  station,
  pending,
  onStatus,
}: {
  station: FuelStation;
  pending: boolean;
  onStatus: (status: FuelStatus) => void;
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div>
        <p className="font-medium text-neutral-800">{station.name}</p>
        <p className="font-mono text-xs text-neutral-400">
          {station.location.lat.toFixed(4)}, {station.location.lon.toFixed(4)} ·{" "}
          {station.fuel_types}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge status={station.status} />
        <div className="inline-flex rounded-lg border border-neutral-200 p-0.5">
          {STATUSES.map((s) => (
            <button
              key={s.value}
              disabled={pending || station.status === s.value}
              onClick={() => onStatus(s.value)}
              className={`rounded-md px-2 py-1 text-xs font-medium disabled:opacity-40 ${
                station.status === s.value
                  ? "bg-neutral-800 text-white"
                  : "text-neutral-600 hover:bg-neutral-100"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </li>
  );
}

function StatusBadge({ status }: { status: FuelStatus }) {
  const styles: Record<FuelStatus, string> = {
    available: "bg-success/10 text-success",
    shortage: "bg-warning/10 text-warning",
    closed: "bg-danger/10 text-danger",
  };
  const labels: Record<FuelStatus, string> = {
    available: "Disponible",
    shortage: "Pénurie",
    closed: "Fermée",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}
