import React, { useState } from "react";
import { Check, RotateCcw, FileText, Sparkles, Code } from "lucide-react";
import { Modal, ErrorNotice } from "@/components/ui";
import { display, formatAmount, formatCurrency, isAmountField } from "@/lib/formatters";
import { usePlatform, useData } from "@/components/platform-provider";
import { api } from "@/lib/api";
import type { Document, ConfigResponse, CaseSummary } from "@/lib/types";

export type Action = {
  kind: "classification" | "correction" | "move" | "reconcile";
  doc: Document;
  field?: string;
};

export function ActionModal({
  action,
  onClose,
  onComplete,
}: {
  action: Action;
  onClose: () => void;
  onComplete: () => Promise<void>;
}) {
  const { notify, devMode } = usePlatform(),
    { data: cases } = useData<{ items: CaseSummary[] }>("/cases?limit=100", 0);
  const { data: cfg } = useData<ConfigResponse>("/config", 0);
  const [reason, setReason] = useState(""),
    [type, setType] = useState(
      action.doc.doc_type === "unknown" ? "application" : action.doc.doc_type,
    ),
    [target, setTarget] = useState("");

  const findFieldValue = (dict?: Record<string, unknown> | null, targetField?: string): unknown => {
    if (!dict || !targetField) return undefined;
    if (targetField in dict) return dict[targetField];
    const lower = targetField.toLowerCase();
    for (const [k, v] of Object.entries(dict)) {
      if (k.toLowerCase() === lower) return v;
    }
    return undefined;
  };

  const originalFieldVal =
    findFieldValue(action.doc.overrides, action.field) ??
    findFieldValue(action.doc.normalized, action.field) ??
    findFieldValue(action.doc.raw, action.field) ??
    null;

  type PageInitialItem = {
    page_number: number;
    footer_present: boolean;
    evidence: string;
  };

  const isPageInitialsField =
    (action.field || "").toLowerCase().includes("page_initials") ||
    Boolean(
      originalFieldVal &&
        typeof originalFieldVal === "object" &&
        "pages" in (originalFieldVal as Record<string, unknown>),
    );

  const isSignatureOrStampField =
    !isPageInitialsField &&
    Boolean(
      (originalFieldVal &&
        typeof originalFieldVal === "object" &&
        ("present" in (originalFieldVal as Record<string, unknown>) ||
          "stamp_present" in (originalFieldVal as Record<string, unknown>))) ||
        (action.field || "").toLowerCase().includes("signature") ||
        (action.field || "").toLowerCase().includes("stamp"),
    );

  const getInitialPages = (): PageInitialItem[] => {
    if (
      originalFieldVal &&
      typeof originalFieldVal === "object" &&
      "pages" in (originalFieldVal as Record<string, unknown>)
    ) {
      const pages = (originalFieldVal as { pages: unknown[] }).pages;
      if (Array.isArray(pages) && pages.length) {
        return pages.map((p, idx) => {
          const item = (typeof p === "object" && p !== null ? p : {}) as Record<string, unknown>;
          return {
            page_number: typeof item.page_number === "number" ? item.page_number : idx + 1,
            footer_present: item.footer_present === true,
            evidence: typeof item.evidence === "string" ? item.evidence : "",
          };
        });
      }
    }
    return [
      { page_number: 1, footer_present: true, evidence: "" },
      { page_number: 2, footer_present: true, evidence: "" },
      { page_number: 3, footer_present: true, evidence: "" },
      { page_number: 4, footer_present: false, evidence: "Main signing block page" },
    ];
  };

  const getInitialSig = () => {
    const o = (originalFieldVal && typeof originalFieldVal === "object" ? originalFieldVal : {}) as Record<string, unknown>;
    return {
      present: o.present === true || o.stamp_present === true,
      complete: o.complete !== false,
      page_number: typeof o.page_number === "number" ? o.page_number : 1,
      signer_name: typeof o.name === "string" ? o.name : typeof o.text === "string" ? o.text : "",
      evidence: typeof o.evidence === "string" ? o.evidence : "",
    };
  };

  const [pageList, setPageList] = useState<PageInitialItem[]>(() => getInitialPages());
  const [sigData, setSigData] = useState(() => getInitialSig());

  const getInitialText = (val: unknown): string => {
    if (val === null || val === undefined) return "";
    const cleanStr = (s: unknown): string => {
      if (s === null || s === undefined) return "";
      return String(s).replace(/<br\s*\/?>/gi, " ").trim();
    };

    if (typeof val === "object") {
      if (Array.isArray(val)) {
        return val
          .map((item) => {
            if (item && typeof item === "object") {
              const rec = item as Record<string, unknown>;
              return cleanStr(
                rec.text ??
                rec.raw ??
                (typeof rec.complete === "string" ? rec.complete : undefined) ??
                rec.value ??
                rec.amount_raw ??
                rec.name ??
                rec.description ??
                Object.values(rec).filter((v) => typeof v === "string" || typeof v === "number").join(" ")
              );
            }
            return cleanStr(item);
          })
          .filter(Boolean)
          .join("\n");
      }
      const o = val as Record<string, unknown>;
      if (Array.isArray(o.items)) {
        return (o.items as unknown[])
          .map((item) => {
            if (item && typeof item === "object") {
              const rec = item as Record<string, unknown>;
              return cleanStr(
                rec.text ??
                rec.raw ??
                (typeof rec.complete === "string" ? rec.complete : undefined) ??
                rec.value ??
                rec.amount_raw ??
                rec.name ??
                rec.description ??
                Object.values(rec).filter((v) => typeof v === "string" || typeof v === "number").join(" ")
              );
            }
            return cleanStr(item);
          })
          .filter(Boolean)
          .join("\n");
      }
      if (isAmountField(o)) {
        return formatAmount(o);
      }
      if (o.raw !== undefined && o.raw !== null) return cleanStr(o.raw);
      if (o.selected !== undefined && o.selected !== null)
        return Array.isArray(o.selected) ? o.selected.join(", ") : cleanStr(o.selected);
      if (o.text !== undefined && o.text !== null) return cleanStr(o.text);
      if (o.complete !== undefined && o.complete !== null && typeof o.complete !== "boolean") return cleanStr(o.complete);
      if (o.name !== undefined && o.name !== null) return cleanStr(o.name);
      if (o.description !== undefined && o.description !== null) return cleanStr(o.description);
      if (o.value !== undefined && o.value !== null) return cleanStr(o.value);
      return "";
    }
    return cleanStr(val);
  };

  const getInitialCurrency = (val: unknown): string => {
    return formatCurrency(val);
  };

  const [textValue, setTextValue] = useState(() => getInitialText(originalFieldVal));
  const [currencyValue, setCurrencyValue] = useState(() => getInitialCurrency(originalFieldVal));
  const [isJsonMode, setIsJsonMode] = useState(false);
  const [rawJsonValue, setRawJsonValue] = useState(() => JSON.stringify(originalFieldVal, null, 2));

  const [providerId, setProviderId] = useState("");
  const [pending, setPending] = useState(false),
    [error, setError] = useState("");

  const title = {
    classification: "Confirm Document Type",
    correction: "Correct Field Value",
    move: "Move Document to Another Case",
    reconcile: "Reconcile External Submission",
  }[action.kind];

  return (
    <Modal title={title} onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setPending(true);
          setError("");
          try {
            const base = "/documents/" + action.doc.id;
            if (action.kind === "classification")
              await api(base + "/classification", {
                method: "POST",
                body: JSON.stringify({ doc_type: type, reason }),
              });
            if (action.kind === "correction") {
              let correctionPayload: unknown;
              if (isJsonMode) {
                correctionPayload = JSON.parse(rawJsonValue);
              } else if (isPageInitialsField) {
                correctionPayload = {
                  page_count: pageList.length,
                  pages: pageList.map((p) => ({
                    page_number: p.page_number,
                    footer_present: p.footer_present,
                    non_text: true,
                    complete: true,
                    evidence:
                      p.evidence ||
                      (p.footer_present ? "Initials verified by reviewer" : "No initials observed"),
                  })),
                };
              } else if (isSignatureOrStampField) {
                correctionPayload = {
                  present: sigData.present,
                  complete: sigData.complete,
                  page_number: Number(sigData.page_number) || 1,
                  non_text: true,
                  ...(sigData.signer_name ? { name: sigData.signer_name, text: sigData.signer_name } : {}),
                  evidence:
                    sigData.evidence ||
                    (sigData.present ? "Signature/stamp verified by reviewer" : "Absence verified"),
                };
              } else if (
                (action.field || "").toLowerCase() === "item_name" ||
                (originalFieldVal &&
                  typeof originalFieldVal === "object" &&
                  Array.isArray((originalFieldVal as Record<string, unknown>).items))
              ) {
                const origObj = (originalFieldVal && typeof originalFieldVal === "object" ? originalFieldVal : {}) as Record<string, unknown>;
                const origItems = Array.isArray(origObj.items) ? (origObj.items as unknown[]) : [];
                const lines = textValue.split("\n").map((l) => l.trim()).filter(Boolean);
                correctionPayload = {
                  ...origObj,
                  table_complete: true,
                  items: lines.map((line, idx) => {
                    const prev = (origItems[idx] || origItems[0] || {}) as Record<string, unknown>;
                    return {
                      ...prev,
                      row_id: prev.row_id ?? String(idx + 1),
                      raw: line,
                      complete: true,
                      text: line,
                    };
                  }),
                };
              } else if (Array.isArray(originalFieldVal)) {
                const lines = textValue.split("\n").map((l) => l.trim()).filter(Boolean);
                if (originalFieldVal.length > 0 && typeof originalFieldVal[0] === "object") {
                  correctionPayload = lines.map((line, idx) => {
                    const prev = (originalFieldVal[idx] || originalFieldVal[0] || {}) as Record<string, unknown>;
                    return {
                      ...prev,
                      row_id: String(idx + 1),
                      raw: line,
                      text: line,
                    };
                  });
                } else {
                  correctionPayload = lines;
                }
              } else {
                if (
                  originalFieldVal &&
                  typeof originalFieldVal === "object"
                ) {
                  const orig = { ...(originalFieldVal as Record<string, unknown>) };
                  if ("raw" in orig || "currency" in orig) {
                    orig.raw = textValue;
                    if (currencyValue.trim()) orig.currency = currencyValue.trim();
                    correctionPayload = orig;
                  } else if ("amount_raw" in orig || "currency_raw" in orig) {
                    orig.amount_raw = textValue;
                    if (currencyValue.trim()) orig.currency_raw = currencyValue.trim();
                    correctionPayload = orig;
                  } else if ("selected" in orig) {
                    orig.selected = textValue;
                    correctionPayload = orig;
                  } else {
                    orig.raw = textValue;
                    if (currencyValue.trim()) orig.currency = currencyValue.trim();
                    correctionPayload = orig;
                  }
                } else {
                  correctionPayload = textValue;
                }
              }
              await api(base + "/corrections", {
                method: "POST",
                body: JSON.stringify({
                  field: action.field || "",
                  value: correctionPayload,
                  reason,
                }),
              });
            }
            if (action.kind === "move")
              await api(base + "/move", {
                method: "POST",
                body: JSON.stringify({ case_id: target, reason }),
              });
            if (action.kind === "reconcile")
              await api(base + "/reconcile", {
                method: "POST",
                body: JSON.stringify({
                  stage: action.doc.provider_state?.pending_create,
                  provider_id: providerId,
                  reason,
                }),
              });
            notify("Action recorded in audit trail.");
            await onComplete();
          } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to process action.");
          } finally {
            setPending(false);
          }
        }}
      >
        <p className="muted">{action.doc.filename}</p>
        {error && <ErrorNotice message={error} />}
        {action.kind === "classification" && (
          <label>
            Verified Document Type
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {cfg &&
                Object.entries(cfg.payload.profiles).map(([profileId, p]) => (
                  <option value={profileId} key={profileId}>
                    {p.label}
                  </option>
                ))}
            </select>
          </label>
        )}
        {action.kind === "correction" && (
          <div className="correction-fields-group" style={{ marginBottom: 14 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#1e293b",
                  textTransform: "uppercase",
                }}
              >
                {action.field ? `${action.field.replaceAll("_", " ")} (${action.field})` : "Field"}
              </span>
              <button
                type="button"
                className="text-link"
                style={{ fontSize: "11px" }}
                onClick={() => setIsJsonMode((m) => !m)}
              >
                {isJsonMode ? "Switch to Form Mode" : "Switch to Raw JSON"}
              </button>
            </div>

            {isJsonMode ? (
              <label>
                Payload JSON
                <textarea
                  className="code-input"
                  rows={6}
                  value={rawJsonValue}
                  onChange={(e) => setRawJsonValue(e.target.value)}
                  required
                />
              </label>
            ) : isPageInitialsField ? (
              <div style={{ marginBottom: 12 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8,
                  }}
                >
                  <label style={{ margin: 0, fontWeight: 600, fontSize: "12px" }}>
                    RIPLAY Physical Page Verification ({pageList.length} Pages)
                  </label>
                  <button
                    type="button"
                    className="text-link"
                    style={{ fontSize: "11px" }}
                    onClick={() =>
                      setPageList((prev) => [
                        ...prev,
                        { page_number: prev.length + 1, footer_present: true, evidence: "" },
                      ])
                    }
                  >
                    + Add Page
                  </button>
                </div>
                <div className="grouped-pages-grid">
                  {pageList.map((p, idx) => (
                    <div key={p.page_number} className="page-group-card">
                      <span className="page-num-tag">Page {p.page_number}</span>
                      <select
                        value={p.footer_present ? "true" : "false"}
                        onChange={(e) => {
                          const nextPresent = e.target.value === "true";
                          setPageList((prev) =>
                            prev.map((item, i) =>
                              i === idx ? { ...item, footer_present: nextPresent } : item,
                            ),
                          );
                        }}
                      >
                        <option value="true">Present (Initials)</option>
                        <option value="false">Absent / Blank</option>
                      </select>
                      <input
                        type="text"
                        value={p.evidence}
                        onChange={(e) => {
                          const val = e.target.value;
                          setPageList((prev) =>
                            prev.map((item, i) =>
                              i === idx ? { ...item, evidence: val } : item,
                            ),
                          );
                        }}
                        placeholder="Evidence / notes (e.g. initials visible at bottom right)"
                      />
                    </div>
                  ))}
                </div>
                <p className="subtext" style={{ marginTop: 6 }}>
                  Review initials for each page. Verified values update the RIPLAY compliance audit trail automatically.
                </p>
              </div>
            ) : isSignatureOrStampField ? (
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                  <label>
                    Mark / Stamp Status
                    <select
                      value={sigData.present ? "true" : "false"}
                      onChange={(e) => setSigData({ ...sigData, present: e.target.value === "true" })}
                    >
                      <option value="true">Present (Mark Observed)</option>
                      <option value="false">Absent (Blank Area)</option>
                    </select>
                  </label>
                  <label>
                    Completeness
                    <select
                      value={sigData.complete ? "true" : "false"}
                      onChange={(e) => setSigData({ ...sigData, complete: e.target.value === "true" })}
                    >
                      <option value="true">Complete / Legible</option>
                      <option value="false">Incomplete / Cropped</option>
                    </select>
                  </label>
                  <label>
                    Physical Page #
                    <input
                      type="number"
                      min={1}
                      value={sigData.page_number}
                      onChange={(e) => setSigData({ ...sigData, page_number: Number(e.target.value) || 1 })}
                      required
                    />
                  </label>
                  <label>
                    Signer Name / Visible Text
                    <input
                      type="text"
                      value={sigData.signer_name}
                      onChange={(e) => setSigData({ ...sigData, signer_name: e.target.value })}
                      placeholder="e.g. Customer Name, Branch Stamp"
                    />
                  </label>
                </div>
                <label>
                  Evidence / Location Notes
                  <input
                    type="text"
                    value={sigData.evidence}
                    onChange={(e) => setSigData({ ...sigData, evidence: e.target.value })}
                    placeholder="e.g. Signature clearly visible in signing block"
                  />
                </label>
              </div>
            ) : (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      originalFieldVal &&
                      typeof originalFieldVal === "object" &&
                      ("currency" in originalFieldVal ||
                        "currency_raw" in originalFieldVal ||
                        (action.field || "").toLowerCase().includes("amount") ||
                        (action.field || "").toLowerCase().includes("total"))
                        ? "1fr 140px"
                        : "1fr",
                    gap: "12px",
                    marginBottom: "8px",
                  }}
                >
                  <label>
                    Target Value
                    {Array.isArray(originalFieldVal) ||
                    (originalFieldVal &&
                      typeof originalFieldVal === "object" &&
                      Array.isArray((originalFieldVal as Record<string, unknown>).items)) ||
                    textValue.includes("\n") ||
                    (action.field || "").toLowerCase() === "item_name" ? (
                      <textarea
                        rows={5}
                        className="code-input"
                        value={textValue}
                        onChange={(e) => setTextValue(e.target.value)}
                        placeholder="Enter item description(s), one per line…"
                        required
                      />
                    ) : (
                      <input
                        type="text"
                        value={textValue}
                        onChange={(e) => setTextValue(e.target.value)}
                        placeholder="Enter the correct value as visible on the document…"
                        required
                      />
                    )}
                  </label>
                  {originalFieldVal &&
                    typeof originalFieldVal === "object" &&
                    ("currency" in originalFieldVal ||
                      "currency_raw" in originalFieldVal ||
                      (action.field || "").toLowerCase().includes("amount") ||
                      (action.field || "").toLowerCase().includes("total")) && (
                      <label>
                        Currency
                        <input
                          type="text"
                          value={currencyValue}
                          onChange={(e) => setCurrencyValue(e.target.value.toUpperCase())}
                          placeholder="e.g. USD, CNY, IDR"
                        />
                      </label>
                    )}
                </div>
                <p className="subtext">
                  Correction is recorded in the audit trail. Original values remain preserved; SOP rules will be evaluated automatically.
                </p>
              </>
            )}
          </div>
        )}
        {action.kind === "move" && (
          <label>
            Select Target Case
            <select
              required
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">Select case…</option>
              {cases?.items
                .filter((c) => c.id !== action.doc.case_id)
                .map((c) => (
                  <option value={c.id} key={c.id}>
                    {c.reference} — {c.customer}
                  </option>
                ))}
            </select>
          </label>
        )}
        {action.kind === "reconcile" && (
          <>
            <p className="muted">
              Reconcile external provider submission.
            </p>
            <label>
              {String(action.doc.provider_state?.pending_create)}
              <input
                required
                value={providerId}
                onChange={(e) => setProviderId(e.target.value)}
              />
            </label>
          </>
        )}
        <label>
          Reason for this Action (Required for banking audit trail)
          <textarea
            required
            minLength={5}
            maxLength={1000}
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain the reason for this correction or cite visible document evidence…"
          />
        </label>
        <div className="modal-actions">
          <button className="secondary" type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending}>
            {pending ? "Saving…" : "Confirm Action"}
            <Check size={16} />
          </button>
        </div>
      </form>
    </Modal>
  );
}
