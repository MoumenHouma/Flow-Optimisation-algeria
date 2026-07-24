// Authenticated file download for route exports (F5). Uses fetch + Blob because
// the endpoint requires the Bearer token (a plain <a href> can't send it).
import { ApiError } from "@/lib/api-client";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function downloadRouteExport(routeId: string, format: "pdf" | "xlsx"): Promise<void> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${BASE_URL}/api/v1/routes/${routeId}/export?format=${format}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new ApiError(response.status, await response.text());

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `tournee-${routeId.slice(0, 8)}.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
