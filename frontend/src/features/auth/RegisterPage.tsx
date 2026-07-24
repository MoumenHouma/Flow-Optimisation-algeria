import { type FormEvent, useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { useRegister } from "@/api/auth";

// Registration — creates a company + its admin user (docs/PRD.md §2.1 Khaled).
export function RegisterPage() {
  const navigate = useNavigate();
  const register = useRegister();
  const [form, setForm] = useState({ companyName: "", fullName: "", email: "", password: "" });

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    register.mutate(form, { onSuccess: () => navigate("/") });
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-6">
      <h1 className="text-2xl font-bold">Créer une flotte</h1>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        {(
          [
            ["companyName", "Nom de l'entreprise", "text"],
            ["fullName", "Votre nom", "text"],
            ["email", "Email", "email"],
            ["password", "Mot de passe (min. 8)", "password"],
          ] as const
        ).map(([key, label, type]) => (
          <div key={key}>
            <label htmlFor={key} className="block text-sm font-medium">
              {label}
            </label>
            <input
              id={key}
              type={type}
              required
              minLength={type === "password" ? 8 : undefined}
              value={form[key]}
              onChange={update(key)}
              className="mt-1 w-full rounded-lg border border-neutral-300 p-2"
            />
          </div>
        ))}
        {register.isError && (
          <p role="alert" className="text-sm text-danger">
            Impossible de créer le compte (email déjà utilisé ?).
          </p>
        )}
        <button
          type="submit"
          disabled={register.isPending}
          className="w-full rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
        >
          {register.isPending ? "Création…" : "Créer mon compte"}
        </button>
        <p className="text-xs text-neutral-500">
          En créant un compte, vous acceptez les{" "}
          <a
            href="https://routeopt.dz/cgu.html"
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline"
          >
            CGU
          </a>{" "}
          et la{" "}
          <a
            href="https://routeopt.dz/confidentialite.html"
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline"
          >
            politique de confidentialité
          </a>
          .
        </p>
      </form>
      <p className="mt-4 text-sm text-neutral-500">
        Déjà un compte ?{" "}
        <Link to="/login" className="text-primary hover:underline">
          Se connecter
        </Link>
      </p>
    </main>
  );
}
