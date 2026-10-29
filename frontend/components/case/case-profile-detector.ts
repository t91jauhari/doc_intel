import type { ConfigResponse, Document } from "@/lib/types";

export const INVOICE_1_COLUMNS: [string, string][] = [
  ["from_name", "Company Name (Header)"],
  ["from_address", "Company Address"],
  ["to_name", "Bill To Name"],
  ["to_address", "Bill To Address"],
  ["to_phone", "Bill To Phone"],
  ["ship_to_name", "Ship To Name"],
  ["ship_to_address", "Ship To Address"],
  ["ship_to_phone", "Ship To Phone"],
  ["invoice_number", "Invoice Number\n(what if the underlying is not an invoice)"],
  ["invoice_date", "Invoice Date\n(what if the underlying is not an invoice)"],
  ["due_date", "Due Date"],
  ["item_name", "Item Description"],
  ["quantity", "Quantity"],
  ["unit_price", "Unit Price"],
  ["final_total_amount", "Total"],
  ["subtotal_all_items", "Subtotal"],
  ["discount", "Discount"],
  ["subtotal_less_discount", "Subtotal Less Discount"],
  ["shipping_handling", "Shipping/Handling"],
  ["beneficiary_name", "Beneficiary Name"],
  ["bank_account_number", "Account Number"],
  ["bank_name", "Beneficiary Bank"],
  ["bank_address", "Address Bank"],
  ["swift_code", "Beneficary Bank SWIFT Code"],
];

export const INVOICE_2_COLUMNS: [string, string][] = [
  ["to_name", "To (Customer Name)"],
  ["to_address", "To Address"],
  ["to_phone", "To Phone"],
  ["from_name", "From (Company Name)"],
  ["from_address", "From Address"],
  ["from_phone", "From Phone"],
  ["bank_name", "Bank Name (Payment Note)"],
  ["swift_code", "SWIFT Code"],
  ["bank_account_number", "Bank Account Number"],
  ["invoice_date", "Invoice Date"],
  ["due_date", "Due Date"],
  ["invoice_number", "Invoice Number"],
  ["item_name", "Item Name"],
  ["quantity", "Quantity"],
  ["unit_price", "Unit Price"],
  ["subtotal", "Subtotal"],
  ["subtotal_all_items", "Subtotal (All Items)"],
  ["final_total_amount", "Final Total Amount"],
  ["claim_note", "Claim No.2 (60% of Supply Equipment) Claim Note / Material Arrived at Site"],
];

export function detectInvoiceProfile(docItem: Document, cfg?: ConfigResponse | null): boolean {
  if (docItem.doc_type === "invoice_2") return true;
  if (docItem.doc_type === "invoice_1") return false;

  const signatures = cfg?.payload.invoice_signatures || {
    invoice_2_terms: [
      "claim no",
      "supply equipment",
      "material arrived at site",
      "pt tiga utama",
      "chem co",
      "dokumen underlying",
    ],
    invoice_1_terms: [
      "ship to",
      "bill to",
      "subtotal less discount",
      "shipping/handling",
    ],
  };

  const norm = (docItem.normalized || {}) as Record<string, unknown>;
  const raw = (docItem.raw || {}) as Record<string, unknown>;

  // 1. Check if claim_note has positive milestone/claim content
  const claim = (norm.claim_note || raw.claim_note) as Record<string, unknown> | undefined;
  if (claim && typeof claim === "object") {
    if (claim.present === true || claim.note || claim.claim_number) {
      return true;
    }
  }

  // 2. Scan OCR text / vendor signatures for Invoice 2 (FIRST priority)
  const haystack = `${JSON.stringify(raw)} ${JSON.stringify(norm)} ${docItem.filename || ""}`.toLowerCase();
  for (const term of signatures.invoice_2_terms) {
    if (haystack.includes(term.toLowerCase())) return true;
  }

  // 3. Check if invoice_1 specific fields or terms are present
  if (
    (norm.ship_to_name && norm.ship_to_name !== "Missing") ||
    (norm.discount && norm.discount !== "Missing") ||
    (norm.shipping_handling && norm.shipping_handling !== "Missing") ||
    (norm.beneficiary_name && norm.beneficiary_name !== "Missing")
  ) {
    return false;
  }

  for (const term of signatures.invoice_1_terms) {
    if (haystack.includes(term.toLowerCase())) return false;
  }

  return false;
}

export function cleanDocDisplayFilename(filename: string, customer?: string): string {
  let clean = filename;
  if (customer) {
    clean = clean.replace(new RegExp(`^.*?${customer.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*-\\s*`, "i"), "");
  }
  clean = clean.replace(/^Forex\s*-\s*/i, "");
  return clean.trim() || filename;
}
