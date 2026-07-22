import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TerritoriesPage } from "@/features/territories/TerritoriesPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const ZONES = [
  {
    id: "z1",
    name: "Zone 1",
    color: "#2563EB",
    driver_user_id: "u1",
    centroid: { lat: 36.75, lon: 3.05 },
    delivery_count: 3,
  },
];

describe("TerritoriesPage", () => {
  it("lists zones and auto-generates", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/territories": () => ({ body: ZONES }),
      "GET /api/v1/fleet/drivers": () => ({
        body: [{ id: "u1", email: "a@a.dz", full_name: "Amine", role: "driver" }],
      }),
      "POST /api/v1/territories/auto-generate": () => ({ status: 201, body: ZONES }),
    });
    const user = userEvent.setup();
    renderWithProviders(<TerritoriesPage />, { route: "/territories" });

    await waitFor(() => expect(screen.getByText("Zone 1")).toBeInTheDocument());
    expect(screen.getByText(/3 livraison/)).toBeInTheDocument();
    // Assigned driver shown in the select.
    expect(screen.getByLabelText(/Livreur pour Zone 1/)).toHaveValue("u1");

    await user.click(screen.getByRole("button", { name: /générer automatiquement/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/territories/auto-generate"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("reassigns a driver", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/territories": () => ({ body: ZONES }),
      "GET /api/v1/fleet/drivers": () => ({
        body: [
          { id: "u1", email: "a@a.dz", full_name: "Amine", role: "driver" },
          { id: "u2", email: "y@y.dz", full_name: "Yacine", role: "driver" },
        ],
      }),
      "PUT /api/v1/territories/z1": () => ({ body: { ...ZONES[0], driver_user_id: "u2" } }),
    });
    const user = userEvent.setup();
    renderWithProviders(<TerritoriesPage />, { route: "/territories" });

    await waitFor(() => expect(screen.getByText("Zone 1")).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(/Livreur pour Zone 1/), "u2");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/territories/z1"),
        expect.objectContaining({ method: "PUT" }),
      ),
    );
  });
});
