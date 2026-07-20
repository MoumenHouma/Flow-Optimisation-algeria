import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { Layout } from "@/components/Layout";

describe("Layout", () => {
  it("renders navigation to every section + logout", () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: /tableau de bord/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /importer/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /optimiser/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /flotte/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /analytics/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /déconnexion/i })).toBeInTheDocument();
  });
});
