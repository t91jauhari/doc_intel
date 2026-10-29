import { Badge, Empty } from "@/components/ui";
import { display, isScopeDisclaimerFinding } from "@/lib/formatters";
import type { ConfigResponse, Document, Finding } from "@/lib/types";

export type FindingFilter = "all" | "attention" | "visual" | "pass" | "disclaimer";

export function CaseSopFindings({
  findings,
  documents,
  profiles,
  findingFilter,
  onFilterChange,
}: {
  findings: Finding[];
  documents: Document[];
  profiles?: ConfigResponse["payload"]["profiles"];
  findingFilter: FindingFilter;
  onFilterChange: (f: FindingFilter) => void;
}) {
  const attentionCount = findings.filter((f) => ["FAIL", "REVIEW", "ERROR"].includes(f.result)).length;
  const visualCount = findings.filter((f) => f.evaluation_type === "VISUAL").length;
  const passCount = findings.filter((f) => f.result === "PASS").length;
  const disclaimerCount = findings.filter((f) => isScopeDisclaimerFinding(f)).length;

  const filteredFindings = findings.filter((f) => {
    if (findingFilter === "attention") return ["FAIL", "REVIEW", "ERROR"].includes(f.result);
    if (findingFilter === "visual") return f.evaluation_type === "VISUAL";
    if (findingFilter === "pass") return f.result === "PASS";
    if (findingFilter === "disclaimer") return isScopeDisclaimerFinding(f);
    return true;
  });

  return (
    <section className="panel findings-section" style={{ marginTop: 20, padding: "20px 24px" }}>
      <div className="field-evidence-toolbar" style={{ margin: "-20px -24px 16px", padding: "12px 24px" }}>
        <div className="field-filter-pills">
          {[
            ["all", "All Findings", findings.length],
            ["attention", "Needs Attention", attentionCount],
            ["visual", "Visual Checks", visualCount],
            ["pass", "Compliant (Pass)", passCount],
            ["disclaimer", "Scope Disclaimers", disclaimerCount],
          ].map(([key, label, count]) => (
            <button
              key={String(key)}
              type="button"
              className={findingFilter === key ? "active" : ""}
              onClick={() => onFilterChange(key as FindingFilter)}
            >
              {label} <span>{count}</span>
            </button>
          ))}
        </div>
      </div>

      {findings.length ? (
        <div className="findings-list">
          {filteredFindings.map((f, index) => {
            const leftPath = String(f.evidence?.path || f.field || "");
            const rightPath = String(f.evidence?.other_path || "");

            const leftDocIds = Array.isArray(f.evidence?.document_ids)
              ? (f.evidence.document_ids as string[])
              : typeof f.evidence?.document_id === "string"
                ? [f.evidence.document_id]
                : [];
            const leftDoc =
              documents.find((d) => leftDocIds.includes(d.id)) ||
              documents.find((d) => leftPath.startsWith(d.doc_type + "."));

            const rightDocIds = Array.isArray(f.evidence?.reference_document_ids)
              ? (f.evidence.reference_document_ids as string[])
              : typeof f.evidence?.reference_document_id === "string"
                ? [f.evidence.reference_document_id]
                : [];
            const rightDoc =
              documents.find((d) => rightDocIds.includes(d.id)) ||
              documents.find((d) => rightPath.startsWith(d.doc_type + "."));

            const leftLabel = leftDoc
              ? profiles?.[leftDoc.doc_type as keyof typeof profiles]?.columns?.find(
                  ([k]) => k === leftPath.replace(leftDoc.doc_type + ".", ""),
                )?.[1] || leftPath
              : leftPath;

            const rightLabel = rightDoc
              ? profiles?.[rightDoc.doc_type as keyof typeof profiles]?.columns?.find(
                  ([k]) => k === rightPath.replace(rightDoc.doc_type + ".", ""),
                )?.[1] || rightPath
              : rightPath;

            const isDisclaimer = isScopeDisclaimerFinding(f);
            const actualVal = f.actual ?? f.evidence?.value ?? f.evidence?.actual_value;
            const expectedVal = f.expected ?? f.evidence?.other_value ?? f.evidence?.expected_value;
            const hasComparison =
              !isDisclaimer &&
              ((actualVal !== undefined && actualVal !== null) ||
                (expectedVal !== undefined && expectedVal !== null));

            return (
              <div
                key={f.rule_id || index}
                className="finding-item"
                style={{
                  padding: "16px",
                  borderRadius: "10px",
                  border: "1px solid #e2e8f0",
                  marginBottom: "12px",
                  background: "#ffffff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <strong style={{ fontSize: "14px", color: "#0f172a" }}>{f.rule_id}</strong>
                      <Badge value={f.result} />
                      {f.evaluation_type === "VISUAL" && <span className="mini-tag visual">Visual Check</span>}
                    </div>
                    <p style={{ margin: "4px 0 8px", fontSize: "13px", color: "#475569" }}>{f.message}</p>
                  </div>
                </div>

                {hasComparison && (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: "12px",
                      background: "#f8fafc",
                      padding: "12px 14px",
                      borderRadius: "8px",
                      marginTop: "8px",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <div>
                      <span style={{ fontSize: "11px", fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>
                        {leftDoc ? leftDoc.filename : "Source Document"} ({leftLabel})
                      </span>
                      <div style={{ fontSize: "13px", fontWeight: 600, color: "#1e293b", marginTop: 4 }}>
                        {display(actualVal)}
                      </div>
                    </div>
                    <div>
                      <span style={{ fontSize: "11px", fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>
                        {rightDoc ? rightDoc.filename : "Comparison Document"} ({rightLabel})
                      </span>
                      <div style={{ fontSize: "13px", fontWeight: 600, color: "#1e293b", marginTop: 4 }}>
                        {display(expectedVal)}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <Empty
          title="No SOP findings recorded"
          detail="Run SOP compliance checks once documents are extracted."
        />
      )}
    </section>
  );
}
