import { type FormEvent, useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { useLogin } from "@/api/auth";

// Login screen — minimal, accessible form (docs/DESIGN.md §7).
export function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => navigate("/") });
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-6">
      <h1 className="text-2xl font-bold">Connexion</h1>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 p-2"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 p-2"
          />
        </div>
        {login.isError && (
          <p role="alert" className="text-sm text-danger">
            Email ou mot de passe invalide.
          </p>
        )}
        <button
          type="submit"
          disabled={login.isPending}
          className="w-full rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
        >
          {login.isPending ? "Connexion…" : "Se connecter"}
        </button>
      </form>
      <p className="mt-4 text-sm text-neutral-500">
        <Link to="/forgot-password" className="text-primary hover:underline">
          Mot de passe oublié ?
        </Link>
      </p>
      <p className="mt-2 text-sm text-neutral-500">
        Pas de compte ?{" "}
        <Link to="/register" className="text-primary hover:underline">
          Créer une flotte
        </Link>
      </p>
    </main>
  );
}
