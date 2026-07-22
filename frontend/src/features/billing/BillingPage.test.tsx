import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BillingPage } from "@/features/billing/BillingPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const FREE_BILLING = {
  plan: "free",
  price_da: 0,
  status: "none",
  usage: {
    vehicles: 1,
    max_vehicles: 1,
    deliveries_today: 10,
    max_deliveries_per_day: 10,
    deliveries_this_month: 40,
  },
};

const INVOICES = [
  {
    id: "i1",
    period: "2026-07",
    plan: "starter",
    amount_da: 2500,
    status: "paid",
    method: "baridimob",
    reference: "TX-42",
    issued_at: "2026-07-01T00:00:00+00:00",
    paid_at: "2026-07-02T00:00:00+00:00",
  },
];

describe("BillingPage", () => {
  it("shows the plan, a maxed usage bar and invoices", async () => {
    mockFetch({
      "GET /api/v1/billing": () => ({ body: FREE_BILLING }),
      "GET /api/v1/billing/invoices": () => ({ body: INVOICES }),
    });
    renderWithProviders(<BillingPage />, { route: "/billing" });

    await waitFor(() => expect(screen.getByText("2026-07")).toBeInTheDocument());
    // "Free" appears as both the current-plan header and a plan button.
    expect(screen.getAllByText("Free").length).toBeGreaterThanOrEqual(1);
    // Usage is at the cap — the quota warning renders.
    expect(screen.getAllByText(/Quota atteint/).length).toBeGreaterThanOrEqual(1);
  });

  it("changes plan via PUT", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/billing": () => ({ body: FREE_BILLING }),
      "GET /api/v1/billing/invoices": () => ({ body: [] }),
      "PUT /api/v1/billing/plan": () => ({ body: { ...FREE_BILLING, plan: "pro" } }),
    });
    const user = userEvent.setup();
    renderWithProviders(<BillingPage />, { route: "/billing" });

    await waitFor(() => expect(screen.getByRole("button", { name: "Pro" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Pro" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/billing/plan"),
        expect.objectContaining({ method: "PUT" }),
      ),
    );
  });
});
