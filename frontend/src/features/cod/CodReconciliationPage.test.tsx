import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CodReconciliationPage } from "@/features/cod/CodReconciliationPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const SUMMARY = {
  rows: [
    {
      driver_user_id: "u1",
      day: "2026-07-22",
      count: 2,
      total_expected: 3500,
      total_collected: 3300,
      discrepancies: 1,
    },
  ],
  total_expected: 3500,
  total_collected: 3300,
  discrepancies: 1,
};

const PAYMENTS = [
  {
    id: "c1",
    delivery_id: "d1",
    order_id: "CMD-1",
    route_id: "r1",
    driver_user_id: "u1",
    amount_expected: 1500,
    amount_collected: 1500,
    currency: "DZD",
    method: "cash",
    status: "collected",
    collected_at: "2026-07-22T10:00:00+00:00",
  },
  {
    id: "c2",
    delivery_id: "d2",
    order_id: "CMD-2",
    route_id: "r1",
    driver_user_id: "u1",
    amount_expected: 2000,
    amount_collected: 1800,
    currency: "DZD",
    method: "cash",
    status: "discrepancy",
    collected_at: "2026-07-22T11:00:00+00:00",
  },
];

describe("CodReconciliationPage", () => {
  it("renders totals, the summary table and payment rows", async () => {
    mockFetch({
      "GET /api/v1/cod/summary": () => ({ body: SUMMARY }),
      "GET /api/v1/cod/payments": () => ({ body: PAYMENTS }),
    });
    renderWithProviders(<CodReconciliationPage />, { route: "/cod" });

    await waitFor(() => expect(screen.getByText("CMD-1")).toBeInTheDocument());
    expect(screen.getByText("CMD-2")).toBeInTheDocument();
    // One discrepancy shows in the KPI and the summary row.
    expect(screen.getByText("Écart")).toBeInTheDocument();
  });

  it("reconciles a record via PUT", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/cod/summary": () => ({ body: SUMMARY }),
      "GET /api/v1/cod/payments": () => ({ body: PAYMENTS }),
      "PUT /api/v1/cod/payments/c1": () => ({ body: { ...PAYMENTS[0], status: "reconciled" } }),
    });
    const user = userEvent.setup();
    renderWithProviders(<CodReconciliationPage />, { route: "/cod" });

    await waitFor(() => expect(screen.getByText("CMD-1")).toBeInTheDocument());
    await user.click(screen.getAllByRole("button", { name: "Valider" })[0]);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/cod/payments/c1"),
        expect.objectContaining({ method: "PUT" }),
      ),
    );
  });
});
