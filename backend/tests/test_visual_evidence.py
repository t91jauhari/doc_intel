import io
from types import SimpleNamespace
import fitz
import pytest
from PIL import Image
from app.evidence import rectangle, build_evidence, apply_evidence_review
from app.storage import original_key, store

def original():
    pdf=fitz.open();page=pdf.new_page(width=200,height=300)
    page.draw_rect(fitz.Rect(100,200,180,280),color=(1,0,0),fill=(1,0,0))
    return pdf.tobytes()

def test_crop_is_real_source_region_and_preserves_observation():
    doc=SimpleNamespace(org='sqe',branch_id='b',id='visual-test',sha256='source',provider_state={})
    store().put(original_key(doc),original(),'application/pdf')
    response={'id':'ext-1','extract_result':{'customer_signature':{'present':True,'page_number':1}},'extract_metadata':{'visual_evidence':{'customer_signature':{'page_number':1,'bbox':[.5,2/3,.9,14/15],'units':'normalized'}}}}
    evidence=build_evidence(doc,response)
    assert evidence[0]['available'] and evidence[0]['observed_present'] is True
    image=Image.open(io.BytesIO(store().read(evidence[0]['storage_key'])))
    assert image.size==(160,160)
    assert image.getpixel((80,80))==(255,0,0)
    response['extract_metadata']={}
    missing=build_evidence(doc,response)
    assert missing[0]['available'] is False and missing[0]['observed_present'] is True
    report=apply_evidence_review({'status':'PASS','fields':{'customer_signature':{'status':'PASS','issues':[]}}},missing)
    assert report['status']=='REVIEW'
    assert report['fields']['customer_signature']['issues'][0]['code']=='CROP_EVIDENCE_REQUIRED'

@pytest.mark.parametrize('box',[
 {'bbox':[0,0,1,1]}, {'bbox':[0,0,2,1],'units':'normalized'},
 {'bbox':[1,0,0,1],'units':'normalized'}, {'bbox':[0,0,float('nan'),1],'units':'normalized'},
 {'bbox':[0,0,10,10],'units':'pixels'},
])
def test_invalid_coordinates_are_rejected(box):
    with fitz.open(stream=original(),filetype='pdf') as pdf:
        with pytest.raises(ValueError): rectangle(box,pdf[0])

def test_initial_crops_include_every_observed_page():
    doc=SimpleNamespace(org='sqe',branch_id='b',id='initial-test',sha256='source',provider_state={})
    response={'extract_result':{'page_initials':{'pages':[{'page_number':n,'footer_present':True} for n in range(1,5)]}},'extract_metadata':{}}
    assert len(build_evidence(doc,response))==4

def test_failed_storage_is_not_misreported_as_missing_box(monkeypatch):
    doc=SimpleNamespace(org='sqe',branch_id='b',id='io-test',sha256='source',provider_state={})
    monkeypatch.setattr(store(),'read',lambda key: (_ for _ in ()).throw(IOError('offline')))
    response={'extract_result':{'customer_signature':{'present':True}},'extract_metadata':{'visual_evidence':{'customer_signature':{'page_number':1,'bbox':[0,0,1,1],'units':'normalized'}}}}
    with pytest.raises(IOError):build_evidence(doc,response)

def test_prefix_filename_routing_and_alias_batch_grouping(signed):
    from app.domain import route, default_config
    from test_platform import publish_fixture, PDF
    cfg=default_config()
    assert route('(Compressed)Form Riplay-Langit R.pdf',cfg)[:2]==('riplay','Langit R')
    assert route('EKTP Langit Raharja.pdf',cfg)[:2]==('ektp','Langit Raharja')
    assert route('Surat Pernyataan Pembelian Valas-Sri P.pdf',cfg)[:2]==('unknown','Sri P')
    settings=signed.get('/api/config').json();settings['payload']['provider']='fixture';settings['payload']['customer_aliases']={'Langit R':'Langit Raharja'}
    assert signed.post('/api/config/publish',json={'expected_version':settings['version'],'payload':settings['payload']}).status_code==200
    branch=signed.get('/api/branches').json()[0]['id']
    response=signed.post('/api/uploads',data={'branch_id':branch,'template':'custom'},files=[('files',(name,PDF,'application/pdf')) for name in ['Form Riplay-Langit R.pdf','EKTP Langit Raharja.pdf']],headers={'Idempotency-Key':'aliases'})
    assert response.status_code==202 and len(response.json()['case_ids'])==1


def test_assignment_scope_and_due_dates(signed):
    from test_platform import publish_fixture,upload
    publish_fixture(signed)
    cid=upload(signed,names=('test_transaction.pdf',),template='custom').json()['case_ids'][0]
    assignment=signed.get(f'/api/cases/{cid}/assignment').json()
    uid=assignment['candidates'][0]['id']
    assert signed.put(f'/api/cases/{cid}/assignment',json={'assigned_to':'unknown','due_at':100}).status_code==422
    assert signed.put(f'/api/cases/{cid}/assignment',json={'assigned_to':uid,'due_at':100}).status_code==200
    updated=signed.get(f'/api/cases/{cid}/assignment').json()
    assert updated['assigned_to']==uid and updated['due_at']==100


def test_missing_crops_block_release_even_with_confirmed_sop(signed):
    from test_platform import publish_fixture,upload,process_all
    publish_fixture(signed)
    cid=upload(signed,names=('test_transaction.pdf',),template='custom').json()['case_ids'][0]
    process_all()
    detail=signed.get(f'/api/cases/{cid}').json()
    assert detail['status']=='NEEDS_REVIEW'
    assert any(not e['available'] for d in detail['documents'] for e in d['validation']['visual_evidence'])


def test_crops_and_pages_require_document_access(signed):
    from test_platform import publish_fixture,upload
    from app.db import SessionLocal, Document
    from sqlalchemy import select
    publish_fixture(signed)
    cid=upload(signed,names=('test_transaction.pdf',),template='custom').json()['case_ids'][0]
    with SessionLocal.begin() as db:
        doc=db.scalar(select(Document).where(Document.case_id==cid));did=doc.id;doc.org='another-bank'
    assert signed.get(f'/api/documents/{did}/pages/1').status_code==404
    assert signed.get(f'/api/documents/{did}/evidence/revision/image').status_code==404

def test_rotation_uses_displayed_page_coordinates():
    pdf=fitz.open();page=pdf.new_page(width=200,height=300)
    page.draw_rect(fitz.Rect(100,200,180,280),color=(1,0,0),fill=(1,0,0));page.set_rotation(90)
    doc=SimpleNamespace(org='sqe',branch_id='b',id='rotated',sha256='source',provider_state={})
    store().put(original_key(doc),pdf.tobytes(),'application/pdf')
    # Rotate original red box to displayed coordinates: x=20..100, y=100..180.
    response={'extract_result':{'customer_signature':True},'extract_metadata':{'visual_evidence':{'customer_signature':{'page_number':1,'bbox':[20/300,.5,100/300,.9],'units':'normalized'}}}}
    evidence=build_evidence(doc,response)
    image=Image.open(io.BytesIO(store().read(evidence[0]['storage_key'])))
    assert image.getpixel((image.width//2,image.height//2))==(255,0,0)


def test_context_conflicts_are_suggestions_not_effective_values():
    from app.case_context import suggestions
    docs=[SimpleNamespace(status='COMPLETED',doc_type=kind,id=str(i)) for i,kind in enumerate(['valas_declaration_1','valas_declaration_2'])]
    values=suggestions(docs)
    assert all(x['conflict'] and x['requires_acceptance'] for x in values)

def test_visual_box_review_is_audited_and_does_not_replace_raw(signed):
    from test_platform import publish_fixture,upload,process_all
    from app.db import SessionLocal,Document
    from sqlalchemy import select
    from copy import deepcopy
    publish_fixture(signed)
    cid=upload(signed,names=('crop_transaction.pdf',),template='custom').json()['case_ids'][0]
    process_all()
    with SessionLocal() as db:
        doc=db.scalar(select(Document).where(Document.case_id==cid));did=doc.id;before=deepcopy(doc.raw)
        store().put(original_key(doc),original(),'application/pdf')
    bad=signed.post(f'/api/documents/{did}/visual-box',json={'field':'customer_signature','page_number':1,'bbox':[0,0,2,1],'reason':'Inspected original document'})
    assert bad.status_code==422
    response=signed.post(f'/api/documents/{did}/visual-box',json={'field':'customer_signature','page_number':1,'bbox':[.5,2/3,.9,14/15],'reason':'Customer signer region inspected'})
    assert response.status_code==202,response.text
    detail=signed.get(f'/api/cases/{cid}').json()
    updated=detail['documents'][0]
    assert updated['raw']==before
    e=next(e for e in updated['validation']['visual_evidence'] if e['field']=='customer_signature')
    assert e['available'] and e['review_status']=='REVIEWED'
    image_id=e['storage_key'].rsplit('/',1)[1][len(e['revision'])+1:-4]
    downloaded=signed.get(f'/api/documents/{did}/evidence/{e["revision"]}/{image_id}')
    assert downloaded.status_code==200 and downloaded.content.startswith(b'\x89PNG')
    assert signed.get(f'/api/documents/{did}/pages/1').status_code==200
