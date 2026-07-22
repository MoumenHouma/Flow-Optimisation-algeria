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
      "GET /api/v1/fleet/depots": () => ({ body: [] }),
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
      "GET /api/v1/fleet/depots": () => ({ body: [] }),
    });
    renderWithProviders(<FleetPage />);

    await waitFor(() => expect(screen.getByText("Camion 1")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /ajouter un véhicule/i })).toBeDisabled();
  });

  it("adds a depot (F12 multi-dépôt)", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/fleet/vehicles": () => ({ body: [] }),
      "GET /api/v1/fleet/summary": () => ({
        body: { plan: "pro", vehicle_count: 0, max_vehicles: 20 },
      }),
      "GET /api/v1/fleet/depots": () => ({ body: [] }),
      "POST /api/v1/fleet/depots": () => ({
        status: 201,
        body: {
          id: "d1",
          name: "Entrepôt Alger",
          location: { lat: 36.75, lon: 3.05 },
          address: "Alger",
          active: true,
        },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<FleetPage />);

    await waitFor(() => expect(screen.getByText("Dépôts")).toBeInTheDocument());

    await user.type(screen.getByLabelText("Nom du dépôt"), "Entrepôt Alger");
    await user.type(screen.getByLabelText("Adresse du dépôt"), "Alger");
    await user.type(screen.getByLabelText("Latitude"), "36.75");
    await user.type(screen.getByLabelText("Longitude"), "3.05");
    await user.click(screen.getByRole("button", { name: /ajouter un dépôt/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/fleet/depots"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
