// Display formatting helpers (docs/DESIGN.md §2.2 uses mono for data).

export function formatKm(meters?: number | null): string {
  if (meters == null) return "—";
  return `${(meters / 1000).toFixed(1)} km`;
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null) return "—";
  const total = Math.round(seconds / 60);
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  return hours > 0 ? `${hours}h ${minutes}min` : `${minutes}min`;
}
