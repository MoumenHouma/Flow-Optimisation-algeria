import { ArrowRight, CircleCheck, CircleDashed } from "lucide-react";
import { Link } from "react-router-dom";

import type { DashboardSummary } from "@/types";

// First-run guide: a fresh company lands on an empty dashboard with no idea what
// to do first. Drives entirely off the dashboard summary (no extra request) and
// disappears once the company has both a vehicle and a delivery.
interface Step {
  done: boolean;
  title: string;
  description: string;
  to: string;
  cta: string;
}

export function OnboardingChecklist({ data }: { data: DashboardSummary }) {
  const hasVehicle = data.vehicles_total > 0;
  const hasDelivery = data.deliveries_total > 0;
  const hasRoute = data.today_routes > 0 || data.week_optimizations > 0;

  // Nothing to guide once the fleet is set up and deliveries exist.
  if (hasVehicle && hasDelivery) return null;

  const steps: Step[] = [
    {
      done: hasVehicle,
      title: "Ajoutez un véhicule",
      description: "Capacité, point de départ et autonomie carburant.",
      to: "/fleet",
      cta: "Gérer la flotte",
    },
    {
      done: hasDelivery,
      title: "Importez vos livraisons",
      description: "Un fichier CSV d’adresses — un modèle est téléchargeable.",
      to: "/import",
      cta: "Importer un fichier",
    },
    {
      done: hasRoute,
      title: "Optimisez une tournée",
      description: "RouteOpt calcule l’ordre de passage de chaque véhicule.",
      to: "/optimize",
      cta: "Planifier une tournée",
    },
  ];
  const nextStep = steps.find((s) => !s.done);

  return (
    <section
      aria-labelledby="onboarding-title"
      className="mt-6 rounded-lg border border-primary/30 bg-primary/5 p-4"
    >
      <h2 id="onboarding-title" className="text-sm font-semibold text-neutral-800">
        Premiers pas
      </h2>
      <p className="mt-1 text-sm text-neutral-600">
        Trois étapes pour votre première tournée optimisée.
      </p>
      <ol className="mt-4 space-y-3">
        {steps.map((step) => {
          const isNext = step === nextStep;
          return (
            <li key={step.to} className="flex items-start gap-3">
              {step.done ? (
                <CircleCheck className="mt-0.5 h-5 w-5 shrink-0 text-success" aria-hidden="true" />
              ) : (
                <CircleDashed
                  className="mt-0.5 h-5 w-5 shrink-0 text-neutral-400"
                  aria-hidden="true"
                />
              )}
              <div className="min-w-0 flex-1">
                <p
                  className={
                    step.done ? "text-sm text-neutral-400 line-through" : "text-sm font-medium"
                  }
                >
                  {step.title}
                </p>
                {!step.done && <p className="text-sm text-neutral-500">{step.description}</p>}
              </div>
              {!step.done && (
                <Link
                  to={step.to}
                  className={
                    isNext
                      ? "inline-flex shrink-0 items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-dark"
                      : "inline-flex shrink-0 items-center gap-1 text-sm text-primary hover:underline"
                  }
                >
                  {step.cta}
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
