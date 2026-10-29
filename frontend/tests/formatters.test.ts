import test from "node:test";
import assert from "node:assert/strict";
import {
  formatAmount,
  formatCurrency,
  formatDisplay,
  isAmountField,
  isScopeDisclaimerFinding,
} from "../lib/formatters";

test("formatAmount extracts pure numeric amount from money schema without currency strings", () => {
  const single = { amount_raw: "1530,00", currency_raw: "USD", unit_raw: "MT" };
  assert.equal(formatAmount(single), "1530,00");

  const rowArray = [
    { row_id: "1", amount_raw: "1530,00", currency_raw: "USD" },
    { row_id: "2", amount_raw: "206.550,00", currency_raw: "USD" },
  ];
  assert.equal(formatAmount(rowArray), "1530,00\n206.550,00");

  const normalized = { amount: "206550.00", currency: "USD" };
  assert.equal(formatAmount(normalized), "206550.00");

  assert.equal(formatAmount(null), "Missing");
  assert.equal(formatAmount(undefined), "Missing");
  assert.equal(formatAmount(""), "Missing");
  assert.equal(formatAmount("123.45"), "123.45");
});

test("formatCurrency extracts currency symbol or ISO code", () => {
  assert.equal(formatCurrency({ currency_raw: "USD", amount_raw: "100" }), "USD");
  assert.equal(formatCurrency({ currency: "$", amount: "50" }), "$");
  assert.equal(formatCurrency(null), "");
  assert.equal(formatCurrency("USD"), "");
});

test("isAmountField identifies numeric fields and guards against presence objects", () => {
  assert.equal(isAmountField({ amount_raw: "100", currency_raw: "USD" }), true);
  assert.equal(isAmountField([{ amount: "50" }]), true);

  // claim_note has present: false/true and should not be treated as amount
  const claimNote = {
    present: false,
    note_raw: null,
    amount_raw: null,
  };
  assert.equal(isAmountField(claimNote), false);

  assert.equal(isAmountField(null), false);
  assert.equal(isAmountField("string"), false);
  assert.equal(isAmountField(123), false);
});

test("isScopeDisclaimerFinding accurately detects regulatory non-penalizing disclaimers", () => {
  const disclaimer1 = {
    result: "NOT_APPLICABLE",
    reason_code: "EXPLICITLY_NOT_APPLICABLE",
    message: "Policy Disclaimer Check",
  };
  assert.equal(isScopeDisclaimerFinding(disclaimer1), true);

  const disclaimer2 = {
    result: "PASS",
    evidence: { policy: "regulatory_scope_disclaimer" },
  };
  assert.equal(isScopeDisclaimerFinding(disclaimer2), true);

  const normalFailure = {
    result: "FAIL",
    reason_code: "MISMATCH",
  };
  assert.equal(isScopeDisclaimerFinding(normalFailure), false);

  assert.equal(isScopeDisclaimerFinding(null), false);
});

test("formatDisplay formats general values cleanly", () => {
  assert.equal(formatDisplay(true), "Present");
  assert.equal(formatDisplay(false), "Absent");
  assert.equal(formatDisplay(null), "Missing");
  assert.equal(formatDisplay("PT Tiga Utama"), "PT Tiga Utama");
});
