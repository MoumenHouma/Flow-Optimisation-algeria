import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FuelPage } from "@/features/fuel/FuelPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const STATIONS = [
  {
    id: "s1",
    name: "Naftal Bab Ezzouar",
    location: { lat: 36.72, lon: 3.18 },
    fuel_types: "essence,diesel",
    status: "available",
    notes: null,
  },
];

describe("FuelPage", () => {
  it("lists stations with their status", async () => {
    mockFetch({
      "GET /api/v1/fuel/stations": () => ({ body: STATIONS }),
    });
    renderWithProviders(<FuelPage />, { route: "/fuel" });

    await waitFor(() => expect(screen.getByText("Naftal Bab Ezzouar")).toBeInTheDocument());
    // The status badge renders (Disponible appears as badge + a status button).
    expect(screen.getAllByText("Disponible").length).toBeGreaterThanOrEqual(1);
  });

  it("flags a shortage via PUT", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/fuel/stations": () => ({ body: STATIONS }),
      "PUT /api/v1/fuel/stations/s1/status": () => ({
        body: { ...STATIONS[0], status: "shortage" },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<FuelPage />, { route: "/fuel" });

    await waitFor(() => expect(screen.getByText("Naftal Bab Ezzouar")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Pénurie" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/fuel/stations/s1/status"),
        expect.objectContaining({ method: "PUT" }),
      ),
    );
  });
});
