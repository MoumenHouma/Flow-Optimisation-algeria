// Driver PWA (Phase 2, F8) — docs/DESIGN.md §3.4.
// Mobile-first, offline-capable, large touch targets (>48px), proof of delivery.
export function DriverPage() {
  return (
    <main className="p-4">
      <h1 className="text-xl font-bold">Ma tournée</h1>
      <p className="mt-2 text-neutral-500">
        TODO (Phase 2): carte livraison courante, navigation, boutons Livré/Échec/Photo,
        offline + sync différée (docs/DESIGN.md §3.4, PRD §4.1).
      </p>
    </main>
  );
}
