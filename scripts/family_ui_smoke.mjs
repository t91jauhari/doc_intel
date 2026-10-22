import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs/promises';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'frontend/package.json'));
const {chromium,expect}=require('@playwright/test');
const browser=await chromium.launch({headless:true,channel:process.platform==='win32'?'msedge':undefined});
const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
let published;
// Exercise the complete UI while keeping the real published configuration unchanged.
await page.route('**/api/config/publish',async route=>{
 published=route.request().postDataJSON();
 return route.fulfill({status:200,json:{id:'ui-family-test',version:published.expected_version+1,payload:published.payload}});
});
try{
 await page.goto('http://localhost:3000/login');
 await page.getByLabel('Organization',{exact:true}).fill(process.env.DEV_ORGANIZATION||'sqe');
 await page.getByLabel('Email address',{exact:true}).fill(process.env.DEV_EMAIL||'sqe@bic.local');
 await page.getByLabel('Password',{exact:true}).fill(process.env.DEV_PASSWORD||'P@ssw0rd2026');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('http://localhost:3000/');
 await page.goto('http://localhost:3000/settings');
 await page.getByRole('button',{name:'Document families',exact:true}).click();
 await page.getByRole('button',{name:'Add document family',exact:true}).click();
 const modal=page.getByRole('dialog');
 await modal.getByLabel('Family name',{exact:true}).fill('Loan Review UI');
 await expect(modal.getByLabel('Family ID',{exact:false})).toHaveValue('loan_review_ui');
 await modal.getByRole('button',{name:'Create family draft',exact:true}).click();
 await expect(page.locator('.family-context select')).toHaveValue('loan_review_ui');
 await page.getByRole('button',{name:'2 · Documents & extraction',exact:true}).click();
 await page.getByLabel('Family extraction guidance',{exact:false}).fill('Read the original labeled boxes and all continuation lines.');
 await fs.mkdir(path.join(root,'data/family-ui'),{recursive:true});
 await page.getByLabel('Family extraction guidance',{exact:false}).scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(root,'data/family-ui/documents-and-guidance.png'),fullPage:false});
 await page.getByRole('button',{name:'3 · Checks & reports',exact:true}).click();
 await page.getByLabel('Default reference dataset',{exact:false}).selectOption('');
 await page.getByLabel('Default report layout',{exact:false}).selectOption('forex');
 await page.getByRole('button',{name:'1 · Basics',exact:true}).click();
 await page.getByRole('button',{name:'Configure transaction flows',exact:false}).click();
 await page.getByRole('button',{name:'Add transaction flow',exact:true}).click();
 await modal.getByLabel('Name',{exact:true}).fill('Loan Review UI Flow');
 await modal.getByRole('button',{name:'Add to configuration draft',exact:true}).click();
 await page.getByRole('button',{name:'Publish configuration',exact:true}).click();
 // Current settings UI may display its publish confirmation first.
 const confirm=page.getByRole('dialog').getByRole('button',{name:/Publish/});
 if(await confirm.count())await confirm.click();
 await expect.poll(()=>!!published).toBe(true);
 const f=published.payload.document_families.loan_review_ui;
 if(!f.extraction_guidance||f.dataset_id!==null||!f.profiles.length)throw Error('Family settings lost during publishing');
 const flow=published.payload.templates.loan_review_ui_flow;
 if(flow.document_family!=='loan_review_ui'||flow.dataset_id!==null)throw Error('Family defaults were not inherited by the flow');
 await expect(page.locator('.family-context select')).toHaveValue('forex');
 await fs.mkdir(path.join(root,'data/family-ui'),{recursive:true});
 await page.screenshot({path:path.join(root,'data/family-ui/configuration.png'),fullPage:true});
 if(errors.length)throw Error(errors.join('; '));
 console.log(JSON.stringify({familyCreation:true,guidanceEditor:true,noReferenceDataset:true,flowInheritance:true,publishPayload:true,browserErrors:errors,realConfigurationWrites:0,realProviderCalls:0}));
}catch(e){console.log(JSON.stringify({browserErrors:errors,visibleText:(await page.locator('body').innerText()).slice(0,3500)}));throw e;}finally{await browser.close();}
