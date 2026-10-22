const { chromium } = require('playwright-core');
const fs = require('fs');
const EXE = process.env.CHROME_EXE;
(async () => {
  const b = await chromium.launch({ executablePath: EXE });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  let page = await ctx.newPage();
  const issues = [];
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + String(e).slice(0, 300)));
  page.on('requestfailed', r => { if (!r.url().includes('_next')) consoleErrors.push('REQFAIL: ' + r.method() + ' ' + r.url() + ' :: ' + (r.failure() || {}).errorText); });
  page.setDefaultTimeout(30000);

  const out = (s) => console.log(s);

  // ---------- 1. Login page ----------
  await page.goto('http://localhost:3000/login');
  await page.waitForLoadState('networkidle');
  out('LOGIN page loaded, title=' + (await page.title()));
  const filledBtns = await page.evaluate(() => {
    return [...document.querySelectorAll('button')].map(b => {
      const cs = getComputedStyle(b);
      return { text: (b.textContent || '').trim().slice(0, 40), bg: cs.backgroundColor, disabled: b.disabled };
    });
  });
  out('LOGIN buttons: ' + JSON.stringify(filledBtns));

  // ---------- 2. Login with credentials ----------
  const emailSel = 'input[name="email"], input[type="email"], input#email';
  if (await page.locator(emailSel).count()) await page.fill(emailSel, 'sqe@bic.local');
  else await page.locator('input').first().fill('sqe@bic.local');
  await page.fill('input[type="password"]', 'P@ssw0rd2026');
  await page.screenshot({ path: 'e2e/01-login-filled.png', fullPage: true });
  const loginBtn = page.locator('button[type="submit"]').first();
  if (await loginBtn.count()) await loginBtn.click();
  else await page.locator('button').last().click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);
  out('AFTER LOGIN url=' + page.url());
  await page.screenshot({ path: 'e2e/02-after-login.png', fullPage: true });

  // ---------- 3. Overview ----------
  const overviewFilled = await page.evaluate(() => {
    return [...document.querySelectorAll('button')].filter(b => {
      const bg = getComputedStyle(b).backgroundColor;
      return bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent' && !b.disabled;
    }).map(b => ({ t: (b.textContent || '').trim().slice(0, 30), bg: getComputedStyle(b).backgroundColor }));
  });
  out('OVERVIEW filled buttons: ' + JSON.stringify(overviewFilled));
  await page.screenshot({ path: 'e2e/03-overview.png', fullPage: true });

  // ---------- 4. Upload ----------
  await page.goto('http://localhost:3000/upload');
  await page.waitForLoadState('networkidle');
  out('UPLOAD url=' + page.url());
  await page.screenshot({ path: 'e2e/04-upload.png', fullPage: true });
  const dir = 'C:/Users/pc/Documents/Codex/2026-10-15/ex/outputs/ACCOP All PDFs';
  const files = fs.readdirSync(dir).filter(f => f.toLowerCase().endsWith('.pdf')).map(f => dir + '/' + f);
  out('FILES to upload: ' + files.length);
  const fileInputs = await page.locator('input[type="file"]').count();
  out('UPLOAD file inputs: ' + fileInputs);
  if (fileInputs === 0) issues.push('UPLOAD: no file input found on /upload page');
  await page.locator('input[type="file"]').first().setInputFiles(files);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'e2e/05-upload-files-selected.png', fullPage: true });
  const uploadBtns = await page.evaluate(() => [...document.querySelectorAll('button')].map(b => ({ t: (b.textContent || '').trim().slice(0, 40), dis: b.disabled })));
  out('UPLOAD buttons: ' + JSON.stringify(uploadBtns));
  if (!uploadBtns.some(b => b.t === 'Confirm grouping')) issues.push('UPLOAD: grouping dialog did not open after file selection');

  // Assign every unresolved doc to its first suggested candidate via the select
  for (let round = 0; round < 40; round++) {
    const done = await page.evaluate(() => {
      const selects = [...document.querySelectorAll('.grouping-card select')];
      let changed = false;
      for (const sel of selects) {
        if (sel.value === '') {
          const opt = [...sel.options].find(o => o.value.trim() !== '');
          if (opt) {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
            setter.call(sel, opt.value);
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            changed = true;
            break; // one per pass so React re-renders
          }
        }
      }
      const confirm = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Confirm grouping');
      return { changed, confirmEnabled: confirm ? !confirm.disabled : false };
    });
    if (!done.changed && done.confirmEnabled) break;
    await page.waitForTimeout(300);
  }
  const unassignedLeft = await page.evaluate(() => {
    const p = [...document.querySelectorAll('p')].find(x => /unassigned\./.test(x.textContent));
    return p ? p.textContent.match(/(\d+) unassigned/)?.[1] : '?';
  });
  out('UPLOAD unassigned left before confirm: ' + unassignedLeft);
  await page.screenshot({ path: 'e2e/05b-grouping-resolved.png', fullPage: true });
  await page.click('button:has-text("Confirm grouping")');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'e2e/05c-grouping-confirmed.png', fullPage: true });
  const startBtn = page.locator('button:has-text("Upload & start processing")');
  if (await startBtn.isDisabled()) {
    issues.push('UPLOAD: "Upload & start processing" still disabled after confirming grouping');
    out('UPLOAD page text after confirm: ' + (await page.evaluate(() => document.body.innerText.slice(0, 1200))).replace(/\n+/g, ' | '));
  } else {
    await startBtn.click();
    out('UPLOAD started');
  }
  await page.waitForTimeout(8000);
  await page.screenshot({ path: 'e2e/06-upload-after-start.png', fullPage: true });
  out('UPLOAD after start body: ' + (await page.evaluate(() => document.body.innerText.slice(0, 800))).replace(/\n+/g, ' | '));
  fs.writeFileSync('e2e/state.json', JSON.stringify({ phase: 'upload-started' }));

  // Part 2 continues below (same IIFE): fresh login, poll ingestion, walk pages.
  const b2 = await chromium.launch({ executablePath: EXE });
  const ctx2B = await b2.newContext({ viewport: { width: 1440, height: 900 } });
  page = await ctx2B.newPage();
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + String(e).slice(0, 300)));
  page.setDefaultTimeout(30000);
  await page.goto('http://localhost:3000/login');
  await page.fill('input[type="email"], input[name="email"]', 'sqe@bic.local');
  await page.fill('input[type="password"]', 'P@ssw0rd2026');
  await page.locator('button:has-text("Sign in")').first().click();
  await page.waitForLoadState('networkidle');
  out('PART2 login done, url=' + page.url());

  // ---------- 5. Poll for ingestion completion ----------
  let poll = 0, docSummary = null;
  while (poll++ < 60) {
    await page.waitForTimeout(10000);
    const r = await page.evaluate(async () => {
      const res = await fetch('/api/documents', { credentials: 'include' });
      if (!res.ok) return { err: res.status };
      return await res.json();
    });
    if (r && !r.err) {
      const arr = Array.isArray(r) ? r : (r.items || r.documents || []);
      const counts = {};
      for (const d of arr) { const s = d.status || d.state || '?'; counts[s] = (counts[s] || 0) + 1; }
      docSummary = { total: arr.length, counts };
      out('POLL ' + poll + ' docs=' + JSON.stringify(docSummary));
      const active = ['PENDING', 'PROCESSING', 'UPLOADING', 'QUEUED', 'PARSING', 'CLASSIFYING'].some(s => counts[s]);
      if (!active && arr.length >= 33) break;
    } else { out('POLL ' + poll + ' /api/documents -> ' + JSON.stringify(r)); break; }
  }
  out('FINAL doc summary: ' + JSON.stringify(docSummary));
  await page.screenshot({ path: 'e2e/07-upload-final.png', fullPage: true });

  // ---------- 6. Cases list ----------
  await page.goto('http://localhost:3000/cases');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  out('CASES text: ' + (await page.evaluate(() => document.body.innerText.slice(0, 1500))).replace(/\n+/g, ' | '));
  await page.screenshot({ path: 'e2e/08-cases.png', fullPage: true });

  // ---------- 7. Inbox ----------
  await page.goto('http://localhost:3000/inbox');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  out('INBOX text: ' + (await page.evaluate(() => document.body.innerText.slice(0, 1200))).replace(/\n+/g, ' | '));
  await page.screenshot({ path: 'e2e/09-inbox.png', fullPage: true });

  // ---------- 8. Open first case ----------
  await page.goto('http://localhost:3000/cases');
  await page.waitForTimeout(2000);
  const firstCase = page.locator('a[href^="/cases/"]').first();
  if (await firstCase.count()) {
    const href = await firstCase.getAttribute('href');
    out('OPEN case: ' + href);
    await page.goto('http://localhost:3000' + href);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2500);
    out('CASE detail text: ' + (await page.evaluate(() => document.body.innerText.slice(0, 2500))).replace(/\n+/g, ' | '));
    await page.screenshot({ path: 'e2e/10-case-detail.png', fullPage: true });
  } else issues.push('CASES: no case links found');

  // ---------- 9. Settings ----------
  await page.goto('http://localhost:3000/settings');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'e2e/11-settings.png', fullPage: true });
  out('SETTINGS text: ' + (await page.evaluate(() => document.body.innerText.slice(0, 800))).replace(/\n+/g, ' | '));

  out('\n=== CONSOLE/NETWORK ERRORS (' + consoleErrors.length + ') ===');
  for (const e of consoleErrors.slice(0, 40)) out('  ' + e);
  out('\n=== ISSUES (' + issues.length + ') ===');
  for (const i of issues) out('  - ' + i);
  await b2.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
