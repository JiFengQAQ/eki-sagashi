import csv, json, zipfile, unicodedata

# 扫描所有涉及字符: ekidata站名/线路名 + S12站名 + 维基近郊区文本
chars = set()
for fn in ['station.csv', 'line.csv']:
    with open(f'data/raw/{fn}', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            for k in ('station_name', 'line_name'):
                if k in row:
                    chars.update(row[k])
with open('data/raw/company.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        chars.update(row['company_name'])

z = zipfile.ZipFile('data/raw/S12-25_GML.zip')
d = json.loads(z.read('S12-25_GML/UTF-8/S12-25_NumberOfPassengers.geojson'))
for f in d['features']:
    p = f['properties']
    chars.update(p['S12_001'])
    chars.update(p['S12_002'])
    chars.update(p['S12_003'])

# opencc 简繁
try:
    from opencc import OpenCC
    s2t = OpenCC('s2t')
    t2s = OpenCC('t2s')
except Exception as e:
    print('opencc fail:', e)
    s2t = t2s = None

# 找"候选映射字": 全角汉字中, s2t或t2s会变动的字 + 常用旧字体
cands = {}
for c in sorted(chars):
    if not ('\u4e00' <= c <= '\u9fff'):
        continue
    if s2t is None:
        break
    st = s2t.convert(c)
    ts = t2s.convert(c)
    if c != st or c != ts:
        cands[c] = (st, ts)

print('总字符数:', len(chars), '汉字候选:', len(cands))
for c, (st, ts) in cands.items():
    print(f'  {c}  s2t={st}  t2s={ts}')
