import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain import default_config, route
from app.grouping import plan_grouping

names = [l.strip() for l in Path(__file__).with_name('accop_names.txt').read_text(encoding='utf-8').splitlines() if l.strip()]
cfg = default_config()
print('== route() per file ==')
for n in names:
    hint, cust, _ = route(n, cfg)
    print(f'{cust!r:32} | {hint:22} | {n}')
print()
print('== plan_grouping() ==')
for r in plan_grouping(names, cfg):
    print(f"{r['customer'] or '(unresolved)':28} | {r['status']:10} | {r['hint']:22} | {r['filename']}")
