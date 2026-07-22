import { CheckCircle, Loader2 } from "lucide-react";

import { useCodPayments, useCodSummary, useReconcileCod } from "@/api/cod";
import type { CodPayment, CodSummaryRow } from "@/types";

// COD reconciliation (F17): the manager reconciles cash collected in the field
// against what was due. PRD §4.1 "paiement à la livraison".
export function CodReconciliationPage() {
  const summary = useCodSummary();
  const payments = useCodPayments();
  const reconcile = useReconcileCod();

  return (
    <main className="p-4">
      <h1 className="text-xl font-bold text-neutral-900">Encaissements 💵</h1>

      <section className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Kpi label="Attendu" value={summary.data ? formatDa(summary.data.total_expected) : "—"} />
        <Kpi label="Collecté" value={summary.data ? formatDa(summary.data.total_collected) : "—"} />
        <Kpi
          label="Écarts"
          value={summary.data ? String(summary.data.discrepancies) : "—"}
          alert={!!summary.data && summary.data.discrepancies > 0}
        />
      </section>

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">Par livreur / jour</h2>
        {summary.data && summary.data.rows.length > 0 ? (
          <SummaryTable rows={summary.data.rows} />
        ) : (
          <p className="mt-4 text-sm text-neutral-500">Aucun encaissement sur la période.</p>
        )}
      </section>

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">Détail des encaissements</h2>
        {payments.data && payments.data.length > 0 ? (
          <PaymentsTable
            payments={payments.data}
            pending={reconcile.isPending}
            onReconcile={(id) => reconcile.mutate({ id, status: "reconciled" })}
            onFlag={(id) => reconcile.mutate({ id, status: "discrepancy" })}
          />
        ) : (
          <p className="mt-4 text-sm text-neutral-500">Aucun encaissement à afficher.</p>
        )}
      </section>
    </main>
  );
}

function Kpi({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-sm text-neutral-500">{label}</p>
      <p
        className={`mt-1 font-mono text-2xl font-bold ${alert ? "text-danger" : "text-neutral-900"}`}
      >
        {value}
      </p>
    </div>
  );
}

function SummaryTable({ rows }: { rows: CodSummaryRow[] }) {
  return (
    <table className="mt-4 w-full text-sm">
      <thead>
        <tr className="text-left text-neutral-500">
          <th className="pb-2 font-medium">Jour</th>
          <th className="pb-2 text-right font-medium">Livraisons</th>
          <th className="pb-2 text-right font-medium">Attendu</th>
          <th className="pb-2 text-right font-medium">Collecté</th>
          <th className="pb-2 text-right font-medium">Écarts</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={`${r.day}-${r.driver_user_id}`} className="border-t border-neutral-100">
            <td className="py-2 text-neutral-800">{r.day}</td>
            <td className="py-2 text-right font-mono">{r.count}</td>
            <td className="py-2 text-right font-mono">{formatDa(r.total_expected)}</td>
            <td className="py-2 text-right font-mono">{formatDa(r.total_collected)}</td>
            <td
              className={`py-2 text-right font-mono ${r.discrepancies > 0 ? "text-danger" : "text-neutral-400"}`}
            >
              {r.discrepancies}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PaymentsTable({
  payments,
  pending,
  onReconcile,
  onFlag,
}: {
  payments: CodPayment[];
  pending: boolean;
  onReconcile: (id: string) => void;
  onFlag: (id: string) => void;
}) {
  return (
    <table className="mt-4 w-full text-sm">
      <thead>
        <tr className="text-left text-neutral-500">
          <th className="pb-2 font-medium">Commande</th>
          <th className="pb-2 text-right font-medium">Attendu</th>
          <th className="pb-2 text-right font-medium">Collecté</th>
          <th className="pb-2 font-medium">Statut</th>
          <th className="pb-2 text-right font-medium">Action</th>
        </tr>
      </thead>
      <tbody>
        {payments.map((p) => (
          <tr key={p.id} className="border-t border-neutral-100">
            <td className="py-2 text-neutral-800">{p.order_id ?? p.delivery_id.slice(0, 8)}</td>
            <td className="py-2 text-right font-mono">
              {p.amount_expected != null ? formatDa(p.amount_expected) : "—"}
            </td>
            <td className="py-2 text-right font-mono">{formatDa(p.amount_collected)}</td>
            <td className="py-2">
              <StatusBadge status={p.status} />
            </td>
            <td className="py-2 text-right">
              {p.status === "reconciled" ? (
                <span className="inline-flex items-center gap-1 text-success">
                  <CheckCircle className="h-4 w-4" aria-hidden="true" /> OK
                </span>
              ) : (
                <div className="inline-flex gap-2">
                  <button
                    onClick={() => onReconcile(p.id)}
                    disabled={pending}
                    className="rounded-md bg-success px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
                  >
                    {pending ? (
                      <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                    ) : (
                      "Valider"
                    )}
                  </button>
                  <button
                    onClick={() => onFlag(p.id)}
                    disabled={pending}
                    className="rounded-md border border-danger px-2 py-1 text-xs font-medium text-danger disabled:opacity-50"
                  >
                    Signaler
                  </button>
                </div>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StatusBadge({ status }: { status: CodPayment["status"] }) {
  const styles: Record<CodPayment["status"], string> = {
    pending: "bg-neutral-100 text-neutral-600",
    collected: "bg-primary/10 text-primary",
    reconciled: "bg-success/10 text-success",
    discrepancy: "bg-danger/10 text-danger",
  };
  const labels: Record<CodPayment["status"], string> = {
    pending: "En attente",
    collected: "Collecté",
    reconciled: "Validé",
    discrepancy: "Écart",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

function formatDa(amount: number): string {
  return `${amount.toLocaleString("fr-DZ")} DA`;
}
