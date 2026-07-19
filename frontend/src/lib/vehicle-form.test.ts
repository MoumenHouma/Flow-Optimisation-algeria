import { describe, expect, it } from "vitest";

import { EMPTY_VEHICLE_FORM, parseVehicleForm } from "@/lib/vehicle-form";

const valid = {
  ...EMPTY_VEHICLE_FORM,
  name: "Camion 1",
  lat: "36.7538",
  lon: "3.0588",
  depot_address: "Dépôt Alger Centre",
};

describe("parseVehicleForm", () => {
  it("builds a draft from valid values", () => {
    const { draft, errors } = parseVehicleForm(valid);
    expect(errors).toEqual({});
    expect(draft).toEqual({
      name: "Camion 1",
      vehicle_type: "van",
      license_plate: undefined,
      capacity_weight: 1000,
      capacity_volume: 10,
      depot: { lat: 36.7538, lon: 3.0588 },
      depot_address: "Dépôt Alger Centre",
    });
  });

  it("requires name and depot address", () => {
    const { draft, errors } = parseVehicleForm({ ...valid, name: " ", depot_address: "" });
    expect(draft).toBeNull();
    expect(errors.name).toBeDefined();
    expect(errors.depot_address).toBeDefined();
  });

  it("rejects out-of-range coordinates", () => {
    const { errors } = parseVehicleForm({ ...valid, lat: "99", lon: "200" });
    expect(errors.lat).toBeDefined();
    expect(errors.lon).toBeDefined();
  });

  it("rejects negative or non-numeric capacities", () => {
    const { errors } = parseVehicleForm({ ...valid, capacity_weight: "-5", capacity_volume: "x" });
    expect(errors.capacity_weight).toBeDefined();
    expect(errors.capacity_volume).toBeDefined();
  });

  it("rejects an unknown vehicle type", () => {
    const { errors } = parseVehicleForm({ ...valid, vehicle_type: "boat" });
    expect(errors.vehicle_type).toBeDefined();
  });
});
