import io
from types import SimpleNamespace
import fitz
import pytest
from app.field_evidence import build_field_evidence, populated_fields


def test_wrapped_value_completeness_does_not_become_an_evidence_field():
    assert list(populated_fields({
        'name': {'raw': 'QA Sample', 'complete': True},
        'complete': False, 'nested': {'complete': True},
    })) == [('name.raw', 'QA Sample'), ('complete', False), ('nested.complete', True)]
    assert list(populated_fields({'name': {'raw': None, 'complete': False}}, include_empty=True)) == [('name.raw', None)]


def setup_doc(monkeypatch):
    objects = {}
    pdf = fitz.open(); page = pdf.new_page(width=600, height=800)
    page.insert_text((60, 100), 'Dirman Siswanto')
    objects['original.pdf'] = pdf.tobytes(); pdf.close()
    class Storage:
        def read(self, key): return objects[key]
        def put(self, key, data, mime): objects[key] = data
    monkeypatch.setattr('app.field_evidence.store', lambda: Storage())
    monkeypatch.setattr('app.field_evidence.original_key', lambda doc: 'original.pdf')
    return SimpleNamespace(org='sqe', branch_id='branch', id='doc', sha256='source', provider_state={}), objects


def citation(page=1, x=50):
    return {'page': page, 'bounding_boxes': [{'x': x, 'y': 70, 'w': 140, 'h': 40}], 'page_dimensions': {'width':600, 'height':800}}


def test_nested_fields_numbers_zero_and_false_are_not_dropped():
    assert list(populated_fields({'party': {'name': 'Dirman', 'missing': None}, 'amount':0, 'checked':False, 'empty':'', 'rows':[{'code':'001'}]})) == [('party.name','Dirman'), ('amount',0), ('checked',False), ('rows.0.code','001')]


def test_extract_citations_produce_real_crops(monkeypatch):
    doc, objects = setup_doc(monkeypatch)
    response = {'id':'extract', 'extract_result':{'customer':{'name':'Dirman Siswanto'}, 'amount':0}, 'extract_metadata':{'field_metadata':{'document_metadata':{'customer':{'name':{'citation':[citation()], 'confidence':.9}}, 'amount':{'citation':[citation(x=220)]}}}}}
    result = build_field_evidence(doc, response)
    assert len(result) == 2
    assert all(e['available'] and e['image_available'] and e['crops'] for e in result)
    assert result[0]['crops'][0]['bbox']['source'] == 'extract'
    assert result[0]['confidence'] == .9
    for item in result:
        image = fitz.Pixmap(objects[item['crops'][0]['storage_key']])
        assert image.width == 280 and image.height == 80


def test_multi_region_and_invalid_boxes(monkeypatch):
    doc, objects = setup_doc(monkeypatch)
    response = {'extract_result':{'address':'Two address lines'}, 'extract_metadata':{'field_metadata':{'document_metadata':{'address':{'citation':[citation(), citation(x=220)]}}}}}
    assert len(build_field_evidence(doc, response)[0]['crops']) == 2
    response['extract_metadata']['field_metadata']['document_metadata']['address']['citation'] = [citation(page=2)]
    result = build_field_evidence(doc, response)[0]
    assert not result['available'] and not result['crops']
    assert result['review_status'] == 'REVIEW'


def test_parse_exact_unique_value_and_ambiguous_repeats(monkeypatch):
    import json
    doc, objects = setup_doc(monkeypatch); doc.provider_state['parse_response_key']='parse.json'
    node = {'type':'text', 'text':'Dirman Siswanto', 'bbox':[{'x':50,'y':70,'w':140,'h':40}]}
    parsed={'items':{'pages':[{'page_number':1,'page_width':600,'page_height':800,'items':[node]}]}}
    objects['parse.json']=json.dumps(parsed).encode()
    response={'extract_result':{'name':'Dirman Siswanto'}}
    result=build_field_evidence(doc,response)[0]
    assert result['available'] and result['review_status']=='REVIEW'
    parsed['items']['pages'][0]['items'].append({**node,'bbox':[{'x':250,'y':70,'w':140,'h':40}]})
    objects['parse.json']=json.dumps(parsed).encode()
    result=build_field_evidence(doc,response)[0]
    assert not result['available'] and result['candidate_count']==2


def test_no_substring_guess_and_manual_override(monkeypatch):
    import json
    doc, objects=setup_doc(monkeypatch);doc.provider_state['parse_response_key']='parse.json'
    objects['parse.json']=json.dumps({'items':{'pages':[{'page_number':1,'page_width':600,'page_height':800,'items':[{'text':'Customer label Dirman Siswanto extra prose','bbox':[{'x':50,'y':70,'w':140,'h':40}]}]}]}}).encode()
    response={'extract_result':{'name':'Dirman Siswanto'}}
    assert not build_field_evidence(doc,response)[0]['available']
    response['extract_metadata']={'visual_evidence':{'name':{'page_number':1,'bbox':[.1,.1,.4,.2],'units':'normalized','reviewed_by':'reviewer'}}}
    result=build_field_evidence(doc,response)[0]
    assert result['available'] and result['review_status']=='REVIEWED'


def test_existing_document_refresh_and_manual_region_use_saved_results(signed, monkeypatch):
    from sqlalchemy import select, func
    from app.db import Document, Job, SessionLocal
    from app.storage import original_key, store
    from test_platform import publish_fixture, upload, process_all
    publish_fixture(signed)
    cid=upload(signed,names=('Dirman_ektp.pdf',),template='custom').json()['case_ids'][0]
    process_all()
    with SessionLocal.begin() as db:
        doc=db.scalar(select(Document)); did=doc.id
        before=doc.raw.copy()
        jobs=db.scalar(select(func.count()).select_from(Job))
        pdf=fitz.open();pdf.new_page(width=600,height=800)
        store().put(original_key(doc),pdf.tobytes(),'application/pdf');pdf.close()
        doc.metadata_json={'field_metadata':{'document_metadata':{'nik':{'citation':[citation()]}}}}
    def paid_call(*args, **kwargs): raise AssertionError('Must not rerun provider')
    monkeypatch.setattr('app.processor.run_provider',paid_call)
    response=signed.post(f'/api/documents/{did}/field-evidence')
    assert response.status_code==202,response.text
    data=signed.get(f'/api/cases/{cid}').json()['documents'][0]
    evidence=next(e for e in data['validation']['field_evidence'] if e['field']=='nik')
    assert evidence['image_available'] and data['validation']['fields']['nik']['image_available']
    crop=evidence['crops'][0];name=crop['storage_key'].split('/')[-1]
    image_id=name[len(crop['revision'])+1:-4]
    image=signed.get(f'/api/documents/{did}/evidence/{crop["revision"]}/{image_id}')
    assert image.status_code==200 and image.content.startswith(b'\x89PNG')
    response=signed.post(f'/api/documents/{did}/visual-box',json={'field':'nik','page_number':1,'bbox':[.1,.1,.4,.2],'reason':'Verified source region.'})
    assert response.status_code==202,response.text
    with SessionLocal() as db:
        doc=db.get(Document,did)
        assert doc.raw==before
        assert db.scalar(select(func.count()).select_from(Job))==jobs
        assert next(e for e in doc.validation['field_evidence'] if e['field']=='nik')['review_status']=='REVIEWED'


def test_wrapper_spatial_location_yields_one_value_crop(monkeypatch):
    doc, objects = setup_doc(monkeypatch)
    response = {'extract_result': {
        'place': {'raw': 'Jakarta', 'complete': True},
        'empty': {'raw': None, 'complete': False},
        '_field_locations': [
            {'field': name, 'page_number': 1, 'box_2d': [100, 100, 200, 400]}
            for name in ['place', 'empty']
        ],
    }}
    evidence = build_field_evidence(doc, response)
    assert len(evidence) == 1
    assert evidence[0]['field'] == 'place'
    assert evidence[0]['value'] == 'Jakarta'
    assert evidence[0]['available']
    assert len(evidence[0]['crops']) == 1
