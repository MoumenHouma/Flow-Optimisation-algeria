import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { useForgotPassword } from "@/api/auth";

// Password-recovery request. The confirmation is deliberately identical whether
// or not the address is registered — the API never reveals it either.
export function ForgotPasswordPage() {
  const forgot = useForgotPassword();
  const [email, setEmail] = useState("");

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    forgot.mutate(email);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-6">
      <h1 className="text-2xl font-bold">Mot de passe oublié</h1>
      {forgot.isSuccess ? (
        <div className="mt-6 space-y-4">
          <p role="status" className="text-sm">
            Si un compte existe pour <span className="font-medium">{email}</span>, un lien de
            réinitialisation vient d’être envoyé. Le lien est valable 60 minutes.
          </p>
          <Link to="/login" className="block text-sm text-primary hover:underline">
            Retour à la connexion
          </Link>
        </div>
      ) : (
        <>
          <p className="mt-2 text-sm text-neutral-500">
            Indiquez votre email : nous vous envoyons un lien pour choisir un nouveau mot de passe.
          </p>
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
            {forgot.isError && (
              <p role="alert" className="text-sm text-danger">
                Envoi impossible pour le moment. Réessayez dans une minute.
              </p>
            )}
            <button
              type="submit"
              disabled={forgot.isPending}
              className="w-full rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
            >
              {forgot.isPending ? "Envoi…" : "Envoyer le lien"}
            </button>
          </form>
          <p className="mt-4 text-sm text-neutral-500">
            <Link to="/login" className="text-primary hover:underline">
              Retour à la connexion
            </Link>
          </p>
        </>
      )}
    </main>
  );
}
