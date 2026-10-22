import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'frontend/package.json'));
const {chromium,expect}=require('@playwright/test');
const out=process.env.UI_OUTPUT||path.join(root,'data/field-recovery-ui');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,channel:process.platform==='win32'?'msedge':undefined});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const doc='956d0350-36c5-4642-9471-92f12ef1aad1',caseId='2c9a2036-8606-40a4-9b3d-0d3b21867d2f';
let override=null,posts=[];const errors=[];page.on('pageerror',e=>errors.push(e.message));
// All provider-affecting POST actions are intercepted. This is UI-only verification.
await page.route('**/api/documents/**',async route=>{
 const r=route.request(),url=r.url();
 if(r.method()==='POST'){
  posts.push({url:new URL(url).pathname,body:r.postDataJSON()});
  return route.fulfill({status:503,json:{detail:'UI verification: provider retry intentionally intercepted.'}});
 }
 if(override&&url.endsWith(`/documents/${doc}/reprocess-fields`))return route.fulfill({json:override});
 return route.continue();
});
try{
 await page.goto('http://localhost:3000/login');
 await page.getByLabel('Organization',{exact:true}).fill(process.env.DEV_ORGANIZATION||'sqe');
 await page.getByLabel('Email address',{exact:true}).fill(process.env.DEV_EMAIL||'sqe@bic.local');
 await page.getByLabel('Password',{exact:true}).fill(process.env.DEV_PASSWORD||'P@ssw0rd2026');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('http://localhost:3000/');
 await page.goto(`http://localhost:3000/cases/${caseId}#recovery`);
 const recovery=page.getByRole('region',{name:'Failed field extraction recovery'});
 await expect(recovery).toBeVisible({timeout:15000});
 await expect(recovery).toContainText('gateway could not connect to the model');
 await expect(recovery.getByRole('checkbox')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Resubmit Spider-AI request',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Reconcile provider job',exact:true})).toHaveCount(0);
 await recovery.screenshot({path:path.join(out,'Field_Request_Recovery.png')});
 await recovery.getByRole('button',{name:'Retry field extraction',exact:true}).click();
 await expect(recovery).toContainText('intentionally intercepted');
 if(posts.length!==1||posts[0].body.accept_possible_duplicate_charge!==false||!posts[0].url.endsWith('/retry'))throw Error('Wrong retry action or charge acknowledgment');
 const response=await page.request.get(`http://localhost:3000/api/documents/${doc}/reprocess-fields`);
 override=(await response.json()).map(r=>({...r,requires_duplicate_charge_ack:true,retry_explanation:'',error:'Submission outcome is uncertain.'}));
 await page.reload();await expect(recovery).toBeVisible();
 await expect(recovery.getByRole('button',{name:'Retry field extraction',exact:true})).toBeDisabled();
 await recovery.getByRole('checkbox').check();
 await expect(recovery.getByRole('button',{name:'Retry field extraction',exact:true})).toBeEnabled();
 await recovery.getByRole('button',{name:'Retry field extraction',exact:true}).click();
 await expect(recovery).toContainText('intentionally intercepted');
 if(posts.length!==2||posts[1].body.accept_possible_duplicate_charge!==true)throw Error('Uncertain retry missing acknowledgment');
 if(errors.length)throw Error(errors.join('; '));
 await fs.writeFile(path.join(out,'UI_Verification.json'),JSON.stringify({checks:['Correct field recovery action is visible at the case error','Confirmed connection rejection needs no duplicate-charge acknowledgment','Whole-document and unrelated job recovery actions are hidden','Retry uses the selected-field endpoint and retains the UI on failure','Uncertain submission requires explicit acknowledgment'],browserErrors:errors,interceptedSubmissions:posts.length,realProviderCalls:0},null,2));
 console.log(JSON.stringify({passed:5,browserErrors:errors,realProviderCalls:0}));
}finally{await browser.close();}
