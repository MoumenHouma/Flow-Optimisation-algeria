import { Check, Palette } from "lucide-react";
import { useEffect, useState } from "react";

import { useCompany, useUpdateBranding } from "@/api/company";

// White-label branding editor (F16, admin).
export function BrandingSettings() {
  const { data: company } = useCompany();
  const update = useUpdateBranding();
  const [brandName, setBrandName] = useState("");
  const [color, setColor] = useState("#2563EB");
  const [logoUrl, setLogoUrl] = useState("");

  // Hydrate the form once the company loads.
  useEffect(() => {
    const b = company?.branding;
    if (b) {
      setBrandName(b.brand_name ?? "");
      setColor(b.primary_color ?? "#2563EB");
      setLogoUrl(b.logo_url ?? "");
    }
  }, [company?.branding]);

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    update.mutate({
      brand_name: brandName.trim() || null,
      primary_color: color,
      logo_url: logoUrl.trim() || null,
    });
  };

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <h2 className="flex items-center gap-2 font-semibold">
        <Palette className="h-4 w-4 text-primary" aria-hidden="true" /> Marque (white-label)
      </h2>
      <p className="mt-1 text-sm text-neutral-500">
        Personnalisez le nom, la couleur et le logo affichés dans l'application.
      </p>

      <form onSubmit={save} className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="text-xs font-medium text-neutral-500">Nom de marque</span>
          <input
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            placeholder="RouteOpt"
            className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="text-xs font-medium text-neutral-500">Couleur principale</span>
          <span className="mt-1 flex items-center gap-2">
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              aria-label="Couleur principale"
              className="h-9 w-12 rounded border border-neutral-300"
            />
            <input
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="w-28 rounded-lg border border-neutral-300 px-3 py-2 font-mono text-sm"
            />
          </span>
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="text-xs font-medium text-neutral-500">URL du logo</span>
          <input
            value={logoUrl}
            onChange={(e) => setLogoUrl(e.target.value)}
            placeholder="https://…/logo.png"
            className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2"
          />
        </label>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={update.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-50"
          >
            <Check className="h-4 w-4" aria-hidden="true" /> Enregistrer
          </button>
          {update.isSuccess && <span className="ml-3 text-sm text-success">Enregistré ✓</span>}
        </div>
      </form>
    </section>
  );
}
