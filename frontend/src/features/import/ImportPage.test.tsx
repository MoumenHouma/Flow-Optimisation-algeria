import userEvent from "@testing-library/user-event";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImportPage } from "@/features/import/ImportPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const CSV = "address,weight\n12 Rue Didouche Mourad,5\n45 Bd Mohamed V,8\n";

describe("ImportPage", () => {
  it("parses an uploaded CSV, previews it, and imports", async () => {
    const fetchMock = mockFetch({
      "POST /api/v1/orders": () => ({
        status: 201,
        body: {
          created: 2,
          geocoding_pending: 0,
          deliveries: [
            { id: "d1", geocoding_status: "matched" },
            { id: "d2", geocoding_status: "matched" },
          ],
        },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<ImportPage />);

    const file = new File([CSV], "deliveries.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText(/choisir un fichier csv/i), file);

    // Preview shows the valid count
    await waitFor(() => expect(screen.getByText(/2 valides/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /importer 2 livraisons/i }));

    await waitFor(() => expect(screen.getByText(/2 livraisons importées/i)).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/orders"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("rejects a non-CSV file", async () => {
    mockFetch({});
    renderWithProviders(<ImportPage />);

    const input = screen.getByLabelText(/choisir un fichier csv/i);
    const file = new File(["x"], "data.xlsx", { type: "application/vnd.ms-excel" });
    // fireEvent bypasses the input's accept filter so our handler runs and rejects it.
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/exportez votre fichier excel en csv/i),
    );
  });
});
