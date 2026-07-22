import type { ReactElement } from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

// Render a component inside the app's providers (React Query + Router).
export function renderWithProviders(ui: ReactElement, { route = "/" } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

interface MockResponse {
  status?: number;
  body?: unknown;
}
type Handler = () => MockResponse;

// Stub global fetch, routing by "METHOD /pathname" to a canned response.
export function mockFetch(handlers: Record<string, Handler>) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = (init?.method ?? "GET").toUpperCase();
    const pathname = new URL(url, "http://test.local").pathname;
    const handler = handlers[`${method} ${pathname}`] as Handler | undefined;
    const res: MockResponse = handler !== undefined ? handler() : { status: 404 };
    const status = res.status ?? 200;
    const body = "body" in res ? res.body : {}; // preserve an explicit null body
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
      text: async () => (body == null ? "" : JSON.stringify(body)),
      blob: async () => new Blob([JSON.stringify(body ?? "")]),
    } as Response;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
