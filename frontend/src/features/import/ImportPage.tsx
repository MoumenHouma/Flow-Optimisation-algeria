import { type ChangeEvent, type DragEvent, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Upload, Download, FileWarning, CheckCircle2, Loader2 } from "lucide-react";

import { useCreateDeliveries } from "@/api/orders";
import { parseCsv } from "@/lib/csv";
import { buildTemplateCsv, mapRows, type ImportPreview } from "@/lib/delivery-import";

// CSV import — docs/DESIGN.md §3.5 (drag-drop, preview, validation, correction).
export function ImportPage() {
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [parseError, setParseError] = useState<string>("");
  const fileInput = useRef<HTMLInputElement>(null);
  const create = useCreateDeliveries();

  const handleFile = async (file: File) => {
    setParseError("");
    create.reset();
    if (!/\.(csv|txt)$/i.test(file.name)) {
      setParseError("Format non supporté. Exportez votre fichier Excel en CSV.");
      return;
    }
    try {
      const text = await file.text();
      const { rows } = parseCsv(text);
      setFileName(file.name);
      setPreview(mapRows(rows));
    } catch {
      setParseError("Impossible de lire le fichier.");
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  };

  const onSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void handleFile(file);
  };

  const downloadTemplate = () => {
    const url = URL.createObjectURL(new Blob([buildTemplateCsv()], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "modele-livraisons.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const geoSummary = useMemo(() => {
    const list = create.data?.deliveries ?? [];
    return {
      matched: list.filter((d) => d.geocoding_status === "matched").length,
      approximate: list.filter((d) => d.geocoding_status === "approximate").length,
      failed: list.filter((d) => d.geocoding_status === "failed").length,
    };
  }, [create.data]);

  return (
    <main className="mx-auto max-w-4xl p-6">
      <h1 className="text-2xl font-bold">Importer les livraisons</h1>

      {/* Dropzone */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        className="mt-6 rounded-lg border-2 border-dashed border-neutral-300 bg-white p-8 text-center"
      >
        <Upload className="mx-auto h-8 w-8 text-neutral-400" aria-hidden="true" />
        <p className="mt-2 text-sm text-neutral-600">Glissez votre fichier CSV ici</p>
        <button
          onClick={() => fileInput.current?.click()}
          className="mt-3 rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium hover:bg-neutral-50"
        >
          Parcourir
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".csv,text/csv"
          onChange={onSelect}
          className="hidden"
          aria-label="Choisir un fichier CSV"
        />
        <p className="mt-4 text-xs text-neutral-500">
          Colonnes: address, time_window_start, time_window_end, weight, volume, priority, phone
        </p>
        <button
          onClick={downloadTemplate}
          className="mt-2 inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          <Download className="h-4 w-4" aria-hidden="true" /> Télécharger le modèle
        </button>
      </div>

      {parseError && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-danger">
          {parseError}
        </p>
      )}

      {preview && !create.isSuccess && <PreviewTable preview={preview} fileName={fileName} />}

      {preview && !create.isSuccess && (
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={() => create.mutate(preview.valid)}
            disabled={preview.valid.length === 0 || create.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark disabled:opacity-50"
          >
            {create.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Importer {preview.valid.length} livraison{preview.valid.length > 1 ? "s" : ""}
          </button>
          {preview.invalid.length > 0 && (
            <span className="text-sm text-warning">
              {preview.invalid.length} ligne(s) à corriger seront ignorées
            </span>
          )}
        </div>
      )}

      {create.isError && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-danger">
          Échec de l'import. Réessayez.
        </p>
      )}

      {/* Success + geocoding breakdown */}
      {create.isSuccess && create.data && (
        <section className="mt-6 rounded-lg border border-green-200 bg-green-50 p-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-success">
            <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
            {create.data.created} livraisons importées
          </h2>
          <ul className="mt-2 space-y-1 text-sm text-neutral-700">
            <li>📍 {geoSummary.matched} géocodées précisément</li>
            {geoSummary.approximate > 0 && <li>≈ {geoSummary.approximate} approximatives</li>}
            {geoSummary.failed > 0 && (
              <li className="text-danger">⚠️ {geoSummary.failed} adresses non trouvées (à corriger)</li>
            )}
          </ul>
          <Link
            to="/optimize"
            className="mt-4 inline-block rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark"
          >
            Continuer vers l'optimisation →
          </Link>
        </section>
      )}
    </main>
  );
}

function PreviewTable({ preview, fileName }: { preview: ImportPreview; fileName: string }) {
  // Show up to 20 rows: valid ones first, then flagged ones for correction.
  const sample = [
    ...preview.valid.slice(0, 20).map((d, i) => ({ line: i + 2, draft: d, errors: [] as string[] })),
    ...preview.invalid.slice(0, 20).map((e) => ({ line: e.line, draft: null, errors: e.errors })),
  ].slice(0, 20);

  return (
    <div className="mt-6 rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-sm text-neutral-600">
        <span className="font-medium">{fileName}</span> — {preview.valid.length} valides,{" "}
        {preview.invalid.length} à corriger sur {preview.total}
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-neutral-500">
            <tr>
              <th className="p-2">Ligne</th>
              <th className="p-2">Adresse</th>
              <th className="p-2">Statut</th>
            </tr>
          </thead>
          <tbody>
            {sample.map((r) => (
              <tr key={r.line} className="border-t border-neutral-100">
                <td className="p-2 font-mono text-neutral-400">{r.line}</td>
                <td className="p-2">{r.draft?.address ?? <em className="text-neutral-400">—</em>}</td>
                <td className="p-2">
                  {r.errors.length === 0 ? (
                    <span className="text-success">✓ OK</span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-danger">
                      <FileWarning className="h-4 w-4" aria-hidden="true" />
                      {r.errors.join(", ")}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
