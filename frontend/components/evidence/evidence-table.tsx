"use client";
import { Eye, Pencil } from "lucide-react";
import { Badge } from "@/components/ui";
import { formatAmount, display, isAmountField } from "@/lib/formatters";
import { VisualRegionEditor } from "@/components/visual-region-editor";
import type { UnifiedFieldRow } from "./evidence-types";
import type { Document } from "@/lib/types";

export interface EvidenceTableProps {
  filteredRows: UnifiedFieldRow[];
  activeField: string;
  showInspector: boolean;
  doc: Document;
  totalAllCount: number;
  canReview: boolean;
  onSelectField: (field: string) => void;
  onOpenInspector: () => void;
  onFilterReset: () => void;
  onCorrectField: (field: string) => void;
  onRegionSaved?: () => void;
}

export function EvidenceTable({
  filteredRows,
  activeField,
  showInspector,
  doc,
  totalAllCount,
  canReview,
  onSelectField,
  onOpenInspector,
  onFilterReset,
  onCorrectField,
  onRegionSaved,
}: EvidenceTableProps) {
  const formatFieldValue = (_field: string, val: unknown) => {
    if (isAmountField(val)) {
      return formatAmount(val);
    }
    return display(val);
  };

  return (
    <div className="table-scroll fields-table side-by-side-table">
      <table>
        <thead>
          <tr>
            <th>Document Field</th>
            <th>Extracted Value</th>
            <th>Visual Evidence</th>
            <th>Status & Actions</th>
          </tr>
        </thead>
        <tbody>
          {filteredRows.length === 0 ? (
            <tr>
              <td colSpan={4} className="empty-filter-row">
                No fields match the selected filter.{" "}
                <button
                  type="button"
                  className="text-link"
                  onClick={onFilterReset}
                >
                  Show all {totalAllCount} fields
                </button>
              </td>
            </tr>
          ) : (
            filteredRows.map((row) => {
              const isSelected = activeField === row.field;
              const availableCrops = row.crops
                .filter((c) => c.url)
                .filter(
                  (c, idx, arr) =>
                    arr.findIndex(
                      (other) =>
                        (c.storageKey && other.storageKey === c.storageKey) ||
                        (c.url && other.url === c.url),
                    ) === idx,
                );
              const isOverridden =
                doc.overrides &&
                Object.prototype.hasOwnProperty.call(
                  doc.overrides,
                  row.field,
                ) &&
                doc.overrides[row.field] !== undefined;

              return (
                <tr
                  key={row.field}
                  className={isSelected ? "selected-field-row" : ""}
                  onClick={() => onSelectField(row.field)}
                >
                  <td className="field-name-cell">
                    <div className="field-label-wrap">
                      <strong style={{ whiteSpace: "pre-line" }}>{row.label}</strong>
                      <span className="field-key-code">{row.field}</span>
                    </div>
                    <div className="field-tags-row">
                      {row.isVisual && (
                        <span className="mini-tag visual">Visual</span>
                      )}
                      {isOverridden && (
                        <span className="mini-tag override">Overridden</span>
                      )}
                    </div>
                  </td>

                  <td className="field-value">
                    {row.value == null &&
                    row.result?.issues.some((i) =>
                      [
                        "UNRECOGNIZED_ENUM",
                        "INVALID_OR_MISSING_ENUM",
                      ].includes(i.code),
                    ) ? (
                      <span className="enum-warning-text">
                        Unrecognized value · needs review
                      </span>
                    ) : (
                      <span className="effective-value-text">
                        {formatFieldValue(row.field, row.value)}
                      </span>
                    )}
                    {row.field !== "page_initials" &&
                      row.crops
                        .filter((c) => c.kind === "visual")
                        .map((c, idx) => (
                          <div key={idx} className="visual-observed-line">
                            Observed:{" "}
                            <strong>
                              {c.observedPresent === null ||
                              c.observedPresent === undefined
                                ? "uncertain"
                                : c.observedPresent
                                  ? "present"
                                  : "absent"}
                            </strong>
                            {c.pageNumber ? ` (P${c.pageNumber})` : ""}
                          </div>
                        ))}
                  </td>

                  <td className="field-crop-cell">
                    {availableCrops.length > 0 ? (
                      <div className="inline-crop-strip">
                        {availableCrops.map((crop, idx) => (
                          <div
                            key={`${crop.storageKey || idx}`}
                            className="inline-crop-card"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectField(row.field);
                              if (!showInspector) onOpenInspector();
                            }}
                          >
                            <div className="inline-crop-img-wrap">
                              <img
                                loading="lazy"
                                alt={`${row.label}${
                                  crop.pageNumber
                                    ? `, page ${crop.pageNumber}`
                                    : ""
                                }`}
                                src={crop.url}
                              />
                            </div>
                            <div className="inline-crop-meta">
                              <span>
                                {crop.pageNumber
                                  ? `Page ${crop.pageNumber}`
                                  : "Crop"}
                              </span>
                              {crop.sourceField !== row.field && (
                                <span className="crop-subpath">
                                  {crop.sourceField.replace(
                                    row.field + ".",
                                    "",
                                  )}
                                </span>
                              )}
                              <Eye size={12} />
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="inline-crop-empty">
                        <span>
                          {row.errors[0] || "No crop image available"}
                        </span>
                        {canReview && (
                          <span
                            className="inline-region-trigger"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <VisualRegionEditor
                              documentId={doc.id}
                              field={row.field}
                              onSaved={onRegionSaved || (() => {})}
                            />
                          </span>
                        )}
                      </div>
                    )}
                  </td>

                  <td className="field-check-cell">
                    <div className="check-action-top">
                      {row.checkStatus === "OK" ? (
                        <span
                          className="badge good"
                          title="Spider-AI extraction result. Native document validation was skipped."
                        >
                          OK
                        </span>
                      ) : row.checkStatus === "SKIPPED" ? null : (
                        <Badge value={row.checkStatus} />
                      )}
                      {canReview &&
                        !row.isVisualOnly &&
                        doc.status === "COMPLETED" && (
                          <button
                            type="button"
                            className="icon-button"
                            aria-label={"Correct " + row.label}
                            title={"Correct " + row.label}
                            onClick={(e) => {
                              e.stopPropagation();
                              onCorrectField(row.field);
                            }}
                          >
                            <Pencil size={14} />
                          </button>
                        )}
                    </div>
                    {row.hasApprovedAlias && (
                      <div className="field-issue">
                        Normalized using approved alias
                      </div>
                    )}
                    {row.result?.issues.slice(0, 2).map((i) => (
                      <div key={i.code} className="field-issue">
                        {i.code.replaceAll("_", " ").toLowerCase()}
                      </div>
                    ))}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
