import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DriverPage } from "@/features/driver/DriverPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const ROUTE = {
  route_id: "r1",
  vehicle_name: "Fourgon 1",
  total_distance_m: 1000,
  delivered: 0,
  total: 2,
  stops: [
    {
      delivery_id: "d1",
      sequence: 0,
      address: "12 Rue Didouche Mourad",
      lat: 36.75,
      lon: 3.06,
      customer_phone: "0550123456",
      time_window_start: "09:00",
      time_window_end: "12:00",
      status: "assigned",
    },
    {
      delivery_id: "d2",
      sequence: 1,
      address: "45 Bd Mohamed V",
      lat: 36.76,
      lon: 3.07,
      customer_phone: null,
      time_window_start: null,
      time_window_end: null,
      status: "assigned",
    },
  ],
};

describe("DriverPage", () => {
  it("shows the current stop with progress and marks it delivered", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/driver/route": () => ({ body: ROUTE }),
      "PUT /api/v1/driver/deliveries/d1/status": () => ({ body: { id: "d1", status: "delivered" } }),
    });
    const user = userEvent.setup();
    renderWithProviders(<DriverPage />, { route: "/driver" });

    await waitFor(() => expect(screen.getByText(/12 Rue Didouche Mourad/)).toBeInTheDocument());
    expect(screen.getByText("0/2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /livré/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/driver/deliveries/d1/status"),
        expect.objectContaining({ method: "PUT" }),
      ),
    );
  });

  it("shows an empty state when no route is assigned", async () => {
    mockFetch({ "GET /api/v1/driver/route": () => ({ body: null }) });
    renderWithProviders(<DriverPage />, { route: "/driver" });
    await waitFor(() =>
      expect(screen.getByText(/aucune tournée assignée/i)).toBeInTheDocument(),
    );
  });
});
