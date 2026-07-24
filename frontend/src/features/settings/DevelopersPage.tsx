import { Copy, KeyRound, Plus, Trash2, Webhook as WebhookIcon } from "lucide-react";
import { useState } from "react";

import {
  useApiKeys,
  useCreateApiKey,
  useCreateWebhook,
  useDeleteWebhook,
  useRevokeApiKey,
  useWebhooks,
} from "@/api/integrations";
import { BrandingSettings } from "@/features/settings/BrandingSettings";
import type { ApiKey, Webhook } from "@/types";

const EVENTS = ["delivery.status_changed", "optimization.completed"] as const;

// Developer settings (F10): API keys + webhooks for e-commerce integration.
export function DevelopersPage() {
  return (
    <main className="space-y-8 p-4">
      <div>
        <h1 className="text-xl font-bold text-neutral-900">Développeurs 🔌</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Intégrez RouteOpt à votre e-commerce via l'API REST et les webhooks.
        </p>
      </div>
      <BrandingSettings />
      <ApiKeys />
      <Webhooks />
    </main>
  );
}

function ApiKeys() {
  const { data: keys } = useApiKeys();
  const create = useCreateApiKey();
  const revoke = useRevokeApiKey();
  const [name, setName] = useState("");
  const [scope, setScope] = useState("read");
  const [freshKey, setFreshKey] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const created = await create.mutateAsync({ name: name.trim(), scope });
    setFreshKey(created.key);
    setName("");
  };

  const active = (keys ?? []).filter((k) => !k.revoked_at);

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <h2 className="flex items-center gap-2 font-semibold">
        <KeyRound className="h-4 w-4 text-primary" aria-hidden="true" /> Clés API
      </h2>

      {freshKey && (
        <div className="mt-3 rounded-lg border border-green-300 bg-green-50 p-3">
          <p className="text-sm font-medium text-success">
            Copiez cette clé maintenant — elle ne sera plus affichée.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 overflow-x-auto rounded bg-white px-2 py-1.5 font-mono text-xs text-neutral-800">
              {freshKey}
            </code>
            <button
              onClick={() => navigator.clipboard?.writeText(freshKey)}
              className="inline-flex items-center gap-1 rounded-lg bg-primary px-2.5 py-1.5 text-xs font-medium text-white"
            >
              <Copy className="h-3.5 w-3.5" aria-hidden="true" /> Copier
            </button>
          </div>
        </div>
      )}

      <form onSubmit={submit} className="mt-4 flex flex-wrap items-end gap-2">
        <label className="flex-1">
          <span className="text-xs font-medium text-neutral-500">Nom</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Intégration Shopify"
            className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          />
        </label>
        <label>
          <span className="text-xs font-medium text-neutral-500">Portée</span>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            aria-label="Portée"
            className="mt-1 block rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          >
            <option value="read">read</option>
            <option value="write">write</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <Plus className="h-4 w-4" aria-hidden="true" /> Créer
        </button>
      </form>

      <div className="mt-4">
        {active.length === 0 ? (
          <p className="text-sm text-neutral-500">Aucune clé active.</p>
        ) : (
          <ul className="divide-y divide-neutral-100">
            {active.map((k) => (
              <KeyRow key={k.id} k={k} onRevoke={() => revoke.mutate(k.id)} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function KeyRow({ k, onRevoke }: { k: ApiKey; onRevoke: () => void }) {
  return (
    <li className="flex items-center justify-between py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-neutral-800">{k.name}</p>
        <p className="font-mono text-xs text-neutral-500">
          {k.key_prefix}…{" · "}
          <span className="rounded bg-primary-light px-1.5 py-0.5 text-primary-dark">
            {k.scope}
          </span>
          {k.last_used_at ? " · utilisée" : " · jamais utilisée"}
        </p>
      </div>
      <button
        onClick={onRevoke}
        className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-danger hover:bg-red-50"
      >
        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" /> Révoquer
      </button>
    </li>
  );
}

function Webhooks() {
  const { data: hooks } = useWebhooks();
  const create = useCreateWebhook();
  const del = useDeleteWebhook();
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState<string[]>([EVENTS[0]]);
  const [secret, setSecret] = useState<string | null>(null);

  const toggle = (ev: string) =>
    setEvents((cur) => (cur.includes(ev) ? cur.filter((e) => e !== ev) : [...cur, ev]));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || events.length === 0) return;
    const created = await create.mutateAsync({ url: url.trim(), events });
    setSecret(created.secret);
    setUrl("");
  };

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <h2 className="flex items-center gap-2 font-semibold">
        <WebhookIcon className="h-4 w-4 text-primary" aria-hidden="true" /> Webhooks
      </h2>

      {secret && (
        <div className="mt-3 rounded-lg border border-green-300 bg-green-50 p-3">
          <p className="text-sm font-medium text-success">
            Secret de signature (HMAC-SHA256) — affiché une seule fois.
          </p>
          <code className="mt-2 block overflow-x-auto rounded bg-white px-2 py-1.5 font-mono text-xs text-neutral-800">
            {secret}
          </code>
        </div>
      )}

      <form onSubmit={submit} className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-medium text-neutral-500">URL de destination</span>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://mon-site.dz/webhooks/routeopt"
            className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          {EVENTS.map((ev) => (
            <button
              key={ev}
              type="button"
              aria-pressed={events.includes(ev)}
              onClick={() => toggle(ev)}
              className={`rounded-full border px-3 py-1.5 font-mono text-xs ${
                events.includes(ev)
                  ? "border-primary bg-primary-light text-primary-dark"
                  : "border-neutral-300 text-neutral-600"
              }`}
            >
              {ev}
            </button>
          ))}
        </div>
        <button
          type="submit"
          disabled={create.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <Plus className="h-4 w-4" aria-hidden="true" /> Ajouter le webhook
        </button>
      </form>

      <div className="mt-4">
        {(hooks ?? []).length === 0 ? (
          <p className="text-sm text-neutral-500">Aucun webhook configuré.</p>
        ) : (
          <ul className="divide-y divide-neutral-100">
            {(hooks ?? []).map((w) => (
              <WebhookRow key={w.id} w={w} onDelete={() => del.mutate(w.id)} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function WebhookRow({ w, onDelete }: { w: Webhook; onDelete: () => void }) {
  return (
    <li className="flex items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-neutral-800">{w.url}</p>
        <p className="truncate font-mono text-xs text-neutral-500">{w.events.join(", ")}</p>
      </div>
      <button
        onClick={onDelete}
        aria-label="Supprimer le webhook"
        className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-danger hover:bg-red-50"
      >
        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" /> Supprimer
      </button>
    </li>
  );
}
