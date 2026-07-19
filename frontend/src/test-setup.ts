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
