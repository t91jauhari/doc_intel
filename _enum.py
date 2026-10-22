import os

EX = {
    "node_modules", ".git", ".next", "__pycache__", ".venv", "venv",
    "dist", "build", ".pytest_cache", ".mypy_cache", "site-packages",
    ".vscode", ".idea", "coverage", ".cache",
}
root = os.getcwd()
out = []
for d, ds, fs in os.walk(root):
    ds[:] = [x for x in ds if x not in EX]
    for f in fs:
        full = os.path.join(d, f)
        try:
            rel = os.path.relpath(full, root)
        except ValueError:
            continue
        if not rel or rel.startswith(".."):
            continue
        out.append(rel.replace("\\", "/"))
out.sort()
with open("_tree.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print(f"WROTE {len(out)} files to _tree.txt")
