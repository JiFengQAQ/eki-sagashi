import sys
sys.path.insert(0, 'pipeline')
import csv
from collections import Counter
from ekidata import load_ekidata
from colors import build_color_table, color_for

t = build_color_table()
eki = load_ekidata()
comp = {c['company_cd']: c['company_name'] for c in eki['companies']}

missing = []
for l in eki['lines']:
    if l['e_status'] != '0':
        continue
    c = color_for(t, l['line_name'], comp.get(l['company_cd'], ''))
    if not c:
        missing.append((comp.get(l['company_cd'], '?'), l['line_name']))

print(f'missing: {len(missing)}')
by_op = Counter(op for op, _ in missing)
for op, n in by_op.most_common(30):
    print(f'  {op}: {n}')
print()
print('sample missing lines:')
for op, ln in missing[:40]:
    print(f'  {op} | {ln}')
