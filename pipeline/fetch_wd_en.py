# -*- coding: utf-8 -*-
"""wbgetentities 批量拉 en label (curl, 50 qid/批) — 从 wd_stations.json 的 qid 出发"""
import json
import os
import subprocess
import time
import urllib.parse

RAW = '/home/ubuntu/eki-sagashi/data/raw'
wd = json.load(open(f'{RAW}/wd_stations.json', encoding='utf-8'))
rows = wd.get('results', {}).get('bindings', [])

qid_to_ja = {}
for r in rows:
    qid = r['station']['value'].rsplit('/', 1)[-1]
    ja = r.get('stationLabel', {}).get('value', '')
    if qid and ja:
        qid_to_ja.setdefault(qid, ja)
qids = list(qid_to_ja.keys())
print(f'qids: {len(qids)}', flush=True)

en_map = {}  # qid -> en label
out_path = f'{RAW}/wd_en.json'
# 断点续跑: 已有结果跳过
done_qids = set()
if os.path.exists(out_path):
    existing = json.load(open(out_path, encoding='utf-8'))
    # existing 是 ja -> en; 需要 qid -> ja 反查
    done_qids = {q for q, ja in qid_to_ja.items() if ja in existing}
    print(f'resume: {len(done_qids)} qids already done', flush=True)

for i in range(0, len(qids), 50):
    chunk = [q for q in qids[i:i + 50] if q not in done_qids]
    if not chunk:
        continue
    url = ('https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=labels'
           '&languages=en|ja&ids=' + urllib.parse.quote('|'.join(chunk)))
    for attempt in range(4):
        try:
            r = subprocess.run(['curl', '-s', '-A', 'eki-sagashi/1.0', '--max-time', '30', url],
                               capture_output=True, text=True, timeout=40)
            data = json.loads(r.stdout)
            for qid, ent in data.get('entities', {}).items():
                en = ent.get('labels', {}).get('en', {}).get('value', '')
                if en:
                    en_map[qid] = en
            break
        except Exception as e:
            if attempt == 3:
                print(f'chunk {i} failed: {e}', flush=True)
            time.sleep(5 * (attempt + 1))
    if (i // 50 + 1) % 25 == 0:
        # 增量保存
        out = {}
        for q, ja in qid_to_ja.items():
            en = en_map.get(q)
            if en and en != ja:
                out.setdefault(ja, en)
        json.dump(out, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{i // 50 + 1}/{len(qids) // 50 + 1} chunks, en: {len(en_map)}', flush=True)
    time.sleep(1.5)

out = {}
for qid, ja in qid_to_ja.items():
    en = en_map.get(qid)
    if en and en != ja:
        out.setdefault(ja, en)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f'stations with en: {len(out)}')
