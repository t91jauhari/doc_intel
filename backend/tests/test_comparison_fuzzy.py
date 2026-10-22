from app.dataset_comparison import fuzzy_text, summarize
from test_dataset_comparison import document, results


def test_fuzzy_rules_keep_identifiers_numbers_and_identity_differences_visible():
    assert fuzzy_text("USD", "USD.", "text", "currency") is None
    assert fuzzy_text("12345678", "12345679", "identifier", "nik") is None
    assert fuzzy_text("Jl. Merdeka 13", "Jl. Merdeka 14", "text", "address") is None
    assert fuzzy_text("INDAH LARUNA PRIMA", "INDAH LARUNA PRIMaX", "text", "name")["status"] == "REVIEW"
    assert fuzzy_text("Jl. Merdeka No 13", "Jl Merdeka No 13", "text", "address")["status"] == "FUZZY_MATCH"
    assert fuzzy_text("Regular international service delivery", "Regular international serv ice delivery", "text", "notes") is None
    assert fuzzy_text("Regular international service delivery", "Regular international service delivary", "text", "notes")["status"] == "FUZZY_MATCH"
    assert fuzzy_text("Dirman Siswanto", "Dirman Santoso", "text", "name") is None


def test_document_percentages_and_fuzzy_counts_use_explicit_denominators():
    stats = summarize([{"status": s} for s in ["MATCH", "FUZZY_MATCH", "MISMATCH", "REVIEW", "NOT_APPLICABLE"]])
    assert stats["match_rate"] == 66.67
    assert stats["exact_match_rate"] == 33.33
    assert stats["coverage_rate"] == 75
    assert not stats["complete"]
    assert summarize([{"status": "NOT_APPLICABLE"}])["match_rate"] is None
    report, rows = results([document(normalized={"name": "INDAH LARUNA PRIMAX", "nik": "3896872710880099"})])
    assert rows["row-4"]["status"] == "REVIEW"
    assert rows["row-4"]["similarity"] > 90
    assert len(report["document_groups"]) == 8
    group = next(g for g in report["document_groups"] if g["section"] == 2)
    assert group["match_rate"] == 100
    assert group["coverage_rate"] == 5
    assert not group["complete"]
