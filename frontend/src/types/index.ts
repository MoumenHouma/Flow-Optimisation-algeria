// Domain types mirroring the API DTOs (docs/SCHEMA.md, backend schemas).

export type DeliveryStatus =
  "pending" | "geocoded" | "assigned" | "en_route" | "delivered" | "failed" | "cancelled";

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface GeoPoint {
  lat: number;
  lon: number;
}

export interface Delivery {
  id: string;
  order_id?: string;
  address: string;
  lat?: number;
  lon?: number;
  geocoding_status: string;
  weight: number;
  volume: number;
  priority: 1 | 2 | 3;
  status: DeliveryStatus;
}

// Client-side draft built from a CSV row, sent to POST /orders.
export interface DeliveryDraft {
  address: string;
  order_id?: string;
  lat?: number;
  lon?: number;
  customer_phone?: string;
  time_window_start?: string;
  time_window_end?: string;
  weight?: number;
  volume?: number;
  priority?: 1 | 2 | 3;
}

export interface BulkCreateResponse {
  created: number;
  geocoding_pending: number;
  deliveries: Delivery[];
}

export type VehicleType = "car" | "van" | "truck" | "motorcycle";

export interface Vehicle {
  id: string;
  name: string;
  vehicle_type: VehicleType;
  license_plate?: string;
  capacity_weight: number;
  capacity_volume: number;
  depot: GeoPoint;
  depot_address: string;
  active: boolean;
}

// Payload for POST/PUT /fleet/vehicles.
export interface VehicleDraft {
  name: string;
  vehicle_type: VehicleType;
  license_plate?: string;
  capacity_weight: number;
  capacity_volume: number;
  depot: GeoPoint;
  depot_address: string;
}

export interface FleetSummary {
  plan: string;
  vehicle_count: number;
  max_vehicles: number | null; // null => unlimited (Enterprise)
}

export interface DriverStop {
  delivery_id: string;
  sequence: number;
  address: string;
  lat: number | null;
  lon: number | null;
  customer_phone: string | null;
  time_window_start: string | null;
  time_window_end: string | null;
  status: DeliveryStatus;
}

export interface DriverRoute {
  route_id: string;
  vehicle_name: string | null;
  total_distance_m: number | null;
  delivered: number;
  total: number;
  stops: DriverStop[];
}

export interface ProofOfDelivery {
  delivery_id: string;
  photo_url: string | null;
  signature_url: string | null;
  lat: number | null;
  lon: number | null;
  captured_at: string;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scope: "read" | "write" | "admin";
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
}

export interface WebhookCreated extends Webhook {
  secret: string;
}

export interface TrendPoint {
  date: string;
  deliveries_completed: number;
  deliveries_failed: number;
  routes: number;
  distance_m: number;
}

export interface Trends {
  days: number;
  points: TrendPoint[];
}

export interface FailureReason {
  reason: string;
  count: number;
}

export interface DriverStat {
  driver_id: string;
  driver_name: string;
  delivered: number;
  failed: number;
}

export interface Performance {
  range_days: number;
  delivered: number;
  failed: number;
  success_rate: number;
  total_distance_m: number;
  routes: number;
  avg_distance_per_route_m: number;
  failure_reasons: FailureReason[];
  drivers: DriverStat[];
}

export interface DashboardSummary {
  date: string;
  deliveries_total: number;
  deliveries_by_status: Record<string, number>;
  vehicles_active: number;
  vehicles_total: number;
  today_routes: number;
  today_distance_m: number;
  today_time_s: number;
  week_optimizations: number;
  week_distance_m: number;
}

export interface RouteStop {
  delivery_id: string;
  sequence: number;
  eta?: string;
  lat?: number | null;
  lon?: number | null;
  address?: string | null;
}

export interface LineStringGeometry {
  type: "LineString";
  coordinates: [number, number][]; // [lon, lat]
}

export interface RouteResult {
  id: string;
  vehicle_id?: string;
  total_distance_m?: number;
  total_time_s?: number;
  status: string;
  depot?: GeoPoint | null;
  geometry?: LineStringGeometry | null;
  stops: RouteStop[];
}

// API responses are snake_case (FastAPI); these mirror the wire shape.
export interface OptimizeResponse {
  job_id: string;
  status: JobStatus;
  estimated_duration_ms: number;
}

export interface JobResult {
  job_id: string;
  status: JobStatus;
  delivery_count?: number;
  vehicle_count?: number;
  solver_strategy?: string;
  duration_ms?: number;
  total_distance_m?: number;
  route_ids: string[];
  error_message?: string;
}
