import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { GeoPoint, RouteResult } from "@/types";

interface MapLibreMapProps {
  routes: RouteResult[];
  depot: GeoPoint;
}

// Route colors from docs/DESIGN.md §2.1 (map palette).
const ROUTE_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#06B6D4", "#EF4444"];

// Default export so it can be lazy-loaded (docs/RULES.md §3.3).
export default function MapLibreMap({ routes, depot }: MapLibreMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!container.current) return;

    const styleUrl = import.meta.env.VITE_MAP_STYLE_URL ?? "/map-style.json";
    const map = new maplibregl.Map({
      container: container.current,
      style: styleUrl,
      center: [depot.lon, depot.lat],
      zoom: 12,
    });
    mapRef.current = map;

    // RTL text plugin for Arabic labels (docs/DESIGN.md §6.1).
    maplibregl.setRTLTextPlugin("/mapbox-gl-rtl-text.js", true);

    map.on("load", () => {
      routes.forEach((route, index) => {
        if (!route.stops.length) return;
        map.addSource(`route-${index}`, {
          type: "geojson",
          data: { type: "Feature", geometry: { type: "LineString", coordinates: [] }, properties: {} },
        });
        map.addLayer({
          id: `route-line-${index}`,
          type: "line",
          source: `route-${index}`,
          paint: {
            "line-color": ROUTE_COLORS[index % ROUTE_COLORS.length],
            "line-width": 3,
          },
        });
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [routes, depot]);

  return <div ref={container} className="h-full w-full" />;
}
