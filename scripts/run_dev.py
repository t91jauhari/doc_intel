"""Start API + independent worker + Next.js on Windows, WSL or Linux."""

import os
import shutil
import subprocess
import sys
import time
import venv
from pathlib import Path

# UTF-8 also makes console output predictable on Windows. File readers still
# declare their encoding explicitly; correctness does not depend on this flag.
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(root / "scripts/init_dev.py")], check=True)
# MinIO runs independently so uploaded files survive app restarts.
# For an externally managed MinIO server, set MINIO_MANAGED_EXTERNALLY=1.
if os.getenv("MINIO_MANAGED_EXTERNALLY") != "1":
    if not shutil.which("docker"):
        raise SystemExit(
            "MinIO requires Docker Desktop. Install/start it, or set MINIO_MANAGED_EXTERNALLY=1 for your existing MinIO server."
        )
    subprocess.run(
        ["docker", "compose", "up", "-d", "--wait", "minio"], cwd=root, check=True
    )
envdir = root / ".venv"
python = envdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if not python.exists():
    venv.create(envdir, with_pip=True)
if subprocess.run(
    [str(python), "-c", "import fastapi,sqlalchemy,temporalio,llama_cloud,minio"],
    capture_output=True,
).returncode:
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-r",
            str(root / "backend/requirements.txt"),
        ],
        check=True,
    )
npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
if not npm:
    raise SystemExit("Install Node.js 24 LTS, reopen the terminal and run again.")


def npm_command(*args):
    return ["cmd.exe", "/d", "/c", "npm", *args] if os.name == "nt" else [npm, *args]


if not (root / "frontend/node_modules").exists():
    subprocess.run(
        npm_command("ci", "--no-audit", "--no-fund"), cwd=root / "frontend", check=True
    )
env = {
    **os.environ,
    "WORKFLOW_DRIVER": "local",
    "API_INTERNAL_URL": "http://127.0.0.1:8000",
    "NEXT_TELEMETRY_DISABLED": "1",
}
children = []
try:
    children.append(
        subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=root / "backend",
            env=env,
        )
    )
    import urllib.request

    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)
            break
        except Exception:
            if children[0].poll() is not None:
                raise RuntimeError("API startup failed; inspect its log.")
            time.sleep(0.5)
    else:
        raise RuntimeError("API did not become healthy.")
    children.append(
        subprocess.Popen(
            [str(python), "-m", "app.worker"], cwd=root / "backend", env=env
        )
    )
    children.append(
        subprocess.Popen(npm_command("run", "dev"), cwd=root / "frontend", env=env)
    )
    print(
        "\nOpen http://localhost:3000 · organization sqe · user sqe@bic.local\nPress Ctrl+C to stop the local services.",
        flush=True,
    )
    while all(p.poll() is None for p in children):
        time.sleep(1)
    if any(p.returncode for p in children if p.returncode is not None):
        raise RuntimeError("A service stopped. Inspect the logs above.")
except KeyboardInterrupt:
    pass
finally:
    for p in reversed(children):
        if p.poll() is None:
            p.terminate()
    for p in children:
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
