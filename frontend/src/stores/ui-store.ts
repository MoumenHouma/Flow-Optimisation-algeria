import { create } from "zustand";

// Global UI state (docs/RULES.md §3.2 — Zustand for UI, React Query for server state).
interface UIState {
  sidebarOpen: boolean;
  activeRouteId: string | null;
  locale: "fr" | "ar" | "ar-dz";
  toggleSidebar: () => void;
  setActiveRoute: (id: string | null) => void;
  setLocale: (locale: UIState["locale"]) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  activeRouteId: null,
  locale: "fr",
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveRoute: (id) => set({ activeRouteId: id }),
  setLocale: (locale) => set({ locale }),
}));

export const isRTL = (locale: UIState["locale"]): boolean => locale.startsWith("ar");
