// Domain types mirroring the API DTOs (docs/SCHEMA.md, backend schemas).

export type DeliveryStatus =
  | "pending"
  | "geocoded"
  | "assigned"
  | "en_route"
  | "delivered"
  | "failed"
  | "cancelled";

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
}

export interface RouteResult {
  id: string;
  vehicle_id?: string;
  total_distance_m?: number;
  total_time_s?: number;
  status: string;
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
