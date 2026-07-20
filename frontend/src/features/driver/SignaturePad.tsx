import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

export interface SignaturePadHandle {
  toBlob: () => Promise<Blob | null>;
  clear: () => void;
  isEmpty: () => boolean;
}

// A finger/stylus signature canvas for proof of delivery (F8, DESIGN §3.4).
export const SignaturePad = forwardRef<SignaturePadHandle>(function SignaturePad(_props, ref) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const dirty = useRef(false);
  const [hasInk, setHasInk] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // Match the backing store to the displayed size for crisp strokes.
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width || 320;
    canvas.height = rect.height || 140;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.lineWidth = 2.5;
      ctx.lineCap = "round";
      ctx.strokeStyle = "#111827";
    }
  }, []);

  const pos = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const start = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    drawing.current = true;
    const { x, y } = pos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const move = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const { x, y } = pos(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    if (!dirty.current) {
      dirty.current = true;
      setHasInk(true);
    }
  };

  const end = () => {
    drawing.current = false;
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    dirty.current = false;
    setHasInk(false);
  };

  useImperativeHandle(ref, () => ({
    isEmpty: () => !dirty.current,
    clear: clearCanvas,
    toBlob: () =>
      new Promise((resolve) => {
        const canvas = canvasRef.current;
        if (!canvas || !dirty.current || !canvas.toBlob) return resolve(null);
        canvas.toBlob((b) => resolve(b), "image/png");
      }),
  }));

  return (
    <div>
      <canvas
        ref={canvasRef}
        aria-label="Signature du client"
        className="h-36 w-full touch-none rounded-lg border border-neutral-300 bg-white"
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerLeave={end}
      />
      {hasInk && (
        <button
          type="button"
          onClick={clearCanvas}
          className="mt-1 text-sm text-neutral-500 underline"
        >
          Effacer
        </button>
      )}
    </div>
  );
});
