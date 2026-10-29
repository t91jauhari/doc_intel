"use client";
import { useEffect, useMemo, useState } from "react";
import {
  Image as ImageIcon,
  Maximize2,
  Minimize2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { usePlatform } from "@/components/platform-provider";
import { extractionCheck } from "@/lib/extraction-export";
import {
  extractBboxArray,
  areCropsDuplicate,
  buildCropUrl,
  formatFieldKeyLabel,
} from "@/components/evidence/evidence-bbox-utils";
import { EvidenceTable } from "@/components/evidence/evidence-table";
import { EvidenceCropInspector } from "@/components/evidence/evidence-crop-inspector";
import type {
  CropItem,
  UnifiedFieldRow,
  FieldFilter,
} from "@/components/evidence/evidence-types";
import type { Configuration, Document } from "@/lib/types";

export function FieldEvidenceWorkspace({
  doc,
  columns,
  provider,
  canWrite,
  canReview,
  pending,
  onRefreshCrops,
  onCorrectField,
  onRegionSaved,
}: {
  doc: Document;
  columns?: [string, string][];
  provider?: Configuration["provider"];
  canWrite: boolean;
  canReview: boolean;
  pending?: boolean;
  onRefreshCrops?: () => void;
  onCorrectField: (field: string) => void;
  onRegionSaved?: () => void;
}) {
  const [filter, setFilter] = useState<FieldFilter>("all");
  const [selectedField, setSelectedField] = useState<string>("");
  const [showInspector, setShowInspector] = useState<boolean>(false);
  const [inspectorZoom, setInspectorZoom] = useState<number>(100);
  const [showDevKeys, setShowDevKeys] = useState<boolean>(false);
  const { devMode } = usePlatform();

  const rows = useMemo<UnifiedFieldRow[]>(() => {
    const labelMap = new Map<string, string>(columns || []);
    const normalizedEntries = Object.entries(doc.normalized || {});
    const fieldEvidenceList = doc.validation?.field_evidence || [];
    const visualEvidenceList = (doc.raw?.visual_evidence as unknown[]) || [];

    const cropsByField = new Map<string, CropItem[]>();
    const errorsByField = new Map<string, string[]>();
    const extraVisualFields = new Set<string>();
    const knownFields = new Set<string>([
      ...(columns || []).map(([k]) => k),
      ...normalizedEntries.map(([k]) => k),
    ]);

    const resolveTargetField = (src: string) => {
      const topKey = src.split(".")[0];
      if (knownFields.has(topKey)) return topKey;
      return src;
    };

    for (const fe of fieldEvidenceList) {
      if (
        fe.field.endsWith(".complete") ||
        fe.field.endsWith(".options_complete")
      ) {
        continue;
      }
      const target = resolveTargetField(fe.field);
      if (!knownFields.has(target)) {
        extraVisualFields.add(target);
      }
      const list = cropsByField.get(target) || [];
      for (const cRaw of fe.crops || []) {
        const c = cRaw as Record<string, unknown>;
        const revision = String(c.revision || "");
        const storageKey = c.storage_key ? String(c.storage_key) : undefined;
        const url = buildCropUrl(doc.id, revision, storageKey);
        const bboxArray = extractBboxArray(c.bbox);
        const imageSha256 = c.image_sha256 ? String(c.image_sha256) : undefined;
        const pageNumber = typeof c.page_number === "number" ? c.page_number : undefined;
        const candidate = {
          url,
          storageKey,
          imageSha256,
          pageNumber,
          bboxArray,
        };
        if (
          url &&
          !list.some((existing) => areCropsDuplicate(existing, candidate))
        ) {
          list.push({
            kind: "field",
            sourceField: fe.field,
            pageNumber,
            revision,
            storageKey,
            url,
            available: true,
            reviewStatus: fe.review_status,
            imageSha256,
            bboxArray,
          });
        }
      }
      cropsByField.set(target, list);
      if (fe.error) {
        const errs = errorsByField.get(target) || [];
        if (!errs.includes(fe.error)) errs.push(fe.error);
        errorsByField.set(target, errs);
      }
    }

    for (const veRaw of visualEvidenceList) {
      const ve = veRaw as Record<string, unknown>;
      const field = String(ve.field || "");
      const target = resolveTargetField(field);
      if (!knownFields.has(target)) {
        extraVisualFields.add(target);
      }
      const list = cropsByField.get(target) || [];
      const revision = String(ve.revision || "");
      const storageKey = ve.storage_key ? String(ve.storage_key) : undefined;
      const url = ve.available && storageKey
        ? buildCropUrl(doc.id, revision, storageKey)
        : undefined;
      const bboxArray = extractBboxArray(ve.bbox);
      const imageSha256 = ve.image_sha256 ? String(ve.image_sha256) : undefined;
      const pageNumber = typeof ve.page_number === "number" ? ve.page_number : undefined;
      const candidate = {
        url,
        storageKey,
        imageSha256,
        pageNumber,
        bboxArray,
      };
      if (
        !list.some((existing) => areCropsDuplicate(existing, candidate))
      ) {
        list.push({
          kind: "visual",
          sourceField: field,
          pageNumber,
          revision,
          storageKey,
          url,
          available: !!(ve.available && url),
          observedPresent: ve.observed_present === true ? true : ve.observed_present === false ? false : null,
          reviewStatus: typeof ve.review_status === "string" ? ve.review_status : undefined,
          error: typeof ve.error === "string" ? ve.error : undefined,
          imageSha256,
          bboxArray,
        });
      }
      cropsByField.set(target, list);
      if (ve.error) {
        const errs = errorsByField.get(target) || [];
        const errStr = String(ve.error);
        if (!errs.includes(errStr)) errs.push(errStr);
        errorsByField.set(target, errs);
      }
    }

    const buildRow = (
      field: string,
      value: unknown,
      isVisualOnly: boolean,
    ): UnifiedFieldRow => {
      const result = doc.validation?.fields?.[field];
      const label = labelMap.get(field) || formatFieldKeyLabel(field);
      const crops = cropsByField.get(field) || [];
      const errors = errorsByField.get(field) || [];
      const checkStatus = isVisualOnly
        ? crops.some((c) => c.observedPresent === false)
          ? "REVIEW"
          : crops.some((c) => c.observedPresent === true)
            ? "VALID"
            : "PENDING"
        : extractionCheck(doc, field, provider) === "OK"
          ? "OK"
          : result?.status || "PENDING";

      const hasApprovedAlias = !!doc.validation?.corrections?.some(
        (c) =>
          typeof c === "object" &&
          c !== null &&
          (c as { field?: string; method?: string }).field === field &&
          (c as { method?: string }).method === "approved_enum_alias",
      );

      const isVisual =
        isVisualOnly ||
        crops.some((c) => c.kind === "visual") ||
        /signature|stamp|paraf|initial|photo|meterai|approval/i.test(field);

      const needsAttention =
        Boolean(result?.issues?.length) ||
        ["INVALID", "FAIL", "REVIEW", "ERROR"].includes(checkStatus) ||
        errors.length > 0 ||
        crops.some((c) => c.kind === "visual" && c.observedPresent === false);

      return {
        field,
        label,
        value,
        isVisualOnly,
        result,
        checkStatus,
        hasApprovedAlias,
        crops,
        errors,
        needsAttention,
        isVisual,
      };
    };

    const definedKeys = new Set((columns || []).map(([k]) => k));
    const hasAmountRaw = (v: unknown): boolean => {
      if (!v || typeof v !== "object") return false;
      if (Array.isArray(v)) {
        return v.some(
          (item) =>
            item &&
            typeof item === "object" &&
            (item as Record<string, unknown>).amount_raw != null &&
            (item as Record<string, unknown>).amount_raw !== "",
        );
      }
      const rec = v as Record<string, unknown>;
      return rec.amount_raw != null && rec.amount_raw !== "";
    };

    const rowsFromColumns = (columns || []).map(([colKey]) => {
      let rawVal =
        doc.overrides?.[colKey] ??
        (hasAmountRaw(doc.raw?.[colKey])
          ? doc.raw?.[colKey]
          : (doc.normalized?.[colKey] ?? doc.raw?.[colKey] ?? null));
      if (
        (rawVal == null ||
          (typeof rawVal === "object" &&
            (rawVal as Record<string, unknown>).amount_raw == null &&
            (rawVal as Record<string, unknown>).amount == null)) &&
        colKey === "subtotal_all_items"
      ) {
        rawVal =
          doc.overrides?.subtotal ??
          (hasAmountRaw(doc.raw?.subtotal)
            ? doc.raw?.subtotal
            : (doc.normalized?.subtotal ?? doc.raw?.subtotal ?? null));
      }
      return buildRow(colKey, rawVal, false);
    });

    const extraNormalizedRows = normalizedEntries
      .filter(([field]) => !definedKeys.has(field))
      .map(([field, value]) => buildRow(field, value, false));

    const extraVisualRows: UnifiedFieldRow[] = [];
    for (const extraField of extraVisualFields) {
      if (definedKeys.has(extraField) || knownFields.has(extraField)) continue;
      const extraCrops = cropsByField.get(extraField) || [];
      const observedSummary = extraCrops
        .filter((c) => c.kind === "visual")
        .map((c) =>
          c.observedPresent === true
            ? "Present"
            : c.observedPresent === false
              ? "Absent"
              : "Uncertain",
        );
      extraVisualRows.push(
        buildRow(
          extraField,
          observedSummary.length ? observedSummary.join(", ") : null,
          true,
        ),
      );
    }

    return columns && columns.length > 0
      ? [...rowsFromColumns, ...extraNormalizedRows, ...extraVisualRows]
      : [...normalizedEntries.map(([f, v]) => buildRow(f, v, false)), ...extraVisualRows];
  }, [columns, doc, provider]);

  const counts = useMemo(() => {
    return {
      all: rows.length,
      with_crops: rows.filter((r) => r.crops.some((c) => c.url)).length,
      attention: rows.filter((r) => r.needsAttention).length,
      visual: rows.filter((r) => r.isVisual).length,
    };
  }, [rows]);

  const filteredRows = useMemo(() => {
    if (filter === "with_crops") {
      return rows.filter((r) => r.crops.some((c) => c.url));
    }
    if (filter === "attention") {
      return rows.filter((r) => r.needsAttention);
    }
    if (filter === "visual") {
      return rows.filter((r) => r.isVisual);
    }
    return rows;
  }, [filter, rows]);

  // Keep selectedField valid when switching documents or filters
  useEffect(() => {
    if (!rows.length) {
      setSelectedField("");
      return;
    }
    if (selectedField && rows.some((r) => r.field === selectedField)) {
      return;
    }
    const firstWithCropOrIssue =
      rows.find((r) => r.needsAttention && r.crops.some((c) => c.url)) ||
      rows.find((r) => r.crops.some((c) => c.url)) ||
      rows.find((r) => r.needsAttention) ||
      rows[0];
    setSelectedField(firstWithCropOrIssue?.field || "");
  }, [doc.id, rows, selectedField]);

  const activeRow =
    rows.find((r) => r.field === selectedField) ||
    filteredRows[0] ||
    rows[0] ||
    null;

  const activeIndex = activeRow
    ? filteredRows.findIndex((r) => r.field === activeRow.field)
    : -1;

  const stepSelection = (delta: number) => {
    if (!filteredRows.length) return;
    const nextIndex = Math.max(
      0,
      Math.min(
        filteredRows.length - 1,
        (activeIndex >= 0 ? activeIndex : 0) + delta,
      ),
    );
    setSelectedField(filteredRows[nextIndex].field);
  };

  return (
    <div className="field-evidence-workspace">
      <div className="field-evidence-toolbar">
        <div className="field-filter-pills" role="tablist" aria-label="Filter extracted fields">
          <button
            type="button"
            className={filter === "all" ? "active" : ""}
            onClick={() => setFilter("all")}
          >
            All fields <span>{counts.all}</span>
          </button>
          <button
            type="button"
            className={filter === "with_crops" ? "active" : ""}
            onClick={() => setFilter("with_crops")}
          >
            <ImageIcon size={13} />
            With crops <span>{counts.with_crops}</span>
          </button>
          <button
            type="button"
            className={filter === "visual" ? "active" : ""}
            onClick={() => setFilter("visual")}
          >
            <Sparkles size={13} />
            Visual & signatures <span>{counts.visual}</span>
          </button>
          <button
            type="button"
            className={filter === "attention" ? "active" : ""}
            onClick={() => setFilter("attention")}
          >
            Needs attention <span>{counts.attention}</span>
          </button>
        </div>
        <div className="field-toolbar-actions">
          {canWrite && doc.status === "COMPLETED" && (
            <button
              type="button"
              className="secondary compact-btn"
              disabled={pending}
              onClick={onRefreshCrops}
              title="Regenerate or refresh field & visual evidence crops from saved coordinates"
            >
              <RefreshCw size={14} />
              Refresh field crops
            </button>
          )}
          <button
            type="button"
            className="secondary compact-btn"
            onClick={() => setShowInspector((v) => !v)}
            title={
              showInspector
                ? "Hide side-by-side detail inspector"
                : "Show side-by-side detail inspector"
            }
          >
            {showInspector ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            {showInspector ? "Hide inspector" : "Show inspector"}
          </button>
          {devMode && (
            <button
              type="button"
              className="dev-keys-toggle-btn"
              onClick={() => setShowDevKeys((v) => !v)}
              title="Toggle database schema field names"
            >
              {showDevKeys ? "Hide Technical Keys" : "Technical Keys"}
            </button>
          )}
        </div>
      </div>

      <div
        className={
          "field-evidence-split " + (showInspector ? "with-inspector" : "full")
        }
      >
        <EvidenceTable
          filteredRows={filteredRows}
          activeField={activeRow?.field || ""}
          showInspector={showInspector}
          doc={doc}
          totalAllCount={counts.all}
          canReview={canReview}
          onSelectField={setSelectedField}
          onOpenInspector={() => setShowInspector(true)}
          onFilterReset={() => setFilter("all")}
          onCorrectField={onCorrectField}
          onRegionSaved={onRegionSaved}
        />

        {showInspector && activeRow && (
          <EvidenceCropInspector
            activeRow={activeRow}
            activeIndex={activeIndex}
            totalFiltered={filteredRows.length}
            doc={doc}
            canReview={canReview}
            devMode={devMode}
            inspectorZoom={inspectorZoom}
            onZoomChange={setInspectorZoom}
            onStep={stepSelection}
            onCorrectField={onCorrectField}
            onRegionSaved={onRegionSaved}
          />
        )}
      </div>
    </div>
  );
}
