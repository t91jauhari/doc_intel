import type { CropItem } from "./evidence-types";

export function extractBboxArray(b: unknown): number[] | undefined {
  if (!b || typeof b !== "object") return undefined;
  const o = b as Record<string, unknown>;
  const arr = (o.bbox || o.box_2d || o.box || o) as unknown;
  if (Array.isArray(arr) && arr.length >= 4 && arr.every((x) => typeof x === "number")) {
    return arr as number[];
  }
  return undefined;
}

export function areCropsDuplicate(
  existing: CropItem,
  candidate: {
    url?: string;
    storageKey?: string;
    imageSha256?: string;
    pageNumber?: number;
    bboxArray?: number[];
  },
): boolean {
  if (existing.url && candidate.url && existing.url === candidate.url) return true;
  if (existing.storageKey && candidate.storageKey && existing.storageKey === candidate.storageKey) return true;
  if (existing.imageSha256 && candidate.imageSha256 && existing.imageSha256 === candidate.imageSha256) return true;
  if (
    existing.pageNumber !== undefined &&
    candidate.pageNumber !== undefined &&
    existing.pageNumber === candidate.pageNumber
  ) {
    if (
      existing.bboxArray &&
      candidate.bboxArray &&
      existing.bboxArray.length >= 4 &&
      candidate.bboxArray.length >= 4
    ) {
      const b1 = existing.bboxArray.map((v) => (v > 1 ? v / 1000 : v));
      const b2 = candidate.bboxArray.map((v) => (v > 1 ? v / 1000 : v));
      const diff = Math.max(
        Math.abs(b1[0] - b2[0]),
        Math.abs(b1[1] - b2[1]),
        Math.abs(b1[2] - b2[2]),
        Math.abs(b1[3] - b2[3]),
      );
      if (diff < 0.05) return true;
    }
  }
  return false;
}

export function buildCropUrl(
  docId: string,
  revision: string,
  storageKey?: string,
): string | undefined {
  if (!storageKey || !revision) return undefined;
  const filename = storageKey.split("/").pop();
  if (!filename || filename.length <= revision.length + 5) return undefined;
  const token = filename.slice(revision.length + 1, -4);
  if (!token) return undefined;
  return `/api/documents/${docId}/evidence/${revision}/${token}`;
}

export function baseFieldKey(path: string): string {
  return path.split(".")[0] || path;
}

export function formatFieldKeyLabel(key: string): string {
  return key
    .replaceAll(".", " · ")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
