import { ScrollText } from "lucide-react";
import { useState } from "react";

import { useAuditLog } from "@/api/audit";
import type { AuditEntry } from "@/types";

// Known audited actions (core/audit.py). Empty value = all actions.
const ACTIONS = [
  ["", "Toutes les actions"],
  ["user.login", "Connexion"],
  ["public_api.delivery_created", "Livraison (API publique)"],
  ["proof.accessed", "Preuve consultée"],
  ["company.branding_changed", "Marque modifiée"],
  ["api_key.created", "Clé API créée"],
  ["api_key.revoked", "Clé API révoquée"],
  ["webhook.created", "Webhook créé"],
  ["webhook.deleted", "Webhook supprimé"],
  ["territory.driver_assigned", "Livreur affecté"],
] as const;

// Audit trail (H2, loi 18-07) — admin-only immutable log of sensitive actions.
export function AuditLogPage() {
  const [action, setAction] = useState("");
  const { data, isLoading, isError } = useAuditLog(action || undefined);
  const entries = data ?? [];

  return (
    <main className="space-y-6 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold text-neutral-900">
            <ScrollText className="h-5 w-5 text-primary" aria-hidden="true" /> Journal d'audit
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Trace immuable des actions sensibles (conformité loi 18-07). Réservé aux administrateurs.
          </p>
        </div>
        <label className="text-sm">
          <span className="sr-only">Filtrer par action</span>
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            aria-label="Filtrer par action"
            className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          >
            {ACTIONS.map(([value, label]) => (
              <option key={value || "all"} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isError && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">
          Accès refusé ou journal indisponible. Le journal d'audit est réservé aux administrateurs.
        </p>
      )}

      <section className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-neutral-200 bg-neutral-50 text-xs uppercase text-neutral-500">
            <tr>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Ressource</th>
              <th className="px-4 py-3 font-medium">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {isLoading ? (
              <EmptyRow label="Chargement…" />
            ) : entries.length === 0 ? (
              <EmptyRow label="Aucune entrée." />
            ) : (
              entries.map((e) => <AuditRow key={e.id} entry={e} />)
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  return (
    <tr className="hover:bg-neutral-50">
      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-neutral-500">
        {new Date(entry.created_at).toLocaleString("fr-FR")}
      </td>
      <td className="px-4 py-3">
        <span className="rounded bg-primary-light px-1.5 py-0.5 font-mono text-xs text-primary-dark">
          {entry.action}
        </span>
      </td>
      <td className="px-4 py-3 text-neutral-700">
        {entry.resource_type}
        {entry.resource_id && (
          <span className="ml-1 font-mono text-xs text-neutral-400">
            {entry.resource_id.slice(0, 8)}…
          </span>
        )}
      </td>
      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-neutral-500">
        {entry.ip_address ?? "—"}
      </td>
    </tr>
  );
}

function EmptyRow({ label }: { label: string }) {
  return (
    <tr>
      <td colSpan={4} className="px-4 py-8 text-center text-sm text-neutral-500">
        {label}
      </td>
    </tr>
  );
}
