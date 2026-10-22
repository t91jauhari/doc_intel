/**
 * Non-billable end-to-end test. Starts isolated API, worker and built frontend.
 * Run after frontend build and Playwright browser installation.
 */
import { createRequire } from "node:module";
import { spawn, spawnSync } from "node:child_process";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "frontend/package.json"));
const { chromium } = require(
  process.env.PLAYWRIGHT_MODULE || "@playwright/test",
);
const directory = await mkdtemp(path.join(tmpdir(), "sqe-browser-"));
const python =
  process.env.TEST_PYTHON ||
  path.join(
    root,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
const env = {
  ...process.env,
  APP_ENV: "development",
  APP_SECRET: "isolated-browser-test-secret-32-characters",
  DEV_PASSWORD: "P@ssw0rd2026",
  DEV_EMAIL: "sqe@bic.local",
  DEV_ORGANIZATION: "sqe",
  DATABASE_URL:
    "sqlite:///" + path.join(directory, "test.db").replaceAll("\\", "/"),
  STORAGE_DRIVER: "local",
  STORAGE_PATH: path.join(directory, "files"),
  WORKFLOW_DRIVER: "local",
  API_INTERNAL_URL: "http://127.0.0.1:8000",
  ALLOWED_ORIGINS: "http://localhost:3000,http://127.0.0.1:3000",
  NEXT_TELEMETRY_DISABLED: "1",
};
const children = [];
const output =
  process.env.BROWSER_OUTPUT_DIR || path.join(root, "data/browser-checks");
await mkdir(output, { recursive: true });
const evidence = {
  mode: "synthetic fixtures",
  liveLlama: false,
  checks: [],
  cases: [],
};
let logs = "",
  browser,
  page;
function start(command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  for (const stream of [child.stdout, child.stderr])
    stream.on("data", (data) => {
      logs = (logs + data.toString()).slice(-12000);
    });
  children.push(child);
  return child;
}
async function waitFor(url) {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(1500) });
      if (r.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Service did not start: " + url);
}
try {
  start(
    python,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    path.join(root, "backend"),
  );
  console.log("Waiting for isolated API…");
  await waitFor("http://127.0.0.1:8000/api/health");
  console.log("API ready.");
  start(python, ["-m", "app.worker"], path.join(root, "backend"));
  start(
    process.execPath,
    [
      path.join(root, "frontend/node_modules/next/dist/bin/next"),
      "start",
      "--port",
      "3000",
      "--hostname",
      "127.0.0.1",
    ],
    path.join(root, "frontend"),
  );
  await waitFor("http://127.0.0.1:3000/login");
  console.log("Frontend ready.");
  browser = await chromium.launch({
    headless: true,
    args:
      process.env.BROWSER_SINGLE_PROCESS === "1" ? ["--single-process"] : [],
  });
  console.log("Browser ready.");
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (response) => {
    if (response.status() >= 500)
      errors.push(`${response.status()} ${response.url()}`);
  });
  await page.goto("http://127.0.0.1:3000/login");
  await page.getByLabel("Password", { exact: true }).fill(env.DEV_PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("http://127.0.0.1:3000/");
  await page.getByRole("heading", { name: "Operations overview" }).waitFor();
  await page.screenshot({
    path: path.join(output, "overview-empty.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Configuration", exact: true }).click();
  await page.getByLabel("Provider", { exact: true }).selectOption("fixture");
  await page.getByRole("button", { name: "Publish settings" }).click();
  await page
    .getByText("Configuration published. New cases use the new version.")
    .waitFor();
  await page.getByRole("button", { name: "Automation", exact: true }).click();
  const [configDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download editable XLSX template" }).click(),
  ]);
  const configFile = path.join(directory, "configuration.xlsx");
  await configDownload.saveAs(configFile);
  await page.getByLabel("Import workbook").setInputFiles(configFile);
  await page
    .getByText("Workbook loaded as draft. Replay before publishing.")
    .waitFor();
  await page
    .getByRole("button", { name: "Test settings", exact: true })
    .click();
  await page.getByRole("heading", { name: /Configuration test/ }).waitFor();
  await page.getByRole("button", { name: "SOP rules", exact: true }).click();
  await page.getByRole("button", { name: "Add rule", exact: true }).click();
  await page.getByLabel("Rule ID", { exact: true }).fill("BROWSER_NAME");
  await page
    .getByLabel("Finding message", { exact: true })
    .fill("Browser name comparison");
  await page
    .getByLabel("Approved source", { exact: true })
    .selectOption("SOP3:1");
  await page.getByLabel("Document", { exact: true }).selectOption("ektp");
  await page
    .getByLabel("Field", { exact: true })
    .first()
    .selectOption("ektp.name");
  await page
    .getByLabel("Reference document", { exact: true })
    .selectOption("application");
  await page
    .getByLabel("Field", { exact: true })
    .nth(1)
    .selectOption("application.remitter.name");
  await page
    .getByRole("button", { name: "Apply to draft", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Publish settings", exact: true })
    .click();
  await page
    .getByText("Configuration published. New cases use the new version.")
    .waitFor();
  await page
    .getByRole("link", { name: "Upload documents", exact: true })
    .click();
  await page.locator('input[type="file"]').setInputFiles([
    {
      name: "Poko_transaction.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\nsynthetic upload\n%%EOF"),
    },
    {
      name: "Poko_lld.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\nsynthetic upload LLD\n%%EOF"),
    },
    {
      name: "Poko_invoice.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\nsynthetic upload invoice\n%%EOF"),
    },
    {
      name: "Rina_ektp.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\nsynthetic upload card\n%%EOF"),
    },
    ...["riplay", "valas1", "valas2"].map((type) => ({
      name: `Rina_${type}.pdf`,
      mimeType: "application/pdf",
      buffer: Buffer.from(`%PDF-1.4\nsynthetic upload ${type}\n%%EOF`),
    })),
  ]);
  await page
    .getByText("2 customer groups · labels are editable before upload")
    .waitFor();
  await page.getByRole("button", { name: "Upload & start processing" }).click();
  await page.waitForURL("http://127.0.0.1:3000/cases");
  await page.getByRole("link", { name: "Poko", exact: true }).click();
  await page
    .getByText("Kertas kerja v1", { exact: false })
    .first()
    .waitFor({ timeout: 45000 });
  await page
    .getByText(
      "DEVELOPMENT FIXTURE · These are synthetic values, not extraction of the uploaded PDF.",
    )
    .waitFor();
  await page.screenshot({
    path: path.join(output, "case-workspace.png"),
    fullPage: true,
  });
  await page
    .getByText("Case context and transaction metadata", { exact: true })
    .click();
  await page
    .getByLabel("customer type", { exact: true })
    .selectOption("INDIVIDUAL");
  await page
    .getByLabel("Reason for annotation", { exact: true })
    .fill("Supplied document indicates individual");
  await page
    .getByLabel("Document / page evidence", { exact: true })
    .fill("Transaction application page 1");
  await page
    .getByRole("button", { name: "Save context and rerun", exact: true })
    .click();
  await page
    .getByText("Kertas kerja v2", { exact: false })
    .first()
    .waitFor({ timeout: 45000 });
  await page.getByRole("button", { name: /SOP findings/ }).click();
  await page.locator(".finding-card").first().waitFor();
  await page.getByRole("link", { name: "Inbox", exact: false }).first().click();
  await page.locator(".inbox-list article").first().waitFor();
  await page.getByRole("link", { name: "Kertas kerja", exact: true }).click();
  await page.getByRole("heading", { name: "Report history" }).waitFor();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "PDF", exact: true }).first().click(),
  ]);
  if (!download.suggestedFilename().endsWith(".pdf"))
    throw new Error("PDF download failed.");
  await download.saveAs(path.join(output, "kertas-kerja.pdf"));
  if (
    !(await readFile(path.join(output, "kertas-kerja.pdf")))
      .subarray(0, 5)
      .equals(Buffer.from("%PDF-"))
  )
    throw new Error("Downloaded report is not a PDF.");
  await page.getByLabel("Branch", { exact: true }).selectOption({ index: 1 });
  const [branchDownload] = await Promise.all([
    page.waitForEvent("download"),
    page
      .getByRole("link", { name: "Download branch XLSX", exact: true })
      .click(),
  ]);
  if (!branchDownload.suggestedFilename().endsWith(".xlsx"))
    throw new Error("Branch workbook download failed");
  await branchDownload.saveAs(path.join(output, "branch-kertas-kerja.xlsx"));
  // Inspect saved case results, not only a success message or download filename.
  for (let attempt = 0; attempt < 90; attempt++) {
    const response = await page.request.get("http://127.0.0.1:3000/api/cases");
    if (!response.ok()) throw new Error("Case result request failed");
    const listing = await response.json();
    evidence.cases = await Promise.all(
      listing.items.map(async (item) => {
        const detail = await page.request.get(
          `http://127.0.0.1:3000/api/cases/${item.id}`,
        );
        if (!detail.ok()) throw new Error("Case detail request failed");
        return detail.json();
      }),
    );
    if (
      evidence.cases.length === 2 &&
      evidence.cases.every(
        (c) =>
          c.reports.length &&
          c.documents.every((d) => d.status === "COMPLETED"),
      )
    )
      break;
    if (attempt === 89)
      throw new Error("Not all seven documents produced saved results/reports");
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  const types = new Set(
    evidence.cases.flatMap((c) => c.documents.map((d) => d.doc_type)),
  );
  if (types.size !== 7)
    throw new Error("Expected all seven registered document types");
  const workbookCheck = spawnSync(
    python,
    [
      "-c",
      `
import sys
from openpyxl import load_workbook
w = load_workbook(sys.argv[1], data_only=True)
assert {"Kertas Kerja", "SOP Details", "Document Quality", "Extracted Fields", "Report Trace"}.issubset(w.sheetnames)
s = w["Kertas Kerja"]
rows = [row for row in s.iter_rows(min_row=12, values_only=True) if isinstance(row[0], (int, float))]
assert len(rows) == 2, (len(rows), "expected two case rows")
assert all(row[3] for row in rows), "missing customer/remitter name"
assert all(value in (None, 0, 1) for row in rows for value in (row[11], row[12], row[13], row[14], row[15], row[16], row[17]))
print("PASS: workbook structure, two case rows, customer names and numeric SOP scores")
`,
      path.join(output, "branch-kertas-kerja.xlsx"),
    ],
    { env, encoding: "utf-8" },
  );
  if (workbookCheck.status !== 0)
    throw new Error(`Workbook content check failed: ${workbookCheck.stderr}`);
  evidence.checks.push(workbookCheck.stdout.trim());
  for (const c of evidence.cases) {
    const report = await page.request.get(
      `http://127.0.0.1:3000/api/reports/${c.reports[0].id}/download?format=json`,
    );
    if (!report.ok()) throw new Error("JSON report download failed");
    await writeFile(
      path.join(output, `${c.customer}-report.json`),
      await report.body(),
    );
  }
  evidence.checks.push(
    "all seven document types completed",
    "two grouped cases persisted",
    "versioned SOP reports saved",
    "PDF signature verified",
    "branch XLSX downloaded",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("http://127.0.0.1:3000/");
  await page.getByRole("heading", { name: "Operations overview" }).waitFor();
  await page.screenshot({
    path: path.join(output, "overview-mobile.png"),
    fullPage: true,
  });
  if (errors.length) throw new Error("Browser errors: " + errors.join("\n"));
  evidence.status = "PASS";
  console.log(
    "PASS: browser login, workbook import/export, typed SOP editor, config replay/publication, bulk grouping, case SOP worker, audited context, versioned reports, inbox, PDF/branch XLSX downloads and mobile rendering.",
  );
} catch (error) {
  evidence.status = "FAIL";
  evidence.error = String(error);
  if (page) {
    await page
      .screenshot({
        path: path.join(output, "failure.png"),
        fullPage: true,
      })
      .catch(() => {});
    console.error(
      await page
        .locator("main")
        .innerText()
        .catch(() => "No main view"),
    );
  }
  console.error(error);
  console.error(logs);
  process.exitCode = 1;
} finally {
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify(evidence, null, 2),
    "utf-8",
  );
  await writeFile(path.join(output, "services.log"), logs, "utf-8");
  if (browser) await browser.close();
  for (const child of children.reverse()) child.kill("SIGTERM");
  await new Promise((resolve) => setTimeout(resolve, 1000));
  for (const child of children)
    if (child.exitCode === null) child.kill("SIGKILL");
}
