// Maps parsed CSV rows to delivery payloads with client-side validation.
// Expected columns (DESIGN §3.5): address, order_id, lat, lon, phone,
// time_window_start, time_window_end, weight, volume, priority.
// Only `address` is required; rows with lat/lon skip server-side geocoding.

import type { DeliveryDraft } from "@/types";

export interface RowError {
  line: number; // 1-based line number in the file (incl. header)
  errors: string[];
}

export interface ImportPreview {
  valid: DeliveryDraft[];
  invalid: RowError[];
  total: number;
}

export const CSV_TEMPLATE_HEADERS = [
  "address",
  "order_id",
  "lat",
  "lon",
  "phone",
  "time_window_start",
  "time_window_end",
  "weight",
  "volume",
  "priority",
] as const;

const TIME_RE = /^(\d{1,2}):(\d{2})(:\d{2})?$/;

function parseNonNegative(value: string, label: string, errors: string[]): number | undefined {
  if (!value) return undefined;
  const n = Number(value);
  if (Number.isNaN(n) || n < 0) {
    errors.push(`${label} invalide`);
    return undefined;
  }
  return n;
}

function normalizeTime(value: string, label: string, errors: string[]): string | undefined {
  if (!value) return undefined;
  const m = TIME_RE.exec(value);
  if (!m) {
    errors.push(`${label} doit être au format HH:MM`);
    return undefined;
  }
  const hh = m[1].padStart(2, "0");
  return m[3] ? `${hh}:${m[2]}${m[3]}` : `${hh}:${m[2]}:00`;
}

export function mapRows(rows: Record<string, string>[]): ImportPreview {
  const valid: DeliveryDraft[] = [];
  const invalid: RowError[] = [];

  rows.forEach((r, idx) => {
    const errors: string[] = [];
    const draft: DeliveryDraft = { address: r.address ?? "" };

    if (!draft.address) errors.push("Adresse manquante");
    if (r.order_id) draft.order_id = r.order_id;
    if (r.phone) draft.customer_phone = r.phone;

    const weight = parseNonNegative(r.weight, "Poids", errors);
    if (weight !== undefined) draft.weight = weight;
    const volume = parseNonNegative(r.volume, "Volume", errors);
    if (volume !== undefined) draft.volume = volume;

    if (r.priority) {
      const p = Number(r.priority);
      if (![1, 2, 3].includes(p)) errors.push("Priorité doit être 1, 2 ou 3");
      else draft.priority = p as 1 | 2 | 3;
    }

    const hasLat = Boolean(r.lat);
    const hasLon = Boolean(r.lon);
    if (hasLat !== hasLon) {
      errors.push("lat et lon doivent être fournis ensemble");
    } else if (hasLat && hasLon) {
      const lat = Number(r.lat);
      const lon = Number(r.lon);
      if (Number.isNaN(lat) || lat < -90 || lat > 90) errors.push("Latitude invalide");
      else draft.lat = lat;
      if (Number.isNaN(lon) || lon < -180 || lon > 180) errors.push("Longitude invalide");
      else draft.lon = lon;
    }

    const tws = normalizeTime(r.time_window_start, "Fenêtre (début)", errors);
    const twe = normalizeTime(r.time_window_end, "Fenêtre (fin)", errors);
    if (tws) draft.time_window_start = tws;
    if (twe) draft.time_window_end = twe;
    if (tws && twe && tws > twe) errors.push("Fenêtre horaire: le début est après la fin");

    if (errors.length > 0) {
      invalid.push({ line: idx + 2, errors }); // +2: 1-based + header row
    } else {
      valid.push(draft);
    }
  });

  return { valid, invalid, total: rows.length };
}

export function buildTemplateCsv(): string {
  const example = [
    "12 Rue Didouche Mourad, Alger",
    "CMD-001",
    "",
    "",
    "0550123456",
    "09:00",
    "12:00",
    "5.2",
    "0.3",
    "1",
  ];
  return `${CSV_TEMPLATE_HEADERS.join(",")}\n${example.map(csvCell).join(",")}\n`;
}

function csvCell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}
