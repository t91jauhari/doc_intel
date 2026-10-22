"use client";

import { useEffect, useState } from "react";
import { ArrowRightLeft, Eye, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Configuration } from "@/lib/types";

type Candidate = { id: string; label: string; left: string; right: string; families: string[] };
type Preview = { source_version: number; basis_sha256: string; converted_rule_ids: string[]; payload: Configuration };

export function ComparisonUpgrade({ configuration, version, editable, onApply, family }: {
  configuration: Configuration; version: number; editable: boolean;
  family: string;
  onApply: (configuration: Configuration) => void;
}) {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewSource, setPreviewSource] = useState<Configuration | null>(null);
  const [previewFamily, setPreviewFamily] = useState("");
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    setLoadingCandidates(true);
    if (editable) api<{ candidates: Candidate[] }>("/config/upgrades/comparisons")
      .then(result => { if (!cancelled) setCandidates(result.candidates); })
      .catch(error => { if (!cancelled) setError(error instanceof Error ? error.message : "Could not load upgrade options."); })
      .finally(() => { if (!cancelled) setLoadingCandidates(false); });
    return () => { cancelled = true; };
  }, [version, editable]);
  useEffect(() => { setPreview(null); setPreviewSource(null); setSelected([]); }, [configuration, version, family]);
  if (!editable) return null;
  const available = candidates.filter(candidate => candidate.families.includes(family) && configuration.sop_rules?.some(rule => rule.id === candidate.id));
  const configured = (configuration.generic_sop_rules || []).filter(rule => rule.families.includes(family));
  const previewCurrent = preview && previewSource === configuration && preview.source_version === version && previewFamily === family;
  async function inspect() {
    setBusy(true); setError(""); setPreview(null);
    try {
      const result = await api<Preview>("/config/upgrades/comparisons/preview", {
        method: "POST", body: JSON.stringify({ expected_version: version, rule_ids: selected, payload: configuration }),
      });
      setPreview(result); setPreviewSource(configuration); setPreviewFamily(family);
    } catch (error) { setError(error instanceof Error ? error.message : "Preview failed."); }
    finally { setBusy(false); }
  }
  return <><section className="panel settings-card" aria-labelledby="comparison-upgrade-title">
    <h2 id="comparison-upgrade-title"><ArrowRightLeft size={20} aria-hidden="true" /> Upgrade comparison rules</h2>
    <p>Move supported checks into editable comparison policies. Rule IDs, scoring and order are preserved. Review first, then add the changes to your draft.</p>
    {error && <p role="alert">{error}</p>}
    {loadingCandidates ? <p role="status">Loading supported rules…</p> : available.length ? <fieldset disabled={busy}>
      <legend>Choose rules to review</legend>
      {available.map(candidate => <label key={candidate.id} style={{ display: "flex", flexDirection: "row", alignItems: "start", gap: 12 }}>
        <input type="checkbox" style={{ width: "auto", flex: "0 0 auto" }} checked={selected.includes(candidate.id)} onChange={event => {
          setPreview(null);
          setSelected(event.target.checked ? [...selected, candidate.id] : selected.filter(id => id !== candidate.id));
        }} />
        <span>{candidate.label}<small style={{ display: "block" }}>{candidate.left} ↔ {candidate.right}</small></span>
      </label>)}
      <button type="button" className="button secondary" disabled={!selected.length || busy} onClick={inspect}>
        <Eye size={16} aria-hidden="true" /> {busy ? "Preparing preview…" : `Preview ${selected.length || "selected"} rules`}
      </button>
    </fieldset> : <p>No supported rules remain in this draft.</p>}
    {previewCurrent && <div role="region" aria-label="Comparison upgrade preview">
      <h3><CheckCircle2 size={18} aria-hidden="true" /> Ready for draft review</h3>
      <p>{preview.converted_rule_ids.length} rules from configuration v{preview.source_version}. Existing cases keep their configuration.</p>
      <ul>{available.filter(candidate => preview.converted_rule_ids.includes(candidate.id)).map(candidate =>
        <li key={candidate.id}>{candidate.label}<small style={{ display: "block" }}>Case and whitespace normalized · matching text required</small></li>)}</ul>
      <button type="button" className="button" onClick={() => onApply(preview.payload)}>Add upgrade to draft</button>
      <p>Use the configuration’s Test and Publish actions when your draft is ready. This preview has not published changes.</p>
    </div>}
  </section>
  {!!configured.length && <section className="panel settings-card" aria-labelledby="configured-comparisons-title">
    <h2 id="configured-comparisons-title">Configurable comparisons</h2>
    <p>Edit comparison wording and matching behavior in your draft. Field bindings stay visible for review.</p>
    {configured.map(rule => {
      const change = (patch: Partial<typeof rule>) => onApply({ ...configuration,
        generic_sop_rules: configuration.generic_sop_rules!.map(value => value.id === rule.id ? { ...value, ...patch } : value),
      });
      return <fieldset key={rule.id}>
        <legend>{rule.label}</legend>
        <label>Rule description<input aria-label={`Description for ${rule.id}`} value={rule.label} onChange={event => change({ label: event.target.value })} /></label>
        <p>{rule.policy.left} ↔ {rule.policy.right}</p>
        <label>Matching behavior<select aria-label={`Matching behavior for ${rule.id}`} value={rule.policy.normalization || "literal"}
          onChange={event => change({ policy: { ...rule.policy, normalization: event.target.value as "literal" | "casefold_whitespace" } })}>
          <option value="literal">Exact characters</option>
          <option value="casefold_whitespace">Ignore letter case and extra spaces</option>
        </select></label>
        <label style={{ display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", gap: 8 }}><input type="checkbox" style={{ width: "auto", flex: "0 0 auto" }} checked={rule.enabled !== false} onChange={event => change({ enabled: event.target.checked })} /> Check enabled</label>
      </fieldset>;
    })}
  </section>}</>;
}
