import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DashboardPage } from "@/features/dashboard/DashboardPage";

describe("DashboardPage", () => {
  it("renders the heading", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: /tableau de bord/i })).toBeInTheDocument();
  });
});
