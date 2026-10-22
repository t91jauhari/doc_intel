import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain import route, default_config
from app.grouping import plan_grouping

names = [l.strip() for l in open(Path(__file__).with_name('accop_names.txt'), encoding='utf-8') if l.strip()]
cfg = default_config()
print('== route() per file ==')
for n in names:
    hint, cust, _cls = route(n, cfg)
    print(f'{cust!r:35} | {hint:25} | {n}')
print()
print('== plan_grouping() ==')
rows = plan_grouping(names, cfg)
for r in rows:
    print(f"{r['customer'] or '(unresolved)':30} | {r['status']:10} | {r['hint']:20} | {r['filename']}")
