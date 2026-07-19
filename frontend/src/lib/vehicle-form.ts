// Parses + validates raw vehicle-form fields (strings) into a VehicleDraft.
// Kept pure so the rules are unit-testable independently of the React form.

import type { Vehicle, VehicleDraft, VehicleType } from "@/types";

export interface VehicleFormValues {
  name: string;
  vehicle_type: string;
  license_plate: string;
  capacity_weight: string;
  capacity_volume: string;
  lat: string;
  lon: string;
  depot_address: string;
}

export type VehicleFormErrors = Partial<Record<keyof VehicleFormValues, string>>;

export const EMPTY_VEHICLE_FORM: VehicleFormValues = {
  name: "",
  vehicle_type: "van",
  license_plate: "",
  capacity_weight: "1000",
  capacity_volume: "10",
  lat: "",
  lon: "",
  depot_address: "",
};

export const VEHICLE_TYPES: VehicleType[] = ["car", "van", "truck", "motorcycle"];

export function vehicleToForm(v: Vehicle): VehicleFormValues {
  return {
    name: v.name,
    vehicle_type: v.vehicle_type,
    license_plate: v.license_plate ?? "",
    capacity_weight: String(v.capacity_weight),
    capacity_volume: String(v.capacity_volume),
    lat: String(v.depot.lat),
    lon: String(v.depot.lon),
    depot_address: v.depot_address,
  };
}

function positiveNumber(value: string, label: string, errors: string[]): number | undefined {
  const n = Number(value);
  if (value.trim() === "" || Number.isNaN(n) || n < 0) {
    errors.push(label);
    return undefined;
  }
  return n;
}

export function parseVehicleForm(values: VehicleFormValues): {
  draft: VehicleDraft | null;
  errors: VehicleFormErrors;
} {
  const errors: VehicleFormErrors = {};

  if (!values.name.trim()) errors.name = "Nom requis";
  if (!VEHICLE_TYPES.includes(values.vehicle_type as VehicleType)) {
    errors.vehicle_type = "Type invalide";
  }
  if (!values.depot_address.trim()) errors.depot_address = "Adresse du dépôt requise";

  const weightErr: string[] = [];
  const weight = positiveNumber(values.capacity_weight, "x", weightErr);
  if (weightErr.length) errors.capacity_weight = "Poids ≥ 0 requis";

  const volumeErr: string[] = [];
  const volume = positiveNumber(values.capacity_volume, "x", volumeErr);
  if (volumeErr.length) errors.capacity_volume = "Volume ≥ 0 requis";

  const lat = Number(values.lat);
  if (values.lat.trim() === "" || Number.isNaN(lat) || lat < -90 || lat > 90) {
    errors.lat = "Latitude entre -90 et 90";
  }
  const lon = Number(values.lon);
  if (values.lon.trim() === "" || Number.isNaN(lon) || lon < -180 || lon > 180) {
    errors.lon = "Longitude entre -180 et 180";
  }

  if (Object.keys(errors).length > 0 || weight === undefined || volume === undefined) {
    return { draft: null, errors };
  }

  return {
    draft: {
      name: values.name.trim(),
      vehicle_type: values.vehicle_type as VehicleType,
      license_plate: values.license_plate.trim() || undefined,
      capacity_weight: weight,
      capacity_volume: volume,
      depot: { lat, lon },
      depot_address: values.depot_address.trim(),
    },
    errors: {},
  };
}
