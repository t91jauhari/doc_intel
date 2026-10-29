"use client";
import { CaseConfiguration } from "@/components/case-configuration";
import { FieldEvidenceWorkspace } from "@/components/field-evidence-workspace";
import { FieldReprocess } from "@/components/field-reprocess";
import { FieldRequestRecovery } from "@/components/field-request-recovery";
import { BatchGroupingRepair } from "@/components/batch-grouping-repair";
import { EnumRevalidation } from "@/components/enum-revalidation";
import { CaseTask } from "@/components/case-task";
import { SpiderResubmit } from "@/components/spider-resubmit";
import { CopyExtraction } from "@/components/copy-extraction";
import { VisualRegionEditor } from "@/components/visual-region-editor";
import { use, useState, useCallback, useEffect } from "react";
import Link from "next/link";
import {
  GitBranch,
  Upload,
  FileText,
  RotateCcw,
  Check,
  Download,
  ExternalLink,
  Pencil,
  MoveRight,
  ChevronDown,
  Clock3,
  ShieldCheck,
  Wrench,
  Scale,
  FileCheck2,
  FolderOpen,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  Layers,
  WandSparkles,
  FileSpreadsheet,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { useData, usePlatform } from "@/components/platform-provider";
import {
  Badge,
  Busy,
  ErrorNotice,
  Empty,
  Modal,
  display,
  formatDate,
} from "@/components/ui";
import { StatusBadge, SopBadge } from "@/components/status";
import { CaseSOP } from "@/components/case-sop";
import { api } from "@/lib/api";
import type {
  CaseDetail,
  Document,
  ConfigResponse,
  CaseSummary,
  Branch,
} from "@/lib/types";

import {
  INVOICE_1_COLUMNS,
  INVOICE_2_COLUMNS,
  detectInvoiceProfile,
  cleanDocDisplayFilename,
} from "@/components/case/case-profile-detector";
import { ActionModal, type Action } from "@/components/case/case-action-modal";
import { CaseSopFindings, type FindingFilter } from "@/components/case/case-sop-findings";

export default function CasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params),
    { data, error, loading, refresh } = useData<CaseDetail>("/cases/" + id),
    { notify, user, devMode } = usePlatform();
  const { data: cfg } = useData<ConfigResponse>("/config", 0);
  const { data: branches } = useData<Branch[]>("/branches", 0);

  const [activeMode, setActiveMode] = useState<"documents" | "sop" | "reports">("documents");
  const [selected, setSelected] = useState("");
  const [showReprocess, setShowReprocess] = useState(false);
  const [findingFilter, setFindingFilter] = useState<FindingFilter>("all");
  const [action, setAction] = useState<Action | null>(null);
  const [pending, setPending] = useState(false);
  const branchName = data?.branch_name || branches?.find((b) => b.id === data?.branch_id)?.name || data?.branch_id || "-";

  const close = useCallback(() => setAction(null), []);

  useEffect(() => {
    if (!selected && data && window.location.hash === "#recovery") {
      const failed = data.documents.find((d) => d.error);
      if (failed) setSelected(failed.id);
    }
  }, [data, selected]);

  const doc =
    data?.documents.find((d) => d.id === selected) || data?.documents[0];
  const report = data?.reports[0];

  const getDocProfileInfo = useCallback(
    (docItem?: Document | null) => {
      if (!docItem) return { label: "", columns: undefined as [string, string][] | undefined };
      const dt = docItem.doc_type;
      if (dt === "invoice" || dt === "invoice_1" || dt === "invoice_2") {
        const isInvoice2 =
          dt === "invoice_2" ||
          (dt === "invoice" && detectInvoiceProfile(docItem, cfg));
        const profKey = isInvoice2 ? "invoice_2" : "invoice_1";
        const invoiceProfiles = cfg?.payload.invoice_profiles || cfg?.payload.profiles;
        const prof = invoiceProfiles?.[profKey];
        return {
          label: prof?.label || (isInvoice2 ? "Underlying Invoice 2" : "Underlying Invoice 1"),
          columns:
            (prof?.columns as [string, string][] | undefined) ||
            (isInvoice2 ? INVOICE_2_COLUMNS : INVOICE_1_COLUMNS),
        };
      }
      const prof = cfg?.payload.profiles[dt as keyof typeof cfg.payload.profiles];
      return {
        label: prof?.label || dt,
        columns: prof?.columns as [string, string][] | undefined,
      };
    },
    [cfg],
  );

  const failedDocs =
    data?.documents.filter(
      (d) =>
        d.status === "ERROR" ||
        d.status === "FAILED" ||
        d.status === "NEEDS_CLASSIFICATION",
    ) || [];

  const retryableDocs =
    data?.documents.filter((d) => !d.provider_state?.pending_create) || [];

  const run = async (fn: () => Promise<unknown>, success: string) => {
    setPending(true);
    try {
      await fn();
      notify(success);
      await refresh();
    } catch (err) {
      notify(err instanceof Error ? err.message : "Action failed.", "error");
    } finally {
      setPending(false);
    }
  };

  return (
    <Shell
      title={data?.customer ? `${data.customer}` : "Kasus Nasabah"}
      subtitle={data?.reference ? `Referensi: ${data.reference}` : "Memuat detail kasus..."}
      hideHero={true}
    >
      {error && <ErrorNotice message={error} retry={() => void refresh()} />}
      {loading && !data ? (
        <Busy label="Loading customer case file…" />
      ) : (
        data && (
          <div className="case-page-container">
            {/* Breadcrumb Navigation */}
            <nav className="case-breadcrumb-bar" aria-label="Breadcrumb">
              <Link href="/" className="bc-link">Dashboard</Link>
              <span className="bc-sep">/</span>
              <Link href="/cases" className="bc-link">Customer Cases</Link>
              <span className="bc-sep">/</span>
              <span className="bc-current">{data.customer} ({data.reference})</span>
            </nav>

            {/* Executive Case Summary Card */}
            <header className="case-executive-header">
              <div className="exec-header-top">
                <div className="exec-customer-info">
                  <div className="exec-avatar">{data.customer.charAt(0).toUpperCase()}</div>
                  <div className="exec-customer-text">
                    <h1>{data.customer}</h1>
                    <div className="exec-badges-row">
                      <span className="pill-ref">REF: {data.reference}</span>
                      <span className="pill-branch">Branch: {branchName}</span>
                      <StatusBadge value={data.status} />
                      <SopBadge value={data.validation_status} />
                    </div>
                  </div>
                </div>

                <div className="exec-actions">
                  {report ? (
                    <a
                      className="btn-download-kertas-kerja"
                      href={`/api/reports/${report.id}/download?format=xlsx`}
                      title="Download Official Kertas Kerja in Excel format (.xlsx)"
                    >
                      <FileSpreadsheet size={16} />
                      <span>Download Excel Kertas Kerja</span>
                      <span className="btn-version-pill">v{report.version}</span>
                    </a>
                  ) : (
                    <div
                      className="btn-download-kertas-kerja disabled"
                      title="Kertas Kerja report will be available once SOP evaluation finishes"
                    >
                      <FileSpreadsheet size={16} />
                      <span>Download Excel Kertas Kerja</span>
                      <span className="btn-version-pill">Pending</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Integrated 4-Step Workflow Pipeline */}
              <div className="exec-stepper-wrap">
                <div className="pipeline-steps">
                  {/* Step 1: Document Intake */}
                  <div
                    role="button"
                    tabIndex={0}
                    className={`pipeline-step clickable ${data.documents_count > 0 ? "step-done" : "step-pending"}`}
                    onClick={() => setActiveMode("documents")}
                    title="View Document Package & Extractions"
                  >
                    <div className="step-indicator">1</div>
                    <div className="step-content">
                      <div className="step-name">1. Document Intake</div>
                      <div className="step-desc">
                        {data.documents_count > 0 ? `${data.documents_count} files uploaded` : "Waiting for files"}
                      </div>
                    </div>
                  </div>
                  <div className="pipeline-connector" />

                  {/* Step 2: AI Extraction */}
                  <div
                    role="button"
                    tabIndex={0}
                    className={`pipeline-step clickable ${
                    data.completed_count === data.documents_count && data.documents_count > 0
                      ? "step-done"
                      : data.documents.some((d) => ["RUNNING", "PROCESSING", "QUEUED"].includes(d.status))
                        ? "step-active"
                        : data.documents.some((d) => ["ERROR", "PROCESSING_ERROR"].includes(d.status))
                          ? "step-attention"
                          : "step-pending"
                  }`}
                    onClick={() => setActiveMode("documents")}
                    title="View Extracted Fields & Evidence"
                  >
                    <div className="step-indicator">2</div>
                    <div className="step-content">
                      <div className="step-name">2. AI Extraction</div>
                      <div className="step-desc">
                        {data.documents.some((d) => ["RUNNING", "PROCESSING", "QUEUED"].includes(d.status))
                          ? `Processing (${data.completed_count}/${data.documents_count})`
                          : data.documents.some((d) => ["ERROR", "PROCESSING_ERROR"].includes(d.status))
                            ? `Needs Attention (${data.documents.filter((d) => ["ERROR", "PROCESSING_ERROR"].includes(d.status)).length} failed)`
                            : `${data.completed_count}/${data.documents_count} completed`}
                      </div>
                    </div>
                  </div>
                  <div className="pipeline-connector" />

                  {/* Step 3: SOP Compliance */}
                  <div
                    role="button"
                    tabIndex={0}
                    className={`pipeline-step clickable ${
                    data.status === "SOP_ERROR"
                      ? "step-attention"
                      : ["PASS", "COMPLIANT"].includes(data.validation_status)
                        ? "step-done"
                        : ["REVIEW", "FAIL"].includes(data.validation_status)
                          ? "step-review"
                          : "step-pending"
                  }`}
                    onClick={() => setActiveMode("sop")}
                    title="Inspect SOP Compliance Rule Results"
                  >
                    <div className="step-indicator">3</div>
                    <div className="step-content">
                      <div className="step-name">3. SOP Compliance</div>
                      <div className="step-desc">
                        {data.status === "SOP_ERROR"
                          ? "Evaluation interrupted"
                          : ["PASS", "COMPLIANT"].includes(data.validation_status)
                            ? "All rules compliant"
                            : ["REVIEW", "FAIL"].includes(data.validation_status)
                              ? "Findings need review"
                              : "Waiting for extraction"}
                      </div>
                    </div>
                  </div>
                  <div className="pipeline-connector" />

                  {/* Step 4: Work Paper */}
                  <div
                    role="button"
                    tabIndex={0}
                    className={`pipeline-step clickable ${
                    report?.state === "FINAL"
                      ? "step-done"
                      : report
                        ? "step-ready"
                        : "step-pending"
                  }`}
                    onClick={() => {
                      if (report) {
                        window.location.href = `/api/reports/${report.id}/download?format=xlsx`;
                      } else {
                        setActiveMode("reports");
                      }
                    }}
                    title={report ? "Download Official Work Paper Excel" : "Audit Trail & History"}
                  >
                    <div className="step-indicator">4</div>
                    <div className="step-content">
                      <div className="step-name">4. Work Paper</div>
                      <div className="step-desc">
                        {report?.state === "FINAL"
                          ? `Finalized v${report.version}`
                          : report
                            ? `Draft ready v${report.version}`
                            : "Waiting for SOP"}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </header>

            {/* SOP Interrupted Alert Banner */}
            {data.status === "SOP_ERROR" && (
              <div
                className="fixture-banner"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 16,
                  background: "rgba(220, 38, 38, 0.08)",
                  borderColor: "rgba(220, 38, 38, 0.3)",
                  color: "inherit",
                  marginTop: -6,
                  marginBottom: 16,
                }}
              >
                <div>
                  <strong style={{ color: "var(--color-danger, #dc2626)" }}>
                    SOP Compliance Evaluation Interrupted
                  </strong>
                  <div style={{ fontSize: "13px", opacity: 0.85, marginTop: 2 }}>
                    SOP evaluation encountered a network interruption. All extracted document data remains intact and safely preserved. Click to rerun.
                  </div>
                </div>
                {data.can_write && (
                  <button
                    className="primary"
                    disabled={pending}
                    style={{ whiteSpace: "nowrap" }}
                    onClick={async () => {
                      setPending(true);
                      try {
                        await api("/cases/" + id + "/sop-rerun", { method: "POST" });
                        notify("SOP evaluation rerun using stored document extractions.");
                        await refresh();
                      } catch (e) {
                        notify(e instanceof Error ? e.message : "Rerun failed.", "error");
                      } finally {
                        setPending(false);
                      }
                    }}
                  >
                    <RotateCcw size={15} />
                    Rerun SOP Compliance
                  </button>
                )}
              </div>
            )}

            {/* Missing documents callout */}
            {report?.snapshot.missing.length ? (
              <div className="missing-strip" style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Clock3 size={16} style={{ color: "#d97706", flexShrink: 0 }} />
                  <strong>Waiting for Prerequisite Documents:</strong>
                  <span>
                    {report.snapshot.missing
                      .map(
                        (x) =>
                          cfg?.payload.profiles[x as keyof typeof cfg.payload.profiles]?.label || x,
                      )
                      .join(", ")}
                  </span>
                </div>
              </div>
            ) : null}

            {/* 3-Mode Primary Navigation Tabs */}
            <nav className="workspace-mode-tabs" aria-label="Case workspace modes">
              <button
                type="button"
                className={`mode-tab-btn ${activeMode === "documents" ? "active" : ""}`}
                onClick={() => setActiveMode("documents")}
              >
                <FileText size={17} />
                <span>Documents & Extracted Data</span>
                <span className="mode-tab-count">
                  {data.completed_count}/{data.documents_count}
                </span>
              </button>

              <button
                type="button"
                className={`mode-tab-btn ${activeMode === "sop" ? "active" : ""}`}
                onClick={() => setActiveMode("sop")}
              >
                <Scale size={17} />
                <span>SOP Compliance Checks</span>
                <span
                  className={`mini-status-dot ${
                    data.status === "SOP_ERROR"
                      ? "error"
                      : ["REVIEW", "FAIL"].includes(data.validation_status)
                        ? "warn"
                        : "good"
                  }`}
                  title={data.validation_status}
                />
              </button>

              <button
                type="button"
                className={`mode-tab-btn ${activeMode === "reports" ? "active" : ""}`}
                onClick={() => setActiveMode("reports")}
              >
                <Clock3 size={17} />
                <span>Audit Trail & History</span>
                <span className="mode-tab-count">{data.timeline.length}</span>
              </button>
            </nav>

            {/* MODE 1: DOCUMENTS & EXTRACTED DATA */}
            {activeMode === "documents" && (
              <div className="mode-view-documents">
                {/* Document Package Selector Panel - No Horizontal Scrolling! */}
                <div className="doc-package-panel">
                  <div className="doc-package-header">
                    <div className="doc-package-title">
                      <Layers size={16} style={{ color: "#0d9488" }} />
                      <strong>Customer Document Package ({data.documents_count})</strong>
                      <span className="doc-package-subtext">
                        Select a document to inspect fields, review visual crops, or reprocess.
                      </span>
                    </div>

                    <div className="doc-package-actions">
                      {data.can_write && failedDocs.length > 0 && (
                        <button
                          className="primary compact-btn"
                          disabled={pending}
                          onClick={async () => {
                            setPending(true);
                            try {
                              const res = await api<{
                                queued: unknown[];
                                skipped: { reason: string }[];
                              }>("/cases/" + id + "/retry-documents", { method: "POST" });
                              notify(
                                res.queued.length
                                  ? `Reprocessing ${res.queued.length} failed document(s).`
                                  : "No documents required retry.",
                              );
                              await refresh();
                            } catch (e) {
                              notify(e instanceof Error ? e.message : "Retry failed.", "error");
                            } finally {
                              setPending(false);
                            }
                          }}
                        >
                          <RotateCcw size={14} />
                          Retry Failed ({failedDocs.length})
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Responsive Document Cards Grid - Clean, Spacious, No Scrollbar! */}
                  <div className="doc-package-grid">
                    {data.documents.map((d) => {
                      const profileLabel = getDocProfileInfo(d).label;
                      const isSelected = doc?.id === d.id;
                      const cleanFilename = cleanDocDisplayFilename(d.filename, data?.customer);
                      return (
                        <button
                          key={d.id}
                          type="button"
                          className={`doc-card-btn ${isSelected ? "selected" : ""}`}
                          onClick={() => {
                            setSelected(d.id);
                            setShowReprocess(false);
                          }}
                        >
                          <div className="doc-card-icon-wrap">
                            <FileText size={18} />
                          </div>
                          <div className="doc-card-body">
                            <strong className="doc-card-filename" title={profileLabel}>
                              {profileLabel}
                            </strong>
                            <span className="doc-card-profile" title={d.filename}>
                              {cleanFilename}
                            </span>
                          </div>
                          <div className="doc-card-badge-wrap">
                            <Badge value={d.status} />
                          </div>
                        </button>
                      );
                    })}

                    {/* Missing prerequisite document placeholders */}
                    {report?.snapshot.missing.map((missingType) => {
                      const profileLabel =
                        cfg?.payload.profiles[missingType as keyof typeof cfg.payload.profiles]?.label || missingType;
                      return (
                        <div
                          key={missingType}
                          className="doc-card-missing"
                          title="Prerequisite document pending intake"
                        >
                          <div className="doc-card-icon-wrap missing">
                            <Clock3 size={18} />
                          </div>
                          <div className="doc-card-body">
                            <strong className="doc-card-filename" style={{ color: "#92400e" }}>
                              Missing Document
                            </strong>
                            <span className="doc-card-profile" style={{ color: "#78350f" }}>
                              {profileLabel}
                            </span>
                          </div>
                          <div className="doc-card-badge-wrap">
                            <span className="pill-missing">Pending</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Document Inspection Content */}
                {doc ? (
                  <section
                    className="panel evidence-panel"
                    style={{
                      padding: 0,
                      overflow: "visible",
                      background: "#ffffff",
                      border: "1px solid #f1f5f9",
                      borderRadius: "10px",
                      boxShadow: "0 1px 2px 0 rgba(15, 23, 42, 0.02)",
                    }}
                  >
                    <div
                      className="section-head"
                      style={{
                        padding: "16px 20px",
                        borderBottom: "1px solid #f1f5f9",
                        margin: 0,
                        background: "#ffffff",
                      }}
                    >
                      <div>
                        {(() => {
                          const currentProfileInfo = getDocProfileInfo(doc);
                          return (
                            <>
                              <h2 style={{ fontSize: "16px", margin: 0 }}>{doc.filename}</h2>
                              <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "12px" }}>
                                Document Type: <strong>{currentProfileInfo.label}</strong> · Status: <Badge value={doc.status} />
                              </p>
                            </>
                          );
                        })()}
                      </div>
                      <div className="document-actions-right" style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <CopyExtraction
                          doc={doc}
                          columns={getDocProfileInfo(doc).columns}
                          provider={cfg?.payload.provider}
                        />

                        {/* Per-Field Reprocessing Button */}
                        {data.can_review && doc.status === "COMPLETED" && (
                          <button
                            className="btn-secondary-action compact-btn"
                            onClick={() => setShowReprocess((prev) => !prev)}
                            title="Reprocess specific fields with AI without re-extracting the entire document"
                          >
                            <WandSparkles size={14} />
                            <span>{showReprocess ? "Hide Reprocess" : "Reprocess Specific Fields"}</span>
                          </button>
                        )}

                        {data.can_review && ["COMPLETED", "ERROR", "NEEDS_CLASSIFICATION"].includes(doc.status) && (
                          <button
                            className="text-link"
                            style={{ fontSize: "12px" }}
                            onClick={() => setAction({ kind: "move", doc })}
                          >
                            <MoveRight size={14} />
                            Move Case
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Per-Field AI Reprocessing Panel */}
                    {showReprocess && (
                      <div className="per-field-reprocess-container">
                        <div className="per-field-reprocess-header">
                          <div>
                            <strong>Per-Field AI Reprocessing</strong>
                            <p>
                              Select one or more individual fields to re-extract with targeted prompt guidance without re-processing the entire document.
                            </p>
                          </div>
                          <button className="text-button" onClick={() => setShowReprocess(false)}>
                            Close
                          </button>
                        </div>
                        <FieldReprocess
                          documentId={doc.id}
                          columns={getDocProfileInfo(doc).columns || []}
                          onQueued={() => {
                            setShowReprocess(false);
                            notify("Field reprocessing request queued.");
                            void refresh();
                          }}
                          canReplaceOverrides={data.can_write}
                        />
                      </div>
                    )}

                    {Object.keys(doc.normalized || {}).length ||
                    doc.validation?.visual_evidence?.length ||
                    doc.validation?.field_evidence?.length ? (
                      <FieldEvidenceWorkspace
                        doc={doc}
                        columns={getDocProfileInfo(doc).columns}
                        provider={cfg?.payload.provider}
                        canWrite={data.can_write}
                        canReview={data.can_review}
                        pending={pending}
                        onRefreshCrops={() =>
                          void run(
                            () => api(`/documents/${doc.id}/field-evidence`, { method: "POST" }),
                            "Bukti visual diperbarui dari hasil tersimpan.",
                          )
                        }
                        onCorrectField={(field) => setAction({ kind: "correction", doc, field })}
                        onRegionSaved={() => void refresh()}
                      />
                    ) : (
                      <Empty
                        title={
                          ["ERROR", "NEEDS_CLASSIFICATION"].includes(doc.status)
                            ? "Action required before extraction"
                            : doc.status === "COMPLETED"
                              ? "No field values detected"
                              : "Processing with AI in background"
                        }
                        detail={
                          doc.status === "COMPLETED"
                            ? "The extraction model did not detect structured field values on this document."
                            : "The platform is reading and verifying document contents automatically."
                        }
                      />
                    )}
                  </section>
                ) : (
                  <Empty
                    title="No documents in this customer case yet"
                    detail="Upload customer identity or transaction documents to begin automated extraction."
                  />
                )}
              </div>
            )}

            {/* MODE 2: SOP COMPLIANCE CHECKS */}
            {activeMode === "sop" && (
              <div className="mode-view-sop">
                <CaseSOP data={data} refresh={refresh} />

                {/* SOP Findings Section */}
                <CaseSopFindings
                  findings={report?.snapshot.findings || []}
                  documents={data.documents}
                  profiles={cfg?.payload.profiles}
                  findingFilter={findingFilter}
                  onFilterChange={setFindingFilter}
                />
              </div>
            )}

            {/* MODE 3: AUDIT TRAIL & HISTORY */}
            {activeMode === "reports" && (
              <div className="mode-view-reports">
                {/* Audit Timeline */}
                <section className="panel timeline-panel" style={{ padding: "20px 24px" }}>
                  <div className="section-head" style={{ marginBottom: 16 }}>
                    <h2 style={{ fontSize: "16px", margin: 0 }}>Audit Trail & History Timeline</h2>
                    <span className="count-pill">{data.timeline.length} events</span>
                  </div>

                  <div className="timeline">
                    {data.timeline.map((t) => (
                      <div key={t.id}>
                        <span className="timeline-dot" />
                        <section>
                          <strong>{t.event.replaceAll(".", " / ").replaceAll("_", " ")}</strong>
                          <p>
                            {formatDate(t.created_at)} ·{" "}
                            {t.actor === "worker"
                              ? "Automated Worker"
                              : t.actor === user?.id
                                ? "You"
                                : t.actor}
                          </p>
                          {devMode && (
                            <details style={{ marginTop: 4 }}>
                              <summary style={{ fontSize: "11px", color: "#64748b", cursor: "pointer" }}>Technical Details</summary>
                              <pre style={{ fontSize: "11px", marginTop: 4 }}>{JSON.stringify(t.details, null, 2)}</pre>
                            </details>
                          )}
                        </section>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            )}

            {/* Bottom Maintenance Collapsible Drawer (For Admins & Developers Only) */}
            {data.can_review && devMode && (
              <details className="bottom-maintenance-drawer">
                <summary>
                  <Wrench size={15} />
                  <span>Case Maintenance & Developer Utilities</span>
                </summary>
                <div style={{ marginTop: 14 }}>
                  <BatchGroupingRepair
                    key={id}
                    batchIds={Array.from(
                      new Set(
                        data.documents
                          .map((d) => d.batch_id)
                          .filter((batchId): batchId is string => !!batchId),
                      ),
                    )}
                  />
                  {data.documents.some((d) => d.doc_type === "ektp" && d.status === "COMPLETED") && (
                    <EnumRevalidation caseId={id} refresh={refresh} />
                  )}
                  {data.can_adopt_configuration && (
                    <CaseConfiguration caseId={id} currentVersion={data.config_version} refresh={refresh} />
                  )}
                  <div style={{ marginTop: 12 }}>
                    <CaseTask caseId={data.id} />
                  </div>
                </div>
              </details>
            )}
          </div>
        )
      )}

      {/* Action Modal (Corrections, Classification, Move, Reconcile) */}
      {action && (
        <ActionModal
          key={`${action.kind}-${action.doc.id}-${action.field || ""}`}
          action={action}
          onClose={close}
          onComplete={async () => {
            close();
            await refresh();
          }}
        />
      )}
    </Shell>
  );
}
