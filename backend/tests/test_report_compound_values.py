import copy
import io
from types import SimpleNamespace
from openpyxl import load_workbook
from app.db import Report, SessionLocal
from sqlalchemy import select
from app.reporting import make_report
from app.kertas_kerja import excel_value
from test_platform import publish_fixture, upload, process_all


def test_multiselect_transaction_exports_without_mutating_extraction(signed):
    publish_fixture(signed)
    case_id = upload(signed, names=('Synthetic_transaction.pdf',), template='custom').json()['case_ids'][0]
    process_all()
    with SessionLocal() as db:
        snapshot = copy.deepcopy(db.scalar(select(Report).where(Report.case_id == case_id).order_by(Report.version.desc())).snapshot)
    snapshot['documents'][0]['normalized']['transaction_type'] = ['REMITTANCE', 'VALAS/BANKNOTES']
    original = copy.deepcopy(snapshot)
    report = SimpleNamespace(snapshot=snapshot, version=1, state='DRAFT', approved_by=None, fingerprint='test')
    data, _ = make_report(report, 'xlsx')
    sheet = load_workbook(io.BytesIO(data))['Kertas Kerja']
    assert sheet['F12'].value == 'REMITTANCE; VALAS/BANKNOTES'
    assert snapshot == original
    assert make_report(report, 'json')[0]
    assert make_report(report, 'pdf')[0].startswith(b'%PDF')


def test_compound_display_preserves_scalar_types_and_blocks_formulas():
    assert excel_value(None) is None
    assert excel_value(0) == 0
    assert excel_value(True) is True
    assert excel_value({'place':'KOTA TEST','date':'13-06-2017'}) == 'KOTA TEST — 13 Juni 2017'
    assert excel_value(['=1+1']).startswith("'")
