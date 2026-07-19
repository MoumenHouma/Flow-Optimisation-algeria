import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FleetPage } from "@/features/fleet/FleetPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const VEHICLE = {
  id: "v1",
  name: "Camion 1",
  vehicle_type: "van",
  license_plate: null,
  capacity_weight: 500,
  capacity_volume: 10,
  depot: { lat: 36.75, lon: 3.06 },
  depot_address: "Dépôt Alger",
  active: true,
};

describe("FleetPage", () => {
  it("lists vehicles with the plan quota and deletes on confirm", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/fleet/vehicles": () => ({ body: [VEHICLE] }),
      "GET /api/v1/fleet/summary": () => ({
        body: { plan: "free", vehicle_count: 1, max_vehicles: 1 },
      }),
      "DELETE /api/v1/fleet/vehicles/v1": () => ({ status: 204, body: null }),
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderWithProviders(<FleetPage />);

    await waitFor(() => expect(screen.getByText("Camion 1")).toBeInTheDocument());
    expect(screen.getByText(/1 \/ 1 véhicules · plan free/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /supprimer camion 1/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/fleet/vehicles/v1"),
        expect.objectContaining({ method: "DELETE" }),
      ),
    );
  });

  it("disables adding when the quota is reached", async () => {
    mockFetch({
      "GET /api/v1/fleet/vehicles": () => ({ body: [VEHICLE] }),
      "GET /api/v1/fleet/summary": () => ({
        body: { plan: "free", vehicle_count: 1, max_vehicles: 1 },
      }),
    });
    renderWithProviders(<FleetPage />);

    await waitFor(() => expect(screen.getByText("Camion 1")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /ajouter un véhicule/i })).toBeDisabled();
  });
});
