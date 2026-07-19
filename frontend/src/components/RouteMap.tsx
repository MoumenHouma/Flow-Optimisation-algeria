import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

import type { RouteResult } from "@/types";

// Lazy-load MapLibre with an error boundary (docs/RULES.md §3.3).
const MapLibreMap = lazy(() => import("@/components/MapLibreMap"));

export function RouteMap({ routes }: { routes: RouteResult[] }) {
  return (
    <ErrorBoundary
      fallback={<div className="grid h-full place-items-center text-danger">Carte indisponible</div>}
    >
      <Suspense fallback={<div className="h-full w-full animate-pulse bg-neutral-100" />}>
        <MapLibreMap routes={routes} />
      </Suspense>
    </ErrorBoundary>
  );
}
