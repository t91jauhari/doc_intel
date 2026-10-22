from copy import deepcopy
from types import SimpleNamespace
import fitz
import pytest

from app.spatial_grounding import normalize_response, append_instruction, SPATIAL_INSTRUCTION, spatial_schema
from app.spider_extraction import combine_pages
from app.field_evidence import build_field_evidence
from app.evidence import build_evidence


def test_inline_and_sidecar_preserve_business_values_and_coordinate_order():
    original = {"extract_result": {"name": {"value": "00123", "page_number": 1, "box_2d": [100,200,300,400]}, "party": {"city": "Jakarta"}, "_field_locations":[{"field":"party.city","page_number":2,"box_2d":[10,20,30,40]}]}}
    before = deepcopy(original)
    result = normalize_response(original)
    assert original == before
    assert result["extract_result"] == {"name":"00123","party":{"city":"Jakarta"}}
    assert result["extract_metadata"]["spatial_evidence"]["name"][0]["bbox"] == [.2,.1,.4,.3]
    assert normalize_response(result) == result
    assert append_instruction(append_instruction("Read faithfully." )).count(SPATIAL_INSTRUCTION) == 1
    schema = {"type":"object","properties":{"name":{"type":"string"}}}
    assert "_field_locations" in spatial_schema(schema)["properties"]
    assert "_field_locations" not in schema["properties"]


@pytest.mark.parametrize("box", [[400,200,300,400],[-1,0,10,10],[0,0,1001,10],[True,0,10,10],[0,0,float('nan'),10],[1,2,3]])
def test_invalid_boxes_never_become_crops(box):
    result = normalize_response({"extract_result":{"name":"Text","_field_locations":[{"field":"name","page_number":1,"box_2d":box}]}})
    assert not result["extract_metadata"]["spatial_evidence"]
    assert result["extract_metadata"]["spatial_errors"]["name"]


def test_page_merge_does_not_merge_coordinate_arrays_or_guess_pages():
    pages = [{"page_number": n,"result":{"name":"Same", "rows":[{"code":str(n)}],"_field_locations":[{"field":"name","box_2d":[n*10,20,30+n*10,100]}, {"field":"rows.0.code","box_2d":[100,200,300,400]}]}} for n in [1,2]]
    raw, conflicts = combine_pages(pages)
    assert not conflicts
    result = normalize_response({"extract_result":raw})
    assert {k:v for k,v in result["extract_result"].items() if k != "page_results"} == {"name":"Same","rows":[{"code":"1"},{"code":"2"}]}
    boxes = result["extract_metadata"]["spatial_evidence"]
    assert [b["page_number"] for b in boxes["name"]] == [1,2]
    assert boxes["rows.1.code"][0]["page_number"] == 2
    # Cross-page references must not leak a previous page's box.
    pages[1]["result"]["_field_locations"][0]["page_number"] = 1
    raw,_ = combine_pages(pages)
    assert normalize_response({"extract_result":raw})["extract_metadata"]["spatial_errors"]["name"]


def test_null_and_absent_visual_fields_have_no_box():
    result = normalize_response({"extract_result":{"name":None,"customer_signature":{"present":False,"page_number":1,"box_2d":[10,10,20,20]},"_field_locations":[{"field":"name","page_number":1,"box_2d":[10,10,20,20]}]}})
    assert not result["extract_metadata"]["spatial_evidence"]


def test_actual_crops_use_physical_source_page_and_stay_unreviewed(monkeypatch):
    pdf = fitz.open()
    for color in [(1,0,0),(0,0,1)]:
        page = pdf.new_page(width=600,height=800)
        page.draw_rect(fitz.Rect(60,80,180,160),color=color,fill=color)
    objects = {"source.pdf":pdf.tobytes()}; pdf.close()
    class Storage:
        def read(self,key): return objects[key]
        def put(self,key,data,mime): objects[key]=data
    for module in ["app.field_evidence","app.evidence"]:
        monkeypatch.setattr(module+".store",lambda:Storage())
        monkeypatch.setattr(module+".original_key",lambda doc:"source.pdf")
    doc = SimpleNamespace(org="sqe",branch_id="branch",id="doc",sha256="source",provider_state={})
    response = {"id":"extract-1","extract_result":{"name":"Blue", "customer_signature":{"present":True,"page_number":2},"_field_locations":[{"field":field,"page_number":2,"box_2d":[100,100,200,300]} for field in ["name","customer_signature"]]}}
    fields = build_field_evidence(doc,response)
    assert len(fields) == 1 and fields[0]["field"] == "name"
    crop = fields[0]["crops"][0]
    image = fitz.Pixmap(objects[crop["storage_key"]])
    assert (image.width,image.height) == (240,160)
    assert image.pixel(100,80)[:3] == (0,0,255)
    assert fields[0]["review_status"] == "PENDING"
    visual = build_evidence(doc,response)
    assert visual[0]["available"] and visual[0]["page_number"] == 2
    assert visual[0]["review_status"] == "PENDING"
    response["extract_result"]["_field_locations"][0]["page_number"] = 99
    invalid = build_field_evidence(doc,response)[0]
    assert not invalid["available"] and "bounds" in invalid["error"]


def test_selected_field_run_regenerates_only_its_crops(signed, monkeypatch):
    from test_field_reprocessing import completed
    from app.db import SessionLocal, Document
    from app.storage import original_key, store
    from app.processor import process_job
    doc = completed(signed)
    pdf = fitz.open(); page = pdf.new_page(width=600,height=800)
    page.insert_text((60,100),"NEW NAME")
    store().put(original_key(doc),pdf.tobytes(),"application/pdf"); pdf.close()
    sentinel = {"field":"nik","revision":"keep-original","available":False,"image_available":False,"crops":[]}
    with SessionLocal.begin() as db:
        record = db.get(Document,doc.id)
        record.validation = {**record.validation,"field_evidence":[sentinel]}
    grounded = normalize_response({"extract_result":{"name":{"raw":"NEW NAME","complete":True},"_field_locations":[{"field":"name.raw","page_number":1,"box_2d":[100,100,150,300]}]}})
    patch = {**grounded["extract_result"],"_spatial_metadata":grounded["extract_metadata"]}
    monkeypatch.setattr("app.field_reprocessing.extract_selected",lambda *args:deepcopy(patch))
    request = signed.post(f"/api/documents/{doc.id}/reprocess-fields",json={"fields":["name"],"reason":"Read the original name line"})
    assert request.status_code == 202, request.text
    process_job(request.json()["job_id"])
    with SessionLocal() as db:
        record = db.get(Document,doc.id)
        assert record.status == "COMPLETED", record.error
        from app.db import Job
        assert db.get(Job,request.json()["job_id"]).status == "COMPLETED", db.get(Job,request.json()["job_id"]).error
        assert record.raw["name"]["raw"] == "NEW NAME"
        assert "_spatial_metadata" not in record.raw
        evidence = record.validation["field_evidence"]
        assert next(e for e in evidence if e["field"] == "nik") == sentinel
        assert next(e for e in evidence if e["field"] == "name.raw")["available"]
        assert record.metadata_json["spatial_evidence"]["name.raw"]


def test_prior_page_context_excludes_coordinates():
    from app.spider_extraction import reference_text
    text = reference_text([{"page_number":1,"result":{"name":"Visible name","_field_locations":[{"field":"name","page_number":1,"box_2d":[10,20,30,40]}]}}])
    assert "Visible name" in text
    assert "box_2d" not in text and "_field_locations" not in text
