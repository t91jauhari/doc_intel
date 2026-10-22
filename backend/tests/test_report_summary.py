from openpyxl import Workbook
from app.report_summary import write_summary


def values(sheet):
    return {row[3].value: row[4].value for row in sheet if row[3].value}


def test_zero_scores_and_provisional_points_are_visible_beside_labels():
    sheet = Workbook().active
    write_summary(sheet, 15, [{"scores":{"total":0}, "sop_summary":{"earned":11,"possible":41,"pending":1,"failed":29}}])
    result = values(sheet)
    assert result["Scored compliance (%) · legacy"] == 0
    assert result["Scored cases · legacy"] == 1
    assert result["Unresolved cases · legacy"] == 0
    assert result["Rule compliance (%)"] == 26.83
    assert result["Pending visual reviews"] == 1
    assert result["Rule scoring status"] == "Provisional"


def test_unassessed_legacy_and_missing_point_snapshots_are_explicit():
    sheet = Workbook().active
    write_summary(sheet, 1, [{"scores":{"total":None}}])
    result = values(sheet)
    assert result["Scored compliance (%) · legacy"] == "Awaiting assessment"
    assert result["Scored cases · legacy"] == 0
    assert result["Unresolved cases · legacy"] == 1
    assert result["Cases needing current SOP scoring"] == 1
    assert result["Rule scoring status"] == "Incomplete coverage"
