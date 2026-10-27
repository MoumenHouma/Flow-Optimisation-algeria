import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OnboardingChecklist } from "@/features/dashboard/OnboardingChecklist";
import { renderWithProviders } from "@/test-utils";
import type { DashboardSummary } from "@/types";

function summary(overrides: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    date: "2026-07-24",
    deliveries_total: 0,
    deliveries_by_status: {},
    vehicles_active: 0,
    vehicles_total: 0,
    today_routes: 0,
    today_distance_m: 0,
    today_time_s: 0,
    week_optimizations: 0,
    week_distance_m: 0,
    ...overrides,
  };
}

describe("OnboardingChecklist", () => {
  it("shows all three steps for a brand-new company", () => {
    renderWithProviders(<OnboardingChecklist data={summary()} />);
    expect(screen.getByText("Premiers pas")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /gérer la flotte/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /importer un fichier/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /planifier une tournée/i })).toBeInTheDocument();
  });

  it("marks the vehicle step done once a vehicle exists", () => {
    renderWithProviders(<OnboardingChecklist data={summary({ vehicles_total: 2 })} />);
    // The completed step drops its CTA; the next two remain actionable.
    expect(screen.queryByRole("link", { name: /gérer la flotte/i })).toBeNull();
    expect(screen.getByRole("link", { name: /importer un fichier/i })).toBeInTheDocument();
  });

  it("hides itself once the company has vehicles and deliveries", () => {
    const { container } = renderWithProviders(
      <OnboardingChecklist data={summary({ vehicles_total: 3, deliveries_total: 12 })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
