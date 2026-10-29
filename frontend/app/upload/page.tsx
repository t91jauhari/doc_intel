"use client";
import { useState, useRef, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import {
  UploadCloud,
  FileText,
  X,
  ArrowRight,
  ShieldCheck,
  FolderPlus,
  Info,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { useData, usePlatform } from "@/components/platform-provider";
import { api } from "@/lib/api";
import { Busy, ErrorNotice } from "@/components/ui";
import type { Branch, ConfigResponse, CaseDetail } from "@/lib/types";
import { familyCatalog } from "@/lib/document-family";
import {
  GroupingDialog,
  type GroupingRow as Preview,
} from "@/components/grouping-dialog";
function UploadForm() {
  const router = useRouter(),
    params = useSearchParams(),
    caseId = params.get("case") || "",
    attachBranch = params.get("branch") || "";
  const { startUpload, upload, user } = usePlatform();
  const { data: branches } = useData<Branch[]>("/branches", 0),
    { data: cfg } = useData<ConfigResponse>("/config", 0);
  const [attachedCase, setAttachedCase] = useState<CaseDetail | null>(null);
  const [files, setFiles] = useState<File[]>([]),
    [preview, setPreview] = useState<Preview[]>([]),
    [branch, setBranch] = useState(attachBranch),
    [template, setTemplate] = useState(params.get("template") || "");
  const [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [dragging, setDragging] = useState(false);
  const [groupingOpen, setGroupingOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"grouped" | "flat">("grouped");
  const [previewPending, setPreviewPending] = useState(false);
  const previewRequest = useRef(0);
  const input = useRef<HTMLInputElement>(null),
    key = useRef("");

  const templateOptions = useMemo(() => {
    if (!cfg?.payload.templates) return [];
    const catalog = familyCatalog(cfg.payload);
    return Object.entries(cfg.payload.templates)
      .filter(
        ([, t]) =>
          t.enabled !== false &&
          catalog[t.document_family || "forex"]?.enabled !== false,
      )
      .map(([id, t]) => ({
        id,
        label: t.label || id,
        description: t.description,
      }));
  }, [cfg]);
  const isAdmin =
    user?.role === "bank_admin" ||
    user?.role === "admin" ||
    user?.role === "superadmin";

  const canChangeBranch = isAdmin || (user?.branches && user.branches.length > 1);

  const displayedBranches = useMemo(() => {
    if (!branches?.length) return [];
    if (isAdmin || !user?.branches?.length) return branches;
    const filtered = branches.filter((b) => user.branches.includes(b.id));
    return filtered.length > 0 ? filtered : branches;
  }, [branches, isAdmin, user]);

  const userManuallyChangedBranch = useRef(false);

  useEffect(() => {
    if (caseId || attachBranch || userManuallyChangedBranch.current) return;
    if (user?.branches?.length && branches?.length) {
      const userBranchId =
        user.branches.find((ub) => branches.some((b) => b.id === ub)) ||
        user.branches[0];
      if (userBranchId && branch !== userBranchId) {
        setBranch(userBranchId);
      }
    } else if (!branch && branches?.length) {
      setBranch(branches[0].id);
    }
  }, [branches, user, branch, caseId, attachBranch]);
  useEffect(() => {
    // Only auto-pick when the flow is pinned by an existing case; free uploads
    // require an explicit choice through the confirmation dialog.
    if (caseId && !template && cfg) {
      const first = Object.entries(cfg.payload.templates).find(
        ([, f]) => f.enabled !== false,
      );
      if (first) setTemplate(first[0]);
    }
  }, [cfg, template, caseId]);
  useEffect(() => {
    if (!caseId) return;
    let active = true;
    api<CaseDetail>(`/cases/${caseId}`).then(value => {
      if (active) {
        setAttachedCase(value);
        setTemplate(value.template);
        if (value.branch_id) setBranch(value.branch_id);
      }
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : "Unable to load existing case"); });
    return () => { active = false; };
  }, [caseId]);
  const choose = async (next: File[]) => {
    setError("");
    const IMAGE_RE = /\.(pdf|png|jpe?g)$/i;
    const valid = next.filter((f) => IMAGE_RE.test(f.name));
    if (valid.length !== next.length) {
      setError("Only PDF, PNG or JPG files are supported.");
      return;
    }
    if (valid.length > 100 || valid.some((f) => f.size > 30 * 1024 * 1024)) {
      setError("Choose up to 100 files, each below 30 MB.");
      return;
    }
    if (new Set(valid.map((f) => f.name)).size !== valid.length) {
      setError("Filenames must be unique within an upload.");
      return;
    }
    const request = ++previewRequest.current;
    setPreviewPending(true);
    setGroupingOpen(false);
    setPreview([]);
    setFiles(valid);
    key.current = crypto.randomUUID();
    try {
      const next = await api<Preview[]>("/uploads/preview", {
        method: "POST",
        body: JSON.stringify({ filenames: valid.map((f) => f.name) }),
      });
      if (request !== previewRequest.current) return;
      // Guard against a partially-shaped response: never render `undefined`
      // into the customer label inputs.
      const normalized = next.map((p) => ({
        ...p,
        filename: p.filename ?? "",
        hint: p.hint ?? "",
        customer: p.customer ?? "",
        explanation: p.explanation ?? "",
        original_customer: p.original_customer ?? "",
        status: p.status ?? "unresolved",
        candidates: p.candidates ?? [],
      }));
      setPreview(normalized);
      if (!caseId && normalized.some((p) => p.status === "unresolved"))
        setGroupingOpen(true);
    } catch (e) {
      if (request === previewRequest.current)
        setError(e instanceof Error ? e.message : "Preview unavailable.");
    } finally {
      if (request === previewRequest.current) setPreviewPending(false);
    }
  };
  const submit = async () => {
    if (!files.length || pending || previewPending) return;
    if (!caseId && preview.some((p) => !(p.customer ?? "").trim())) {
      setGroupingOpen(true);
      return;
    }
    setPending(true);
    setError("");
    const form = new FormData();
    form.set("branch_id", branch);
    form.set("template", template);
    if (caseId) form.set("case_id", caseId);
    form.set(
      "grouping",
      JSON.stringify(
        Object.fromEntries(
          preview
            .filter((p) => p.status === "manual" && p.customer.trim())
            .map((p) => [p.filename, p.customer]),
        ),
      ),
    );
    files.forEach((f) => form.append("files", f));
    try {
      const result = await startUpload(form, key.current);
      router.push(
        result.case_ids.length === 1
          ? "/cases/" + result.case_ids[0]
          : "/cases",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setPending(false);
    }
  };
  const groups = new Set(
    preview.map((p) => p.customer.trim().toLowerCase()).filter(Boolean),
  ).size;
  return (
    <Shell
      title={caseId ? "Add Supplementary Documents" : "Bulk upload"}
      subtitle={
        caseId
          ? `Upload additional or missing mandatory documents for case ${attachedCase?.reference ? `"${attachedCase.reference}"` : ""} (${attachedCase?.customer || "Customer"}). All uploaded documents will be processed and verified as part of the existing case workflow.`
          : "Match customer names across the batch, review uncertain matches, then process."
      }
    >
      {groupingOpen && (
        <GroupingDialog
          rows={preview}
          files={files}
          onClose={() => setGroupingOpen(false)}
          onConfirm={(rows) => {
            setPreview(rows);
            setGroupingOpen(false);
            key.current = crypto.randomUUID();
          }}
        />
      )}
      {user?.role === "auditor" ? (
        <ErrorNotice message="Your role has read-only access." />
      ) : (
        <div className="upload-layout">
          <section className="panel upload-panel">
            {caseId && (
              <div
                style={{
                  padding: "16px 20px",
                  background: "#f0fdf4",
                  border: "1px solid #bbf7d0",
                  borderRadius: "10px",
                  marginBottom: "20px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    padding: "8px",
                    background: "#dcfce7",
                    borderRadius: "8px",
                    color: "#15803d",
                    flexShrink: 0,
                  }}
                >
                  <FolderPlus size={20} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "4px" }}>
                    <strong style={{ fontSize: "15px", color: "#166534" }}>
                      Upload Supplementary Documents for Existing Case
                    </strong>
                    {attachedCase && (
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          background: "#ffffff",
                          color: "#166534",
                          padding: "2px 8px",
                          borderRadius: "12px",
                          border: "1px solid #bbf7d0",
                        }}
                      >
                        Case: {attachedCase.reference}
                      </span>
                    )}
                  </div>
                  <p style={{ margin: "0 0 8px", fontSize: "13px", color: "#374151", lineHeight: 1.5 }}>
                    This page is used to upload documents to a specific ongoing case (<strong>{attachedCase?.customer || "Current Customer"}</strong>). Use this when the case requires another mandatory document, or when you need to attach missing documents required by the SOP compliance workflow.
                  </p>
                  <div style={{ display: "flex", gap: "16px", fontSize: "12px", color: "#4b5563", flexWrap: "wrap" }}>
                    <span>✓ Documents are automatically linked to this case package</span>
                    <span>✓ SOP compliance checks rerun automatically after extraction</span>
                  </div>
                </div>
              </div>
            )}
            <div className="section-head">
              <div>
                <h2>
                  {caseId
                    ? "Upload Missing or Supplementary Documents"
                    : "A batch, one upload"}
                </h2>
                <p>
                  {caseId
                    ? "Select and upload the missing mandatory documents required to complete this customer case."
                    : "Processing continues when you leave this screen."}
                </p>
              </div>
              <span className="small-label">PDF · UP TO 30 MB EACH</span>
            </div>
            <div className="form-row">
              <label>
                Branch
                <select
                  value={branch}
                  disabled={!canChangeBranch || !!caseId || pending}
                  onChange={(e) => {
                    userManuallyChangedBranch.current = true;
                    setBranch(e.target.value);
                  }}
                  title={!canChangeBranch ? "Branch is assigned based on your user profile" : undefined}
                >
                  {displayedBranches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Transaction Flow Type
                {caseId && attachedCase ? (
                  <select value={template} disabled>
                    <option value={attachedCase.template}>
                      {attachedCase.transaction_flow_label ||
                        attachedCase.template}{" "}
                      · pinned configuration
                    </option>
                  </select>
                ) : (
                  <select
                    value={template}
                    disabled={pending}
                    onChange={(e) => {
                      setTemplate(e.target.value);
                      key.current = crypto.randomUUID();
                    }}
                  >
                    <option value="">Select Transaction Flow Type…</option>
                    {templateOptions.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                )}
              </label>
            </div>
            {template && cfg?.payload.templates[template]?.description && (
              <div className="info-note" style={{ margin: "10px 25px 0" }}>
                {cfg.payload.templates[template].description}
              </div>
            )}
            <div
              className={"dropzone " + (dragging ? "dragging" : "")}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                if (!pending) void choose(Array.from(e.dataTransfer.files));
              }}
            >
              <div className="drop-icon">
                <UploadCloud size={29} />
              </div>
              <h3>{caseId ? "Drop supplementary documents here" : "Drop customer documents here"}</h3>
              <p>{caseId ? "Select additional files for this case from your computer" : "Or choose a batch from your computer"}</p>
              <button
                className="secondary"
                disabled={pending}
                onClick={() => input.current?.click()}
              >
                {caseId ? "Browse supplementary files" : "Browse files"}
              </button>
              <input
                ref={input}
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                hidden
                onChange={(e) => void choose(Array.from(e.target.files || []))}
              />
            </div>
            {previewPending && <p>Matching customer names across the batch…</p>}
            {!!preview.length && !caseId && (
              <button
                className="secondary"
                disabled={pending || previewPending}
                onClick={() => setGroupingOpen(true)}
              >
                Review grouping
                {preview.some((p) => !(p.customer ?? "").trim())
                  ? " · unresolved documents"
                  : ""}
              </button>
            )}
            {error && <ErrorNotice message={error} />}
            {!!preview.length && (
              <>
                <div className="preview-summary">
                  <div>
                    <strong>{files.length} documents</strong>{" "}
                    <span>
                      {"· "}
                      {caseId ? "Existing case" : groups + " customer groups"} {"· "}
                      labels are editable before upload
                    </span>
                  </div>
                  {!caseId && (
                    <div className="field-filter-pills">
                      <button
                        type="button"
                        className={viewMode === "grouped" ? "active" : ""}
                        onClick={() => setViewMode("grouped")}
                      >
                        Customer packages <span>{groups}</span>
                      </button>
                      <button
                        type="button"
                        className={viewMode === "flat" ? "active" : ""}
                        onClick={() => setViewMode("flat")}
                      >
                        Flat file list <span>{files.length}</span>
                      </button>
                    </div>
                  )}
                </div>
                {viewMode === "grouped" && !caseId && (
                  <div className="upload-package-grid">
                    {Array.from(
                      preview.reduce((acc, row) => {
                        const key = row.customer.trim() || "Unassigned customer";
                        const list = acc.get(key) || [];
                        list.push(row);
                        acc.set(key, list);
                        return acc;
                      }, new Map<string, Preview[]>()),
                    ).map(([custName, custRows]) => (
                      <div key={custName} className="upload-package-card">
                        <div className="upload-package-head">
                          <strong>{custName}</strong>
                          <span className="count-pill">
                            {custRows.length} file{custRows.length === 1 ? "" : "s"}
                          </span>
                        </div>
                        <ul className="upload-package-files">
                          {custRows.map((r) => (
                            <li key={r.filename}>
                              <FileText size={13} />
                              <span>{r.filename}</span>
                              <small>{r.hint.replaceAll("_", " ")}</small>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Document</th>
                        <th>Customer label</th>
                        <th>Filename hint</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {preview.map((p, i) => (
                        <tr key={p.filename}>
                          <td>
                            <span className="file-cell">
                              <FileText size={17} />
                              {p.filename}
                            </span>
                          </td>
                          <td>
                            <input
                              aria-label={"Customer for " + p.filename}
                              value={p.customer}
                              disabled={pending || !!caseId}
                              onChange={(e) =>
                                setPreview((previous) =>
                                  previous.map((x, j) =>
                                    i === j
                                      ? {
                                          ...x,
                                          customer: e.target.value,
                                          status: "manual",
                                        }
                                      : x,
                                  ),
                                )
                              }
                            />
                          </td>
                          <td className="muted">
                            {p.hint.replaceAll("_", " ")}
                          </td>
                          <td>
                            <button
                              className="icon-button"
                              disabled={pending}
                              aria-label={"Remove " + p.filename}
                              onClick={() => {
                                void choose(
                                  files.filter((f) => f.name !== p.filename),
                                );
                                key.current = crypto.randomUUID();
                              }}
                            >
                              <X size={16} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            <div className="upload-actions">
              <span>
                {pending
                  ? "Upload " + (upload?.progress || 0) + "%"
                  : !template && files.length
                    ? "Select a Transaction Flow Type above to proceed."
                    : caseId
                      ? "Uploaded files will be directly attached to this case package."
                      : "Classification verifies the schema after grouping."}
              </span>
              <button
                className="primary"
                disabled={
                  pending ||
                  previewPending ||
                  !files.length ||
                  !branch ||
                  !template ||
                  preview.length !== files.length ||
                  (!caseId && preview.some((p) => !p.customer.trim()))
                }
                onClick={() => void submit()}
              >
                {pending
                  ? "Uploading…"
                  : caseId
                    ? "Upload & Attach to Case"
                    : "Upload & start processing"}
                <ArrowRight size={17} />
              </button>
            </div>
          </section>
          <aside className="panel guidance">
            <div className="guidance-icon">
              <ShieldCheck size={23} />
            </div>
            {caseId ? (
              <>
                <h3>Supplementary Intake</h3>
                <p>
                  Documents uploaded here will be attached directly to customer case <strong>{attachedCase?.reference || caseId}</strong> ({attachedCase?.customer || "Customer"}).
                </p>
                <div style={{ marginTop: "14px", fontSize: "13px", color: "var(--text-muted)" }}>
                  <p style={{ margin: "0 0 8px", fontWeight: 600, color: "var(--text)" }}>
                    When to use this page:
                  </p>
                  <ul style={{ paddingLeft: "18px", margin: "0 0 12px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <li>To fulfill missing mandatory documents required by SOP.</li>
                    <li>To provide supplementary customer identity (e-KTP) or transaction slips.</li>
                    <li>To replace unreadable or incomplete document scans.</li>
                  </ul>
                  <p style={{ margin: 0 }}>
                    Once uploaded, the platform extracts fields and recalculates SOP compliance automatically.
                  </p>
                </div>
              </>
            ) : (
              <>
                <h3>Names bring the case together.</h3>
                <p>
                  Full names and unambiguous initials are matched automatically.
                  Review uncertain assignments before processing.
                </p>
                <div className="filename-example">
                  customer_transaction.pdf
                  <br />
                  customer_lld.pdf
                  <br />
                  customer_invoice.pdf
                </div>
                <ol>
                  <li>
                    <strong>Group first</strong>
                    <span>
                      Same customer label, selected branch and upload batch.
                    </span>
                  </li>
                  <li>
                    <strong>Classify next</strong>
                    <span>The configured provider verifies the document type.</span>
                  </li>
                  <li>
                    <strong>Extract and check</strong>
                    <span>
                      The matching schema and SOP rules run automatically.
                    </span>
                  </li>
                </ol>
                <p className="subtext">
                  Later uploads create new cases unless explicitly attached to an
                  existing case ID.
                </p>
              </>
            )}
            {cfg?.payload.provider === "fixture" && (
              <p className="fixture-note">
                Fixture mode is enabled. Outputs contain synthetic test values.
              </p>
            )}
          </aside>
        </div>
      )}
    </Shell>
  );
}
export default function UploadPage() {
  return (
    <Suspense fallback={<Busy />}>
      <UploadForm />
    </Suspense>
  );
}
