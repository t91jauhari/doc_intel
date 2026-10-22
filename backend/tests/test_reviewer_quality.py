import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from app.domain import default_config, validate_config
from app.extraction_quality import apply_quality
from app.value_display import display_value

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from run_field_regression import score

def test_reviewer_rules_are_idempotent_and_keep_schema_contract():
    original=default_config();before=copy.deepcopy(original)
    cfg=apply_quality(original)
    assert original==before
    assert apply_quality(cfg)==cfg
    validate_config(cfg)
    text=str(cfg['profiles']['riplay']['schema']['properties']['customer_name'])
    assert 'parenthesized' in text and 'autograph' in text
    assert 'Sri Pujianty' not in text and 'marcel' not in text
    invoice=cfg['profiles']['invoice']['schema']['properties']
    assert 'SOLD TO' in invoice['ship_to_name']['description']
    assert 'quantity 1' in invoice['unit_price']['description']
    assert 'GRAND TOTAL' in invoice['shipping_handling']['description']

def test_combined_display_keeps_fee_and_other_description():
    fee={'selected':['DEBIT REKENING/ Debit A/C'],'raw':'$ 30,00','currency':'$'}
    assert display_value(fee)=='DEBIT REKENING/ Debit A/C · $ 30,00'
    assert display_value({'selected':['Lainnya Other'],'other_description':'Pembelian Valas'})=='Lainnya Other · Pembelian Valas'
    assert display_value({'selected':[],'raw':'0','currency':'USD'})=='USD 0'
    assert display_value({'selected':[]})=='None selected'

def test_charge_and_other_comparison_requires_the_whole_value():
    fee={'selected':['DEBIT REKENING/ Debit A/C'],'raw':'$ 30,00','currency':'$'}
    assert score('Debit Rekening/ $30',fee,'charges')=='Valid (same result)'
    assert score('Debit Rekening/ $40',fee,'charges')=='Invalid (different value)'
    assert score('Tunai/ $30',fee,'charges')=='Invalid (different value)'
    assert score('Debit Rekening/ $30',{'selected':['DEBIT REKENING/ Debit A/C'],'raw':None},'charges')=='Invalid (different value)'
    assert score('Lainnya – Pembelian Valas',{'selected':['Lainnya Other'],'other_description':'Pembelian Valas'},'transaction_type')=='Valid (same result)'
    assert score('Lainnya – Pembelian Valas',{'selected':['Lainnya Other'],'other_description':None},'transaction_type')=='Invalid (different value)'
    assert score('USD 280,800',{'amount_raw':'280.800','currency_raw':'USD'},'subtotal_all_items')=='Valid (same result)'
    assert score('USD 280,800',{'amount_raw':'280.801','currency_raw':'USD'},'subtotal_all_items')=='Invalid (different value)'
    assert score('1.00','100','amount')=='Invalid (different value)'

def test_detail_images_are_real_bounded_original_page_crops(monkeypatch):
    import base64
    import fitz
    from app import field_detail_images as detail
    with fitz.open() as pdf:
        page=pdf.new_page(width=600,height=800)
        page.insert_text((100,120),'Original handwriting region')
        data=pdf.tobytes()
    monkeypatch.setattr(detail,'store',lambda:SimpleNamespace(read=lambda key:data))
    monkeypatch.setattr(detail,'original_key',lambda doc:'original')
    beats=[]
    images=detail.detail_images(SimpleNamespace(doc_type='application'),['beneficiary_account_number'],1,lambda:beats.append(1))
    assert len(images)==2 and len(beats)==1
    assert 'SAME original physical page 1' in images[0]['text']
    jpeg=base64.b64decode(images[1]['image_url']['url'].split(',')[1])
    assert jpeg.startswith(b'\xff\xd8') and len(jpeg)<=180000
    assert detail.detail_images(SimpleNamespace(doc_type='ektp'),['name'],1,lambda:None)==[]
