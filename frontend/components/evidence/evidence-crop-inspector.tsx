"use client";
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Layers,
  Pencil,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { Badge } from "@/components/ui";
import { formatAmount, display, isAmountField } from "@/lib/formatters";
import { VisualRegionEditor } from "@/components/visual-region-editor";
import { areCropsDuplicate } from "./evidence-bbox-utils";
import type { UnifiedFieldRow } from "./evidence-types";
import type { Document } from "@/lib/types";

export interface EvidenceCropInspectorProps {
  activeRow: UnifiedFieldRow;
  activeIndex: number;
  totalFiltered: number;
  doc: Document;
  canReview: boolean;
  devMode: boolean;
  inspectorZoom: number;
  onZoomChange: (newZoom: number) => void;
  onStep: (delta: number) => void;
  onCorrectField: (field: string) => void;
  onRegionSaved?: () => void;
}

export function EvidenceCropInspector({
  activeRow,
  activeIndex,
  totalFiltered,
  doc,
  canReview,
  devMode,
  inspectorZoom,
  onZoomChange,
  onStep,
  onCorrectField,
  onRegionSaved,
}: EvidenceCropInspectorProps) {
  const formatFieldValue = (_field: string, val: unknown) => {
    if (isAmountField(val)) {
      return formatAmount(val);
    }
    return display(val);
  };

  const availableCrops = activeRow.crops.filter((c) => c.url);

  return (
    <aside
      className="field-inspector-pane"
      aria-label="Selected field evidence inspector"
    >
      <div className="inspector-head">
        <div>
          <span className="eyebrow">DOCUMENT SOURCE EVIDENCE</span>
          <h3 style={{ whiteSpace: "pre-line" }}>{activeRow.label}</h3>
          <span className="field-key-code">{activeRow.field}</span>
        </div>
        <div className="inspector-nav">
          <button
            type="button"
            className="icon-button"
            disabled={activeIndex <= 0}
            onClick={() => onStep(-1)}
            title="Previous field"
            aria-label="Previous field"
          >
            <ChevronUp size={16} />
          </button>
          <span className="inspector-counter">
            {activeIndex >= 0 ? activeIndex + 1 : 1} / {totalFiltered}
          </span>
          <button
            type="button"
            className="icon-button"
            disabled={activeIndex < 0 || activeIndex >= totalFiltered - 1}
            onClick={() => onStep(1)}
            title="Next field"
            aria-label="Next field"
          >
            <ChevronDown size={16} />
          </button>
        </div>
      </div>

      <div className="inspector-value-box">
        <div className="inspector-value-header">
          <span className="small-label">NILAI TERBACA EFEKTIF</span>
          {activeRow.checkStatus === "OK" ? (
            <span className="badge good">OK</span>
          ) : (
            <Badge value={activeRow.checkStatus} />
          )}
        </div>
        <div className="inspector-effective-val">
          {formatFieldValue(activeRow.field, activeRow.value)}
        </div>
        <div className="inspector-actions-bar">
          {canReview &&
            !activeRow.isVisualOnly &&
            doc.status === "COMPLETED" && (
              <button
                type="button"
                className="secondary compact-btn"
                onClick={() => onCorrectField(activeRow.field)}
              >
                <Pencil size={13} />
                Correct value
              </button>
            )}
          {canReview && (
            <VisualRegionEditor
              documentId={doc.id}
              field={activeRow.field}
              onSaved={onRegionSaved || (() => {})}
            />
          )}
        </div>
      </div>

      <div className="inspector-crops-section">
        <div className="inspector-crops-head">
          <span className="small-label">
            VISUAL EVIDENCE CROPS ({availableCrops.length})
          </span>
          {availableCrops.length > 0 && (
            <div className="inspector-zoom-bar">
              <button
                type="button"
                className="icon-button"
                disabled={inspectorZoom <= 75}
                onClick={() => onZoomChange(Math.max(75, inspectorZoom - 25))}
                title="Zoom out crop"
                aria-label="Zoom out crop"
              >
                <ZoomOut size={14} />
              </button>
              <span>{inspectorZoom}%</span>
              <button
                type="button"
                className="icon-button"
                disabled={inspectorZoom >= 200}
                onClick={() => onZoomChange(Math.min(200, inspectorZoom + 25))}
                title="Zoom in crop"
                aria-label="Zoom in crop"
              >
                <ZoomIn size={14} />
              </button>
            </div>
          )}
        </div>

        {availableCrops.length > 0 ? (
          <div className="inspector-crop-list">
            {activeRow.crops
              .filter((c) => c.url)
              .filter(
                (c, idx, arr) =>
                  arr.findIndex((other) => areCropsDuplicate(other, c)) === idx,
              )
              .map((crop, idx) => (
                <div
                  key={crop.storageKey || idx}
                  className="inspector-crop-card"
                >
                  <div className="inspector-crop-viewport">
                    <img
                      alt={`${activeRow.label}, page ${crop.pageNumber || 1}`}
                      style={{
                        width:
                          inspectorZoom === 100
                            ? "auto"
                            : `${inspectorZoom}%`,
                        maxWidth: inspectorZoom === 100 ? "100%" : "none",
                      }}
                      src={crop.url}
                    />
                  </div>
                  <div className="inspector-crop-foot">
                    <div>
                      <strong>
                        {crop.pageNumber
                          ? `Source page ${crop.pageNumber}`
                          : "Source crop"}
                      </strong>
                      {crop.sourceField !== activeRow.field && (
                        <span className="crop-subpath">
                          {" · "}
                          {crop.sourceField}
                        </span>
                      )}
                      {crop.kind === "visual" && (
                        <span className="crop-subpath">
                          {" · Observed: "}
                          {crop.observedPresent === null ||
                          crop.observedPresent === undefined
                            ? "uncertain"
                            : String(crop.observedPresent)}
                        </span>
                      )}
                    </div>
                    <a
                      className="text-link"
                      href={
                        crop.pageNumber
                          ? `/api/documents/${doc.id}/pages/${crop.pageNumber}`
                          : `/api/documents/${doc.id}/file`
                      }
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open page
                      <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div className="inspector-no-crop">
            <Layers size={20} />
            <p>
              {activeRow.errors[0] ||
                "No bounding-box crop is stored for this field yet."}
            </p>
            <span>
              Use <strong>Select evidence region</strong> above to mark the
              location on the document page, or open the full PDF.
            </span>
          </div>
        )}
      </div>

      {devMode && (
        <details className="inspector-raw-details">
          <summary>Raw, override & validation metadata</summary>
          <pre>
            {JSON.stringify(
              {
                raw: doc.raw?.[activeRow.field],
                override: doc.overrides?.[activeRow.field],
                evidence: activeRow.result?.metadata,
                issues: activeRow.result?.issues,
              },
              null,
              2,
            )}
          </pre>
        </details>
      )}
    </aside>
  );
}
