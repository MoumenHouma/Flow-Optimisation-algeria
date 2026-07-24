import { Camera, Loader2, X } from "lucide-react";
import { useRef, useState } from "react";

import { useUploadProof } from "@/api/driver";
import type { DriverStop } from "@/types";

import { SignaturePad, type SignaturePadHandle } from "./SignaturePad";

// Best-effort geolocation for the proof record; resolves to {} if unavailable.
function currentPosition(): Promise<{ lat?: number; lon?: number }> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({});
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => resolve({}),
      { timeout: 5000 },
    );
  });
}

// Capture proof of delivery (photo required + optional signature) before
// confirming a stop as delivered (F8, SCHEMA §5.3).
export function ProofSheet({
  stop,
  onCancel,
  onConfirmed,
}: {
  stop: DriverStop;
  onCancel: () => void;
  // F17: reports the cash collected when the stop is a COD delivery.
  onConfirmed: (cod?: { cod_collected: number }) => void;
}) {
  const upload = useUploadProof();
  const sigRef = useRef<SignaturePadHandle>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const isCod = stop.cod_amount != null;
  const [collected, setCollected] = useState<string>(
    stop.cod_amount != null ? String(stop.cod_amount) : "",
  );

  const onPickPhoto = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setPhoto(file);
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return file ? URL.createObjectURL(file) : null;
    });
  };

  const confirm = async () => {
    if (!photo) return;
    const pos = await currentPosition();
    const signature = (await sigRef.current?.toBlob()) ?? undefined;
    await upload.mutateAsync({
      deliveryId: stop.delivery_id,
      photo,
      signature,
      ...pos,
    });
    onConfirmed(isCod ? { cod_collected: Number(collected) || 0 } : undefined);
  };

  return (
    <div
      role="dialog"
      aria-label="Preuve de livraison"
      className="fixed inset-0 z-10 flex flex-col bg-white"
    >
      <header className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
        <h2 className="font-semibold">Preuve de livraison</h2>
        <button onClick={onCancel} aria-label="Annuler" className="p-1 text-neutral-500">
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <p className="text-sm text-neutral-500">📍 {stop.address}</p>

        {isCod && (
          <div className="rounded-lg border border-warning/40 bg-warning/10 p-3">
            <label htmlFor="cod-collected" className="text-sm font-medium text-neutral-700">
              💵 Encaissement (à collecter : {stop.cod_amount} {stop.cod_currency})
            </label>
            <input
              id="cod-collected"
              type="number"
              inputMode="decimal"
              min={0}
              value={collected}
              onChange={(e) => setCollected(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 font-mono text-lg"
            />
          </div>
        )}

        <div>
          <label
            htmlFor="pod-photo"
            className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-neutral-300 py-8 text-neutral-500"
          >
            {preview ? (
              <img src={preview} alt="Aperçu de la photo" className="max-h-48 rounded" />
            ) : (
              <>
                <Camera className="h-8 w-8" aria-hidden="true" />
                <span>Prendre une photo</span>
              </>
            )}
          </label>
          <input
            id="pod-photo"
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            onChange={onPickPhoto}
          />
        </div>

        <div>
          <p className="mb-1 text-sm font-medium text-neutral-700">Signature (facultatif)</p>
          <SignaturePad ref={sigRef} />
        </div>

        {upload.isError && (
          <p role="alert" className="text-sm text-danger">
            Échec de l'envoi. Vérifiez la connexion et réessayez.
          </p>
        )}
      </div>

      <footer className="border-t border-neutral-200 p-4">
        <button
          onClick={confirm}
          disabled={!photo || upload.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-success py-4 text-lg font-semibold text-white disabled:opacity-50"
        >
          {upload.isPending && <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />}
          Confirmer la livraison
        </button>
      </footer>
    </div>
  );
}
