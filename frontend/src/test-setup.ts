import "@testing-library/jest-dom";

// Node 22+ ships a native experimental `localStorage` global that throws unless
// started with --localstorage-file; it shadows jsdom's working window.localStorage.
// Force an in-memory implementation so app code reading `localStorage` under test
// (api-client authHeader, auth store) works regardless of the Node version.
{
  const store = new Map<string, string>();
  const memoryStorage = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => void store.set(k, String(v)),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size;
    },
  };
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: memoryStorage,
  });
}

// jsdom's Blob/File lack .text(); polyfill via FileReader so app code using
// `file.text()` (ImportPage) works under test without changes.
if (typeof Blob !== "undefined" && typeof Blob.prototype.text !== "function") {
  Blob.prototype.text = function (this: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsText(this);
    });
  };
}

// jsdom has no object-URL support; the driver proof preview uses it.
if (typeof URL.createObjectURL !== "function") {
  URL.createObjectURL = () => "blob:mock";
  URL.revokeObjectURL = () => {};
}

// jsdom can't paint a canvas; the signature pad guards on a null context, so
// return null instead of letting jsdom log a noisy "not implemented" error.
if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = () => null;
}
