import type { FieldResult } from "@/lib/types";

export type CropItem = {
  kind: "field" | "visual";
  sourceField: string;
  pageNumber?: number;
  revision: string;
  storageKey?: string;
  url?: string;
  available: boolean;
  observedPresent?: boolean | null;
  reviewStatus?: string;
  error?: string;
  imageSha256?: string;
  bboxArray?: number[];
};

export type UnifiedFieldRow = {
  field: string;
  label: string;
  value: unknown;
  isVisualOnly: boolean;
  result?: FieldResult;
  checkStatus: string;
  hasApprovedAlias: boolean;
  crops: CropItem[];
  errors: string[];
  needsAttention: boolean;
  isVisual: boolean;
};

export type FieldFilter = "all" | "with_crops" | "attention" | "visual";
