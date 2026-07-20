import "@testing-library/jest-dom";

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
