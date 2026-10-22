"""Reproducible release gate; run from the project using its Python environment."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Run core checks only; records browser as NOT RUN.",
    )
    args = parser.parse_args()
    node = shutil.which("node")
    if not node:
        parser.error(
            "Node.js is required. Install frontend dependencies with npm ci first."
        )
    output = (
        ROOT
        / "data"
        / "verification"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    output.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "NEXT_TELEMETRY_DISABLED": "1",
        "TEST_PYTHON": sys.executable,
        "BROWSER_OUTPUT_DIR": str(output / "browser"),
    }
    checks = [
        ("backend", [sys.executable, "-m", "pytest", "backend/tests", "-q"], ROOT),
        (
            "engine",
            [sys.executable, "-m", "unittest", "discover", "-s", "engine/tests", "-q"],
            ROOT,
        ),
        (
            "typescript",
            [node, "node_modules/typescript/bin/tsc", "--noEmit"],
            ROOT / "frontend",
        ),
        (
            "frontend-build",
            [node, "node_modules/next/dist/bin/next", "build", "--webpack"],
            ROOT / "frontend",
        ),
    ]
    if not args.skip_browser:
        checks.append(("browser", [node, "scripts/browser_smoke.mjs"], ROOT))
    results = []
    for name, command, cwd in checks:
        print(f"Running {name}; log: {output / (name + '.log')}", flush=True)
        with (output / (name + ".log")).open("w", encoding="utf-8") as log:
            process = subprocess.run(
                command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT
            )
        results.append(
            {
                "check": name,
                "status": "PASS" if process.returncode == 0 else "FAIL",
                "exit_code": process.returncode,
            }
        )
        if process.returncode:
            break
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checks": results,
        "not_run": [name for name, _, _ in checks[len(results) :]],
        "browser_mode": "NOT RUN"
        if args.skip_browser
        else "synthetic fixtures / isolated local storage",
        "live_llama": "NOT RUN",
        "windows_launcher": "NOT RUN",
    }
    (output / "result.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Verification evidence: {output}", flush=True)
    return int(any(r["status"] == "FAIL" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
