import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { apiFetch } from "@/lib/api-client";
import { applyBrandColor, resetBrandColor } from "@/lib/branding";
import type { Branding, Company } from "@/types";

export function useCompany() {
  return useQuery({
    queryKey: ["company"],
    queryFn: () => apiFetch<Company>("/api/v1/company"),
  });
}

export function useUpdateBranding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (branding: Branding) =>
      apiFetch<Company>("/api/v1/company/branding", {
        method: "PUT",
        body: JSON.stringify(branding),
      }),
    onSuccess: (company) => qc.setQueryData(["company"], company),
  });
}

// Fetch the company and apply its brand colour to the theme; returns the
// display name + logo for the app shell (F16 white-label).
export function useBranding() {
  const { data } = useCompany();
  const primaryColor = data?.branding?.primary_color ?? null;

  useEffect(() => {
    if (primaryColor) applyBrandColor(primaryColor);
    else resetBrandColor();
  }, [primaryColor]);

  return {
    brandName: data?.branding?.brand_name ?? "RouteOpt",
    logoUrl: data?.branding?.logo_url ?? null,
  };
}
