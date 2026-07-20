import {
  LayoutDashboard,
  Upload,
  Navigation,
  Truck,
  BarChart3,
  LogOut,
  Languages,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuthStore } from "@/stores/auth-store";
import { isRTL, useUIStore } from "@/stores/ui-store";

// App shell: top nav + routed content (docs/DESIGN.md §3.2, §6 RTL).
const NAV = [
  { to: "/", label: "Tableau de bord", icon: LayoutDashboard, end: true },
  { to: "/import", label: "Importer", icon: Upload, end: false },
  { to: "/optimize", label: "Optimiser", icon: Navigation, end: false },
  { to: "/fleet", label: "Flotte", icon: Truck, end: false },
  { to: "/analytics", label: "Analytics", icon: BarChart3, end: false },
];

export function Layout() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const locale = useUIStore((s) => s.locale);
  const setLocale = useUIStore((s) => s.setLocale);

  const logout = () => {
    clear();
    navigate("/login", { replace: true });
  };

  return (
    <div dir={isRTL(locale) ? "rtl" : "ltr"} className="min-h-screen bg-neutral-50">
      <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="text-lg font-bold text-primary">RouteOpt 📦</span>
            <nav className="flex items-center gap-1 overflow-x-auto">
              {NAV.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${
                      isActive
                        ? "bg-primary-light text-primary-dark"
                        : "text-neutral-600 hover:bg-neutral-100"
                    }`
                  }
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setLocale(locale === "ar" ? "fr" : "ar")}
              aria-label="Changer de langue"
              className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-100"
            >
              <Languages className="h-4 w-4" aria-hidden="true" />
              {locale === "ar" ? "AR" : "FR"}
            </button>
            <button
              onClick={logout}
              className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-100"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl">
        <Outlet />
      </div>
    </div>
  );
}
