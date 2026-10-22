"""Regenerate offline starter XLSX files from the current registered engine contracts."""

import time
from pathlib import Path

from app.config_workbook import export_config
from app.domain import default_config
from app.kertas_kerja import workbook
from app.sop import CATEGORIES, score

root = Path(__file__).resolve().parents[1]
output = root / "templates"
output.mkdir(exist_ok=True)
cfg = default_config()
cfg["provider"] = "fixture"
(output / "forex-workflow-config-template.xlsx").write_bytes(
    export_config(default_config())
)
snapshots = []
for index, status in enumerate(["PASS", "FAIL", "REVIEW"], 1):
    findings = [
        {
            "rule_id": "DEMO_" + category,
            "field": "application.remitter.name",
            "source_ref": "SOP1:2 | SOP2:2",
            "scope_basis": "YES_SELECTED",
            "category": category,
            "eligible": True,
            "result": status if n == 0 else "PASS",
            "message": "Synthetic demonstration only",
            "actual": "Example Customer",
            "expected": "Example Customer",
            "evidence": {"demo": True},
        }
        for n, category in enumerate(CATEGORIES)
    ]
    snapshots.append(
        {
            "reference": f"DEMO-{index}",
            "customer": f"Example Customer {index}",
            "branch_code": "DEMO",
            "branch_name": "Example Branch",
            "configuration": cfg,
            "config_version": 1,
            "provider": "fixture",
            "generated_at": time.time(),
            "sop_completed_at": time.time(),
            "validation_status": status,
            "case_context": {"transaction_carrier": "UNKNOWN"},
            "findings": findings,
            "technical_findings": [],
            "scores": score(findings),
            "documents": [
                {
                    "id": f"demo-{index}",
                    "filename": f"example{index}_transaction.pdf",
                    "doc_type": "application",
                    "status": "COMPLETED",
                    "sha256": "synthetic demo; no original document",
                    "normalized": {
                        "remitter": {"name": f"Example Customer {index}"},
                        "remitter_account_number": f"00000{index}",
                        "transaction_type": "SWIFT",
                        "transaction_date": "05-10-2026",
                    },
                    "raw": {},
                    "overrides": {},
                }
            ],
        }
    )
(output / "forex-kertas-kerja-template.xlsx").write_bytes(workbook(snapshots))
print(
    "Generated starter configuration and synthetic Kertas Kerja examples in templates/."
)
