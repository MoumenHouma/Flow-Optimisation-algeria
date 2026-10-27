import { type FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { useResetPassword } from "@/api/auth";

// Consumes the ?token=… from the emailed link. The token is single-use and the
// server revokes every session on success, so we send the user back to /login.
export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const reset = useResetPassword();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mismatch, setMismatch] = useState(false);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setMismatch(true);
      return;
    }
    setMismatch(false);
    reset.mutate({ token, password }, { onSuccess: () => navigate("/login") });
  };

  if (!token) {
    return (
      <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-6">
        <h1 className="text-2xl font-bold">Lien invalide</h1>
        <p role="alert" className="mt-2 text-sm text-danger">
          Ce lien de réinitialisation est incomplet. Demandez-en un nouveau.
        </p>
        <Link to="/forgot-password" className="mt-4 text-sm text-primary hover:underline">
          Renvoyer un lien
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-6">
      <h1 className="text-2xl font-bold">Nouveau mot de passe</h1>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="password" className="block text-sm font-medium">
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 p-2"
          />
          <p className="mt-1 text-xs text-neutral-500">8 caractères minimum.</p>
        </div>
        <div>
          <label htmlFor="confirm" className="block text-sm font-medium">
            Confirmer le mot de passe
          </label>
          <input
            id="confirm"
            type="password"
            required
            minLength={8}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 p-2"
          />
        </div>
        {mismatch && (
          <p role="alert" className="text-sm text-danger">
            Les deux mots de passe ne correspondent pas.
          </p>
        )}
        {reset.isError && (
          <p role="alert" className="text-sm text-danger">
            Ce lien est expiré ou a déjà été utilisé. Demandez-en un nouveau.
          </p>
        )}
        <button
          type="submit"
          disabled={reset.isPending}
          className="w-full rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
        >
          {reset.isPending ? "Enregistrement…" : "Changer le mot de passe"}
        </button>
      </form>
      <p className="mt-4 text-sm text-neutral-500">
        <Link to="/login" className="text-primary hover:underline">
          Retour à la connexion
        </Link>
      </p>
    </main>
  );
}
