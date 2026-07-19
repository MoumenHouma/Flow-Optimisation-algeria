import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

import type { GeoPoint, RouteResult } from "@/types";

// Lazy-load MapLibre with an error boundary (docs/RULES.md §3.3).
const MapLibreMap = lazy(() => import("@/components/MapLibreMap"));

interface RouteMapProps {
  routes: RouteResult[];
  depot: GeoPoint;
}

export function RouteMap({ routes, depot }: RouteMapProps) {
  return (
    <ErrorBoundary fallback={<div className="p-4 text-danger">Carte indisponible</div>}>
      <Suspense fallback={<div className="h-full w-full animate-pulse bg-neutral-100" />}>
        <MapLibreMap routes={routes} depot={depot} />
      </Suspense>
    </ErrorBoundary>
  );
}
