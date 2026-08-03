# -*- coding: utf-8 -*-
"""数据管道总入口: ekidata + S12客流 + 读音 + 颜色 -> data/stations.json + meta.json"""
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from colors import attach_colors, build_color_table
from ekidata import load_ekidata
from kana import build_kana
from s12 import join_ridership, load_s12

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, 'data')


# 英语来源别名(可考): 站名 -> 英语词列表; 来源中文维基条目名
# 高輪ゲートウェイ: 中文维基「高輪Gateway站」, 名称来源于英语 gateway
STATION_ALIASES = {
    '高輪ゲートウェイ': ['gateway', 'takanawagateway'],
}


def build():
    t0 = time.time()
    eki = load_ekidata()
    color_table = build_color_table()
    attach_colors(eki['stations'], color_table, eki['line_info'])
    s12 = load_s12()
    rid = join_ridership(s12)
    kana = build_kana(eki['stations'])

    # canon.json: 站名/线路字符集 + JP_MAP键 + 简繁体两侧 的 canonical 映射(前端JS查表用)
    from normalize import JP_MAP, canonical_kanji, _KANJI_RE, _s2t
    chars = set(JP_MAP.keys())
    for st in eki['stations']:
        chars.update(st['name'])
        for l in st['lines']:
            chars.update(l['name'])
    chars.update(st['pref'] for st in eki['stations'])
    chars.update(st['muni'] for st in eki['stations'])
    # 简体/繁体查询侧: 对每个数据字符补 s2t/t2s 变体
    from normalize import _t2s
    extra = set()
    for c in list(chars):
        if _KANJI_RE.match(c):
            extra.add(_s2t.convert(c))
            extra.add(_t2s.convert(c))
    chars |= extra
    canon = {}
    for c in chars:
        if c in ('々', 'ヶ', 'ケ', 'ヵ'):
            continue
        if _KANJI_RE.match(c):
            canon[c] = canonical_kanji(c)
        else:
            canon[c] = c

    stations = []
    for st in eki['stations']:
        k, r, r_ou = kana[st['id']]
        rid_info = rid.get(st['id'], {'rid': {'v': None, 'y': None}, 'per': []})
        lines = [{'n': l['name'], 'c': l.get('color')} for l in st['lines']]
        rec = {
            'id': st['id'],
            'name': st['name'],
            'kana': k,
            'roma': r,
            'roma_ou': r_ou,
            'pref': st['pref'],
            'muni': st['muni'],
            'ward': st.get('ward', ''),
            'lat': round(st['lat'], 5),
            'lon': round(st['lon'], 5),
            'lines': lines,
            'rid': {'v': rid_info['rid']['v'], 'y': rid_info['rid']['y']},
        }
        per = []
        for p in rid_info['per']:
            item = {'op': p['op_disp'], 'line': p['line'], 'v': p['v'], 'y': p['y']}
            if p.get('note'):
                item['note'] = p['note']
            per.append(item)
        rec['per'] = per
        al = STATION_ALIASES.get(st['name'])
        if al:
            rec['al'] = al
        stations.append(rec)

    stations.sort(key=lambda s: (s['rid']['v'] is None, -(s['rid']['v'] or 0), s['kana']))

    with_val = sum(1 for s in stations if s['rid']['v'])
    kana_ok = sum(1 for s in stations if s['kana'])
    roma_ok = sum(1 for s in stations if s['roma'])
    line_colored = 0
    line_total = 0
    for s in stations:
        for l in s['lines']:
            line_total += 1
            if l['c']:
                line_colored += 1

    raw = json.dumps(stations, ensure_ascii=False, separators=(',', ':'))
    meta = {
        'name': '駅さがし data',
        'built_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'station_count': len(stations),
        'kana_coverage': round(kana_ok / len(stations), 4),
        'roma_coverage': round(roma_ok / len(stations), 4),
        'rid_coverage': round(with_val / len(stations), 4),
        'line_color_coverage': round(line_colored / line_total, 4),
        'rid_window': '2015-2019(latest available year per station)',
        'rid_source': '国土数値情報 駅別乗降客数データ S12-25(2024年度版, CC BY 4.0)',
        'rid_note': 'JR系は乗車人員×2の推定乗降; 事業者間合算なし(公式方針); 各站取窗口内最新可用年份の最大運営者値',
        'sources': {
            'ekidata': 'https://www.ekidata.jp/ (saitamasaitama/ekidata-json 2022-09-21 snapshot)',
            'ridership': 'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html',
            'colors': 'takumif/railway_colors_japan + Wikipedia 日本の鉄道ラインカラー一覧/infobox 核对',
            'kana': 'Wikidata P1814 + OSM name:ja-Hira + pykakasi(例外词典)',
        },
        'sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'bytes': len(raw),
    }
    with open(os.path.join(DATA_DIR, 'stations.json'), 'w', encoding='utf-8') as f:
        f.write(raw)
    with open(os.path.join(DATA_DIR, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA_DIR, 'canon.json'), 'w', encoding='utf-8') as f:
        json.dump(canon, f, ensure_ascii=False, separators=(',', ':'))
    # web/ 部署副本
    web_dir = os.path.join(REPO_ROOT, 'web')
    for fn in ('stations.json', 'canon.json'):
        import shutil
        shutil.copy(os.path.join(DATA_DIR, fn), os.path.join(web_dir, fn))
    print(f"stations: {len(stations)}  kana: {kana_ok}  roma: {roma_ok}  rid: {with_val}  "
          f"line_color: {line_colored}/{line_total}  bytes: {len(raw)}  {time.time()-t0:.1f}s")


if __name__ == '__main__':
    build()
