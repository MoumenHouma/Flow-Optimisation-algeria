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
  orderId?: string;
  address: string;
  lat?: number;
  lon?: number;
  timeWindowStart?: string;
  timeWindowEnd?: string;
  weight: number;
  volume: number;
  priority: 1 | 2 | 3;
  status: DeliveryStatus;
}

export interface Vehicle {
  id: string;
  name: string;
  vehicleType: "car" | "van" | "truck" | "motorcycle";
  capacityWeight: number;
  capacityVolume: number;
  depot: GeoPoint;
  active: boolean;
}

export interface RouteStop {
  deliveryId: string;
  sequence: number;
  eta?: string;
}

export interface RouteResult {
  id: string;
  vehicleId?: string;
  totalDistanceM?: number;
  totalTimeS?: number;
  status: string;
  stops: RouteStop[];
}

export interface OptimizeResponse {
  jobId: string;
  status: JobStatus;
  estimatedDurationMs: number;
}
