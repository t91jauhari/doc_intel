"use client";
import { createPortal } from "react-dom";
import { useEffect, useRef } from "react";
import { X, LoaderCircle, ArrowUpRight, FileText } from "lucide-react";
import Link from "next/link";
import type { CaseSummary } from "@/lib/types";
import { StatusBadge, SopBadge } from "@/components/status";
import { formatWhen } from "@/lib/time";

export function Badge({ value }: { value: string }) {
  if (!value || value.toUpperCase() === "SKIPPED") return null;
  const upper = value.toUpperCase();
  const color = [
    "PASS",
    "MATCH",
    "FUZZY_MATCH",
    "READY",
    "COMPLETED",
    "FINAL",
    "FINALIZED",
  ].includes(upper)
    ? "good"
    : [
          "FAIL",
          "NOT_COMPLIANT",
          "MISMATCH",
          "VALUE_MISSING",
          "DOCUMENT_MISSING",
          "ERROR",
          "PROCESSING_ERROR",
          "SOP_ERROR",
        ].includes(upper)
      ? "bad"
      : [
            "REVIEW",
            "UNMAPPED",
            "NEEDS_REVIEW",
            "NEEDS_CLASSIFICATION",
            "WAITING_DOCUMENTS",
          ].includes(upper)
        ? "warn"
        : "neutral";
  const label =
    upper === "FAIL" || upper === "FAILED"
      ? "Not Compliant"
      : upper === "NOT_APPLICABLE"
        ? "Scope Disclaimer"
        : value.replaceAll("_", " ").toLowerCase();
  return (
    <span className={"badge " + color}>
      {label}
    </span>
  );
}
export function Busy({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="busy" role="status">
      <LoaderCircle size={18} className="spin" />
      {label}
    </div>
  );
}
export function Empty({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <FileText size={24} />
      </div>
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
    </div>
  );
}
export function ErrorNotice({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="error-notice" role="alert">
      <span>{message}</span>
      {retry && <button onClick={retry}>Retry</button>}
    </div>
  );
}
export {
  formatDate,
  formatAmount,
  formatCurrency,
  formatDisplay,
  display,
  formatInvoiceAmount,
} from "@/lib/formatters";
export function CaseTable({ cases }: { cases: CaseSummary[] }) {
  return (
    <div className="table-scroll">
      <table className="case-table">
        <thead>
          <tr>
            <th>Customer / case</th>
            <th>Progress</th>
            <th>Workflow</th>
            <th>SOP</th>
            <th>Updated</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id}>
              <td>
                <Link className="customer-link" href={"/cases/" + c.id}>
                  {c.customer}
                </Link>
                <div className="subtext">
                  {c.reference} · {c.transaction_flow_label || c.template}
                  {c.branch_name ? ` · ${c.branch_name}` : ""}
                </div>
              </td>
              <td>
                <div className="mini-progress">
                  <span
                    style={{
                      width:
                        (c.documents_count
                          ? (c.completed_count / c.documents_count) * 100
                          : 0) + "%",
                    }}
                  />
                </div>
                <div className="subtext">
                  {c.completed_count} / {c.documents_count}
                  {c.missing_documents?.length
                    ? " · Missing: " + c.missing_documents.join(", ")
                    : c.documents_count
                      ? " · complete"
                      : ""}
                </div>
              </td>
              <td>
                <StatusBadge value={c.status} />
              </td>
              <td>
                <SopBadge value={c.validation_status} />
              </td>
              <td
                className="muted"
                title={new Date(c.updated_at * 1000).toISOString()}
              >
                {formatWhen(c.updated_at)}
              </td>
              <td>
                <Link
                  className="text-link"
                  href={"/cases/" + c.id}
                  aria-label={"Open " + c.customer}
                >
                  {c.status === "WAITING_DOCUMENTS"
                    ? "Add docs"
                    : ["ERROR", "PROCESSING_ERROR"].includes(c.status)
                      ? "Resolve error"
                      : c.status === "NEEDS_REVIEW" ||
                          c.validation_status === "NEEDS_REVIEW" ||
                          c.validation_status === "REVIEW"
                        ? "Review case"
                        : "Open case"}
                  <ArrowUpRight size={15} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Modal({
  className = "",
  title,
  onClose,
  children,
}: {
  className?: string;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const focusable = () =>
      Array.from(
        ref.current?.querySelectorAll<HTMLElement>(
          "button,input,textarea,select,a[href]",
        ) || [],
      ).filter((x) => !x.hasAttribute("disabled"));

    // Focus first input field or first interactive element on mount
    const inputs = Array.from(
      ref.current?.querySelectorAll<HTMLElement>(
        "input:not([disabled]),textarea:not([disabled]),select:not([disabled])",
      ) || [],
    );
    if (inputs.length > 0) {
      inputs[0]?.focus();
    } else {
      focusable()[0]?.focus();
    }

    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
      if (e.key === "Tab") {
        const list = focusable();
        if (e.shiftKey && document.activeElement === list[0]) {
          e.preventDefault();
          list[list.length - 1]?.focus();
        } else if (
          !e.shiftKey &&
          document.activeElement === list[list.length - 1]
        ) {
          e.preventDefault();
          list[0]?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, []);
  if (typeof document === "undefined") return null;
  return createPortal(
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className={`modal ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="modal-head">
          <h2 id="modal-title">{title}</h2>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
