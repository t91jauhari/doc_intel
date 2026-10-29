/**
 * Schema-driven value presentation formatters.
 * Decouples presentation formatting from UI primitives and data models.
 */

export interface DisplayOptions {
  amountOnly?: boolean;
  hideCurrency?: boolean;
}

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function formatDate(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "number" ? value : Number(value);
  if (!Number.isNaN(num) && num > 0) {
    const epochMs = num > 1e11 ? num : num * 1000;
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Jakarta",
    }).format(new Date(epochMs));
  }
  return String(value);
}

/**
 * Extracts pure numeric amount from schema-driven value structures.
 * Utilizes schema properties (amount_raw, amount, value_raw) directly without ad-hoc string stripping.
 */
export function formatAmount(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Missing";

  if (Array.isArray(value)) {
    const rows = value
      .map(formatAmount)
      .filter((v) => v !== "" && v !== "Missing");
    return rows.length > 0 ? rows.join("\n") : "Missing";
  }

  if (typeof value !== "object") {
    const str = String(value).replace(/<br\s*\/?>/gi, " ").trim();
    return str || "Missing";
  }

  const record = value as Record<string, unknown>;

  // Check typed numeric/amount properties from schema definitions
  if (record.amount_raw !== undefined && record.amount_raw !== null && record.amount_raw !== "") {
    return formatAmount(record.amount_raw);
  }
  if (record.amount !== undefined && record.amount !== null && record.amount !== "") {
    return formatAmount(record.amount);
  }
  if (record.value_raw !== undefined && record.value_raw !== null && record.value_raw !== "") {
    return formatAmount(record.value_raw);
  }
  if (record.raw !== undefined && record.raw !== null && record.raw !== "") {
    return formatAmount(record.raw);
  }
  if (record.value !== undefined && record.value !== null && record.value !== "") {
    return formatAmount(record.value);
  }

  return "Missing";
}

/**
 * Extracts explicit currency representation from typed schema fields.
 */
export function formatCurrency(value: unknown): string {
  if (!value || typeof value !== "object") return "";
  const record = value as Record<string, unknown>;
  const cur = record.currency_raw ?? record.currency ?? "";
  return String(cur).trim();
}

/**
 * General purpose display formatter for all structured and primitive document values.
 */
export function formatDisplay(value: unknown, options?: DisplayOptions): string {
  if (value === null || value === undefined || value === "") return "Missing";
  if (typeof value === "boolean") return value ? "Present" : "Absent";

  if (Array.isArray(value)) {
    return value.length
      ? value.map((item) => formatDisplay(item, options)).join("\n")
      : "None selected";
  }

  if (typeof value !== "object") {
    return String(value).replace(/<br\s*\/?>/gi, " ");
  }

  const v = value as Record<string, unknown>;

  // 1. Enum selection with optional custom descriptions
  if ("selected" in v) {
    const parts: string[] = [];
    if (Array.isArray(v.selected) ? v.selected.length : v.selected) {
      parts.push(formatDisplay(v.selected, options));
    }
    if (v.other_description) {
      parts.push(formatDisplay(v.other_description, options));
    }
    if (v.raw != null && v.raw !== "") {
      parts.push(formatDisplay(v.raw, options));
    }
    return parts.length ? parts.join(" · ") : formatDisplay(v.selected, options);
  }

  // 2. Structured Money Schema: amount_raw + currency_raw (+ optional unit_raw)
  if ("currency_raw" in v && "amount_raw" in v) {
    if (options?.amountOnly) {
      return formatAmount(v.amount_raw);
    }
    const rawAmt = v.amount_raw != null && v.amount_raw !== "" ? formatDisplay(v.amount_raw, options).trim() : "";
    const cur = v.currency_raw != null && v.currency_raw !== "" ? formatDisplay(v.currency_raw, options).trim() : "";
    let amount = "Missing";
    if (rawAmt && rawAmt !== "Missing") {
      if (cur && cur !== "Missing" && !options?.hideCurrency && !rawAmt.toLowerCase().includes(cur.toLowerCase())) {
        amount = `${cur} ${rawAmt}`;
      } else {
        amount = rawAmt;
      }
    } else if (cur && cur !== "Missing" && !options?.hideCurrency) {
      amount = cur;
    }

    return amount !== "Missing" && v.unit_raw
      ? `${amount}/${formatDisplay(v.unit_raw, options)}`
      : amount;
  }

  // 3. Formatted Date
  if ("formatted_date" in v) return formatDisplay(v.formatted_date, options);

  // 4. Tabular Line Items
  if ("table_complete" in v && Array.isArray(v.items)) {
    const items = v.items.map((item) => formatDisplay(item, options)).join("\n") || "Missing";
    return (v.table_complete === false ? "Incomplete table · " : "") + items;
  }

  // 5. Contact / Identity blocks
  if ("name" in v || "address" in v || "phone" in v) {
    const parts = [v.name, v.branch, v.address, v.phone].filter(
      (part) => part != null && part !== "",
    );
    if (parts.length) return parts.map((part) => formatDisplay(part, options)).join(" · ");
    if ("full_text" in v) return formatDisplay(v.full_text, options);
  }
  if ("full_text" in v) return formatDisplay(v.full_text, options);

  // 6. Multi-page document check (e.g. RIPLAY page footer presence)
  if ("page_count" in v && Array.isArray(v.pages)) {
    const pages123 = v.pages.filter((p: unknown) => {
      if (p == null || typeof p !== "object") return false;
      const pNum = Number((p as Record<string, unknown>).page_number);
      return pNum >= 1 && pNum <= 3;
    });
    if (
      pages123.length === 3 &&
      pages123.every((p: unknown) => {
        const item = p as Record<string, unknown>;
        return item.footer_present === true || item.present === true;
      })
    ) {
      return "present";
    }
    return "missing";
  }

  // 7. Place and Date (signing blocks)
  if ("place" in v && "date" in v) {
    let date = formatDisplay(v.date, options);
    const match =
      typeof v.date === "string" && /^(\d{2})-(\d{2})-(\d{4})$/.exec(v.date);
    if (match && Number(match[2]) >= 1 && Number(match[2]) <= 12) {
      date = `${Number(match[1])} ${MONTH_NAMES[Number(match[2]) - 1]} ${match[3]}`;
    }
    return `${formatDisplay(v.place, options)} — ${date}`;
  }

  // 8. Visual Stamp / Signature Presence
  const presence = "present" in v ? "present" : "stamp_present" in v ? "stamp_present" : null;
  if (presence) {
    const parts = [v[presence] == null ? "Needs review" : formatDisplay(v[presence], options)];
    if ("complete" in v) {
      parts.push(
        v.complete === true
          ? "Complete"
          : v.complete === false
            ? "Incomplete"
            : "Completeness needs review",
      );
    }
    if (v.text) parts.push(String(v.text));
    for (const key of ["comparison_status", "signature_match"]) {
      if (v[key] != null) {
        parts.push(`${key.replaceAll("_", " ")}: ${formatDisplay(v[key], options)}`);
      }
    }
    return parts.join(" · ");
  }

  // 9. Simple raw wrapper
  if ("raw" in v) {
    if (options?.amountOnly) {
      return formatAmount(v.raw);
    }
    return formatDisplay(v.raw, options);
  }

  // Default fallback
  const hiddenKeys = new Set([
    "evidence",
    "citation",
    "confidence",
    "extraction_confidence",
    "bounding_boxes",
    "page_dimensions",
  ]);

  return (
    Object.entries(v)
      .filter(([key]) => !hiddenKeys.has(key))
      .map(([key, val]) => `${key.replaceAll("_", " ")}: ${formatDisplay(val, options)}`)
      .join(" · ") || "Missing"
  );
}

export const display = formatDisplay;
export const formatInvoiceAmount = formatAmount;

/**
 * Checks if a value conforms to a numeric/amount schema object (e.g. money fields)
 * rather than a presence object or arbitrary text, without checking hardcoded field names.
 */
export function isAmountField(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) {
    return value.some(
      (item) =>
        item &&
        typeof item === "object" &&
        !("present" in item) &&
        ("amount_raw" in item || "amount" in item),
    );
  }
  const rec = value as Record<string, unknown>;
  return !("present" in rec) && ("amount_raw" in rec || "amount" in rec);
}

/**
 * Determines if a finding represents a regulatory scope disclaimer based on
 * structured reason codes or evidence policies rather than hardcoded string prefixes.
 */
export function isScopeDisclaimerFinding(finding?: {
  result?: string;
  reason_code?: string;
  evidence?: { policy?: string };
} | null): boolean {
  if (!finding) return false;
  return (
    finding.result === "NOT_APPLICABLE" ||
    finding.reason_code === "EXPLICITLY_NOT_APPLICABLE" ||
    finding.evidence?.policy === "regulatory_scope_disclaimer"
  );
}
