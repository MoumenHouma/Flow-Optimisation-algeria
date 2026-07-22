import { Plus, Trash2, Warehouse } from "lucide-react";
import { type FormEvent, useState } from "react";

import type { Depot, DepotDraft } from "@/types";

interface DepotPanelProps {
  depots: Depot[];
  onAdd: (draft: DepotDraft) => void;
  onDelete: (id: string) => void;
  adding?: boolean;
}

const EMPTY = { name: "", address: "", lat: "", lon: "" };

// Depots management (F12 multi-dépôt): shared departure points for vehicles.
export function DepotPanel({ depots, onAdd, onDelete, adding = false }: DepotPanelProps) {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const lat = Number(form.lat);
    const lon = Number(form.lon);
    if (!form.name.trim() || !form.address.trim() || Number.isNaN(lat) || Number.isNaN(lon)) {
      setError("Nom, adresse et coordonnées valides sont requis.");
      return;
    }
    setError(null);
    onAdd({
      name: form.name.trim(),
      address: form.address.trim(),
      location: { lat, lon },
      active: true,
    });
    setForm(EMPTY);
  };

  return (
    <section className="mt-8">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Warehouse className="h-5 w-5 text-neutral-500" aria-hidden="true" /> Dépôts
      </h2>
      <p className="mt-1 text-sm text-neutral-500">
        Points de départ partagés. Assignez-en un à un véhicule pour l'optimisation multi-dépôt.
      </p>

      {depots.length > 0 && (
        <ul className="mt-3 space-y-2">
          {depots.map((d) => (
            <li
              key={d.id}
              className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-3"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{d.name}</p>
                <p className="truncate text-xs text-neutral-500">
                  📍 {d.address}{" "}
                  <span className="font-mono">
                    ({d.location.lat}, {d.location.lon})
                  </span>
                </p>
              </div>
              <button
                onClick={() => onDelete(d.id)}
                aria-label={`Supprimer le dépôt ${d.name}`}
                className="rounded p-2 text-danger hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <form
        onSubmit={submit}
        className="mt-3 grid gap-2 rounded-lg border border-neutral-200 bg-white p-3 sm:grid-cols-4"
      >
        <input
          className={inputCls}
          placeholder="Nom (ex. Entrepôt Alger)"
          aria-label="Nom du dépôt"
          value={form.name}
          onChange={set("name")}
        />
        <input
          className={inputCls}
          placeholder="Adresse"
          aria-label="Adresse du dépôt"
          value={form.address}
          onChange={set("address")}
        />
        <input
          className={inputCls}
          placeholder="Latitude"
          aria-label="Latitude"
          value={form.lat}
          onChange={set("lat")}
        />
        <input
          className={inputCls}
          placeholder="Longitude"
          aria-label="Longitude"
          value={form.lon}
          onChange={set("lon")}
        />
        <div className="sm:col-span-4">
          <button
            type="submit"
            disabled={adding}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-50"
          >
            <Plus className="h-4 w-4" aria-hidden="true" /> Ajouter un dépôt
          </button>
          {error && (
            <span role="alert" className="ml-3 text-sm text-danger">
              {error}
            </span>
          )}
        </div>
      </form>
    </section>
  );
}

const inputCls = "rounded-lg border border-neutral-300 p-2 text-sm";
