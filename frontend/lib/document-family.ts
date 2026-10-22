import type { ProfileName, Configuration, DocumentFamilyConfig } from "./types";
export type DocumentFamily = string;
export const familyLabels: Record<DocumentFamily, string> = {
  forex: "Forex",
  account_opening: "Account Opening",
};
const shared: ProfileName[] = ["ektp", "riplay"];
export const familyProfiles: Record<DocumentFamily, ProfileName[]> = {
  forex: [
    "application",
    "lld",
    "invoice",
    "valas_declaration_1",
    "valas_declaration_2",
    ...shared,
  ],
  account_opening: [
    "account_opening_form",
    "join_visit",
    "edd",
    "signature_difference",
    "company_reference",
    ...shared,
  ],
};
export const familyCatalog = (cfg?: Configuration | null): Record<string,DocumentFamilyConfig> => ({
  forex: {label:"Forex",profiles:familyProfiles.forex,required:cfg?.templates.forex?.required||[],sop_rule_ids:(cfg?.sop_rules||[]).filter(r=>!(r.source_ref||"").startsWith("AO:")).map(r=>r.id),dataset_id:"forex-sample-v1",report_layout:"forex"},
  account_opening: {label:"Account Opening",profiles:familyProfiles.account_opening,required:cfg?.templates.account_opening?.required||[],sop_rule_ids:(cfg?.sop_rules||[]).filter(r=>(r.source_ref||"").startsWith("AO:")).map(r=>r.id),dataset_id:"account-opening-sample-v1",report_layout:"account_opening"},
  ...cfg?.document_families,
});
export const inFamily = (type: string, family: DocumentFamily, cfg?: Configuration | null) =>
  (familyCatalog(cfg)[family]?.profiles || []).includes(type as ProfileName);
// Same discriminator as backend transaction_flows.scoped_config.
export const ruleInFamily = (
  rule: { source_ref?: string; id?: string },
  family: DocumentFamily,
  cfg?: Configuration | null,
) =>
  family === "forex" || family === "account_opening"
    ? (rule.source_ref || "").startsWith("AO:") === (family === "account_opening")
    : !!rule.id && !!familyCatalog(cfg)[family]?.sop_rule_ids?.includes(rule.id);
