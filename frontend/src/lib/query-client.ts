import { QueryClient } from "@tanstack/react-query";

// Server-state cache (docs/RULES.md §3.2).
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});
