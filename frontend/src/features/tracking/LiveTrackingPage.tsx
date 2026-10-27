import { useLivePositions } from "@/api/tracking";
import type { LivePosition } from "@/types";

// Live tracking (F18): real-time fleet positions streamed from the backend
// (SSE-over-fetch). Kills the dispatcher's "où est mon livreur ?" phone calls.
export function LiveTrackingPage() {
  const { positions, connected } = useLivePositions();

  return (
    <main className="p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-neutral-900">Suivi en direct 📍</h1>
        <span className="inline-flex items-center gap-2 text-sm text-neutral-500">
          <span
            className={`h-2.5 w-2.5 rounded-full ${connected ? "bg-success" : "bg-neutral-300"}`}
            aria-hidden="true"
          />
          {connected ? "Connecté" : "Hors ligne"}
        </span>
      </div>

      <section className="mt-4 rounded-lg border border-neutral-200 bg-white p-4">
        {positions.length > 0 ? (
          <ul className="divide-y divide-neutral-100">
            {positions.map((p) => (
              <PositionRow key={p.vehicle_id} position={p} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-500">
            Aucun véhicule en mouvement. Les positions apparaissent dès qu'un livreur démarre sa
            tournée.
          </p>
        )}
      </section>
    </main>
  );
}

function PositionRow({ position }: { position: LivePosition }) {
  const seconds = Math.max(0, Math.round(Date.now() / 1000 - position.ts));
  const ago = seconds < 60 ? `il y a ${seconds}s` : `il y a ${Math.round(seconds / 60)} min`;
  return (
    <li className="flex items-center justify-between py-3">
      <div>
        <p className="font-medium text-neutral-800">🚐 {position.vehicle_id.slice(0, 8)}</p>
        <p className="font-mono text-xs text-neutral-400">
          {position.lat.toFixed(5)}, {position.lon.toFixed(5)}
        </p>
      </div>
      <span className="text-xs text-neutral-500">{ago}</span>
    </li>
  );
}
