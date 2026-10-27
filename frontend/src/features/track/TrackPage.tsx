import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { fetchTrack } from "@/api/tracking";

const STATUS_LABELS: Record<string, string> = {
  pending: "En préparation",
  geocoded: "En préparation",
  assigned: "Prise en charge",
  en_route: "En cours de livraison",
  delivered: "Livré",
  failed: "Échec de livraison",
  cancelled: "Annulé",
};

// Public customer tracking page (F18). No auth — reached via a signed link in
// the delivery notification. Shows status and, while en route, the live dot.
export function TrackPage() {
  const { token = "" } = useParams();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["track", token],
    queryFn: () => fetchTrack(token),
    refetchInterval: 15000,
    retry: false,
  });

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center bg-neutral-50 px-4 pt-16">
      <div className="w-full rounded-2xl bg-white p-6 shadow-sm">
        <h1 className="text-center text-lg font-bold text-primary">Suivi de livraison 📦</h1>

        {isLoading && <p className="mt-6 text-center text-neutral-500">Chargement…</p>}

        {isError && (
          <p className="mt-6 text-center text-danger">Lien de suivi invalide ou expiré.</p>
        )}

        {data && (
          <div className="mt-6 text-center">
            {data.order_id && <p className="text-sm text-neutral-500">Commande {data.order_id}</p>}
            <p className="mt-2 text-2xl font-bold text-neutral-900">
              {STATUS_LABELS[data.status] ?? data.status}
            </p>
            {data.vehicle_position ? (
              <p className="mt-4 text-sm text-neutral-600">
                🚐 Votre livreur est en route. Position :{" "}
                <span className="font-mono">
                  {data.vehicle_position.lat.toFixed(4)}, {data.vehicle_position.lon.toFixed(4)}
                </span>
              </p>
            ) : (
              <p className="mt-4 text-sm text-neutral-500">
                Position du livreur indisponible pour le moment.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
