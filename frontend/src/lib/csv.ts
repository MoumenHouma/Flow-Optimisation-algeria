// Minimal RFC-4180-ish CSV parser (dependency-free). Handles quoted fields,
// escaped quotes ("") and quoted newlines. Headers are lower-cased + trimmed.

export interface ParsedCsv {
  headers: string[];
  rows: Record<string, string>[];
}

function parseRecords(text: string): string[][] {
  const s = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const records: string[][] = [];
  let field = "";
  let record: string[] = [];
  let inQuotes = false;

  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inQuotes) {
      if (c === '"') {
        if (s[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ",") {
      record.push(field);
      field = "";
    } else if (c === "\n") {
      record.push(field);
      records.push(record);
      record = [];
      field = "";
    } else {
      field += c;
    }
  }
  if (field !== "" || record.length > 0) {
    record.push(field);
    records.push(record);
  }
  return records;
}

export function parseCsv(text: string): ParsedCsv {
  const records = parseRecords(text);
  if (records.length === 0) return { headers: [], rows: [] };

  const headers = records[0].map((h) => h.trim().toLowerCase());
  const rows = records
    .slice(1)
    .filter((r) => r.some((cell) => cell.trim() !== "")) // drop blank lines
    .map((r) => {
      const obj: Record<string, string> = {};
      headers.forEach((h, i) => {
        obj[h] = (r[i] ?? "").trim();
      });
      return obj;
    });

  return { headers, rows };
}
