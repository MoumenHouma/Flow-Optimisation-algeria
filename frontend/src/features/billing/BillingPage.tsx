import { useBilling, useChangePlan, useInvoices } from "@/api/billing";
import type { Invoice, Plan, Usage } from "@/types";

const PLAN_LABELS: Record<Plan, string> = {
  free: "Free",
  starter: "Starter",
  pro: "Pro",
  enterprise: "Enterprise",
};

const PLAN_ORDER: Plan[] = ["free", "starter", "pro", "enterprise"];

// Billing & quotas (F19): current plan, usage-vs-quota, invoices, plan change.
export function BillingPage() {
  const billing = useBilling();
  const invoices = useInvoices();
  const changePlan = useChangePlan();

  return (
    <main className="p-4">
      <h1 className="text-xl font-bold text-neutral-900">Abonnement 💳</h1>

      <section className="mt-4 rounded-lg border border-neutral-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-neutral-500">Formule actuelle</p>
            <p className="mt-1 text-2xl font-bold text-neutral-900">
              {billing.data ? PLAN_LABELS[billing.data.plan] : "—"}
            </p>
          </div>
          <p className="font-mono text-lg text-neutral-700">
            {billing.data ? `${billing.data.price_da.toLocaleString("fr-DZ")} DA/mois` : ""}
          </p>
        </div>

        {billing.data && <UsageBars usage={billing.data.usage} />}
      </section>

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">Changer de formule</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {PLAN_ORDER.map((plan) => {
            const active = billing.data?.plan === plan;
            return (
              <button
                key={plan}
                disabled={active || changePlan.isPending}
                onClick={() => changePlan.mutate(plan)}
                className={`rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-50 ${
                  active
                    ? "border-primary bg-primary text-white"
                    : "border-neutral-300 text-neutral-700 hover:bg-neutral-100"
                }`}
              >
                {PLAN_LABELS[plan]}
              </button>
            );
          })}
        </div>
        {changePlan.isError && (
          <p role="alert" className="mt-2 text-sm text-danger">
            Changement impossible (réservé aux administrateurs).
          </p>
        )}
      </section>

      <section className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">Factures</h2>
        {invoices.data && invoices.data.length > 0 ? (
          <InvoiceTable invoices={invoices.data} />
        ) : (
          <p className="mt-4 text-sm text-neutral-500">Aucune facture pour le moment.</p>
        )}
      </section>
    </main>
  );
}

function UsageBars({ usage }: { usage: Usage }) {
  return (
    <div className="mt-4 space-y-4">
      <UsageBar label="Véhicules" used={usage.vehicles} cap={usage.max_vehicles} unit="" />
      <UsageBar
        label="Livraisons aujourd'hui"
        used={usage.deliveries_today}
        cap={usage.max_deliveries_per_day}
        unit="/jour"
      />
    </div>
  );
}

function UsageBar({
  label,
  used,
  cap,
  unit,
}: {
  label: string;
  used: number;
  cap: number | null;
  unit: string;
}) {
  const ratio = cap != null && cap > 0 ? Math.min(1, used / cap) : 0;
  const atCap = cap != null && used >= cap;
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-neutral-700">{label}</span>
        <span className={`font-mono ${atCap ? "text-danger" : "text-neutral-500"}`}>
          {used} / {cap ?? "∞"}
          {unit}
        </span>
      </div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-neutral-100">
        <div
          className={`h-full rounded-full ${atCap ? "bg-danger" : "bg-primary"}`}
          style={{ width: cap != null ? `${ratio * 100}%` : "100%" }}
        />
      </div>
      {atCap && (
        <p className="mt-1 text-xs text-danger">
          Quota atteint — passez à une formule supérieure pour en ajouter.
        </p>
      )}
    </div>
  );
}

function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  return (
    <table className="mt-4 w-full text-sm">
      <thead>
        <tr className="text-left text-neutral-500">
          <th className="pb-2 font-medium">Période</th>
          <th className="pb-2 font-medium">Formule</th>
          <th className="pb-2 text-right font-medium">Montant</th>
          <th className="pb-2 font-medium">Statut</th>
        </tr>
      </thead>
      <tbody>
        {invoices.map((i) => (
          <tr key={i.id} className="border-t border-neutral-100">
            <td className="py-2 font-mono text-neutral-800">{i.period}</td>
            <td className="py-2 text-neutral-700">{i.plan}</td>
            <td className="py-2 text-right font-mono">{i.amount_da.toLocaleString("fr-DZ")} DA</td>
            <td className="py-2">
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  i.status === "paid" ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                }`}
              >
                {i.status === "paid" ? "Payée" : "En attente"}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
