import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { routeColor } from "@/lib/route-colors";
import type { RouteResult } from "@/types";

const DEPOT_COLOR = "#10B981";
const ALGER: [number, number] = [3.0588, 36.7538]; // [lon, lat] fallback center

let rtlPluginSet = false;

function orderedLineCoords(route: RouteResult): [number, number][] {
  // Prefer the real road geometry (OSRM) when available.
  if (route.geometry?.coordinates?.length) return route.geometry.coordinates;
  // Otherwise draw straight lines depot -> stops (by sequence) -> depot.
  const pts: [number, number][] = [];
  const depot = route.depot;
  if (depot) pts.push([depot.lon, depot.lat]);
  route.stops
    .filter((s) => s.lat != null && s.lon != null)
    .slice()
    .sort((a, b) => a.sequence - b.sequence)
    .forEach((s) => pts.push([s.lon as number, s.lat as number]));
  if (depot) pts.push([depot.lon, depot.lat]);
  return pts;
}

function numberedMarkerEl(label: string, color: string): HTMLDivElement {
  const el = document.createElement("div");
  el.textContent = label;
  el.style.cssText = `
    display:flex;align-items:center;justify-content:center;
    width:22px;height:22px;border-radius:9999px;
    background:${color};color:#fff;font:600 11px/1 system-ui;
    border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4);`;
  return el;
}

export default function MapLibreMap({ routes }: { routes: RouteResult[] }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!container.current) return;

    const styleUrl = import.meta.env.VITE_MAP_STYLE_URL ?? "/map-style.json";
    const map = new maplibregl.Map({
      container: container.current,
      style: styleUrl,
      center: ALGER,
      zoom: 11,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    if (!rtlPluginSet) {
      // RTL text for Arabic labels (docs/DESIGN.md §6.1); safe to call once.
      try {
        maplibregl.setRTLTextPlugin("/mapbox-gl-rtl-text.js", true);
        rtlPluginSet = true;
      } catch {
        /* already set */
      }
    }

    const bounds = new maplibregl.LngLatBounds();
    const markers: maplibregl.Marker[] = [];

    map.on("load", () => {
      routes.forEach((route, index) => {
        const color = routeColor(index);
        const coords = orderedLineCoords(route);
        coords.forEach((c) => bounds.extend(c));

        if (coords.length >= 2) {
          const sourceId = `route-${route.id}`;
          map.addSource(sourceId, {
            type: "geojson",
            data: {
              type: "Feature",
              geometry: { type: "LineString", coordinates: coords },
              properties: {},
            },
          });
          map.addLayer({
            id: `${sourceId}-line`,
            type: "line",
            source: sourceId,
            layout: { "line-join": "round", "line-cap": "round" },
            paint: { "line-color": color, "line-width": 4, "line-opacity": 0.8 },
          });
        }

        // Numbered stop markers
        route.stops
          .filter((s) => s.lat != null && s.lon != null)
          .forEach((s) => {
            const el = numberedMarkerEl(String(s.sequence + 1), color);
            markers.push(
              new maplibregl.Marker({ element: el })
                .setLngLat([s.lon as number, s.lat as number])
                .setPopup(new maplibregl.Popup({ offset: 16 }).setText(s.address ?? s.delivery_id))
                .addTo(map),
            );
          });

        // Depot marker
        if (route.depot) {
          const el = numberedMarkerEl("D", DEPOT_COLOR);
          markers.push(
            new maplibregl.Marker({ element: el })
              .setLngLat([route.depot.lon, route.depot.lat])
              .addTo(map),
          );
        }
      });

      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { padding: 48, maxZoom: 15, duration: 0 });
      }
    });

    return () => {
      markers.forEach((m) => m.remove());
      map.remove();
      mapRef.current = null;
    };
  }, [routes]);

  return <div ref={container} className="h-full w-full" />;
}
