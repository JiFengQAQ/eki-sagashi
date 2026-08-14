# -*- coding: utf-8 -*-
"""数据管道总入口: ekidata + S12客流 + 读音 + 颜色 -> data/stations.json + meta.json"""
import hashlib
import json
import os
import re
import subprocess
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

# 机场英文名 -> 日语名(公开事实, 用于「空港第N」式站名补前缀别名)
AIRPORT_JA = {
    'Narita': '成田', 'Haneda': '羽田', 'Kansai': '関西',
    'New Chitose': '新千歳', 'Naha': '那覇', 'Fukuoka': '福岡',
    'Kobe': '神戸', 'Sendai': '仙台', 'Miyazaki': '宮崎',
    'Hanamaki': '花巻', 'Yonago': '米子', 'Osaka': '大阪',
    'Central Japan International': '中部国際',
}

_FULLWIDTH_DIGITS = str.maketrans('０１２３４５６７８９', '0123456789')


def systematic_aliases(name, en):
    """系统性别名生成(非单例):
    1) 站名括号内容(空港第２ビル（第２旅客ターミナル）→ 第２旅客ターミナル)
    2) 「空港第N…」站: 由 en 'Airport Terminal 2·3' 数据驱动补「成田空港第Nターミナル」"""
    import re as _re
    out = []
    m = _re.search(r'[（(]([^）)]+)[)）]', name)
    if m:
        out.append(m.group(1))
    # 「第N旅客ターミナル」→ 补剥「旅客」变体「第Nターミナル」
    for a in list(out):
        mm = _re.search(r'第([0-9０-９]+)旅客ターミナル', a)
        if mm:
            out.append(a.replace(mm.group(0), f'第{mm.group(1)}ターミナル'))
    # 「○○空港（第N旅客ターミナル）」→ 「○○空港第Nターミナル」
    mm = _re.match(r'^(.+?空港)（第([0-9０-９]+)旅客ターミナル）$', name)
    if mm:
        n = mm.group(2).translate(_FULLWIDTH_DIGITS)
        out.append(f'{mm.group(1)}第{n}ターミナル')
    if name.startswith('空港第') and en:
        en_airport = _re.match(r'(.+?)\s+Airport', en)
        en_term = _re.search(r'Airport\s+Terminal\s+([0-9·・]+)', en)
        if en_airport and en_term:
            ja = AIRPORT_JA.get(en_airport.group(1))
            if ja:
                for n in en_term.group(1).translate(_FULLWIDTH_DIGITS).replace('・', '·').split('·'):
                    out.append(f'{ja}空港第{n}ターミナル')
    return out


def build():
    t0 = time.time()
    eki = load_ekidata()
    color_table = build_color_table()
    attach_colors(eki['stations'], color_table, eki['line_info'])
    s12 = load_s12()
    rid = join_ridership(s12, eki)
    kana = build_kana(eki['stations'])

    # 英文名合并: OSM name:en > Wikidata en label; 清洗尾 Station
    import re as _re
    wd_en = {}
    wd_en_path = os.path.join(DATA_DIR, 'raw', 'wd_en.json')
    if os.path.exists(wd_en_path):
        wd_en = json.load(open(wd_en_path, encoding='utf-8'))
    en_map = {}
    for st in eki['stations']:
        en = kana[st['id']][3]
        if not en:
            en = wd_en.get(st['name']) or wd_en.get(st['name'] + '駅', '')
        if en:
            cleaned = _re.sub(r'\s*[Ss]tation$', '', en).strip()
            en_map[st['id']] = cleaned

    # canon.json: 站名/线路字符集 + JP_MAP键 + 简繁体两侧 的 canonical 映射(前端JS查表用)
    from normalize import JP_MAP, canonical_kanji, _KANJI_RE, _s2t
    used_chars = set()
    for st in eki['stations']:
        used_chars.update(st['name'])
        for l in st['lines']:
            used_chars.update(l['name'])
        used_chars.update(st['pref'])  # 逐字
        used_chars.update(st['muni'])  # 逐字
    # 简体/繁体查询侧: 数据字符 + JP_MAP键 両方から変体を生成
    from normalize import _t2s
    extra = set()
    for c in list(used_chars) + list(JP_MAP.keys()):
        if _KANJI_RE.match(c):
            extra.add(_s2t.convert(c))
            extra.add(_t2s.convert(c))
    used_chars |= extra
    # JP_MAP 键中映射到数据字符/变体的保留(如 涩→渋, 濱→浜→滨)
    all_needed = used_chars | {k for k, v in JP_MAP.items() if v in used_chars}
    chars = set(JP_MAP.keys()) | all_needed
    canon = {}
    for c in chars:
        if c in ('々', 'ヶ', 'ケ', 'ヵ'):
            continue
        if _KANJI_RE.match(c):
            canon[c] = canonical_kanji(c)
        else:
            canon[c] = c
    # 冗長キー除去: データ+変換バリアント+JP_MAP必要キーのみ残す
    canon = {k: v for k, v in canon.items() if k in all_needed}

    stations = []
    for st in eki['stations']:
        k, r, r_ou, _ = kana[st['id']]
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
        al = list(STATION_ALIASES.get(st['name'], []))
        sys_al = systematic_aliases(st['name'], en_map.get(st['id'], ''))
        for a in sys_al:
            if a not in al:
                al.append(a)
        if al:
            rec['al'] = al
        en = en_map.get(st['id'])
        if en:
            rec['en'] = en
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
        'rid_window': '2015-2024(latest available year per station)',
        'rid_source': '国土数値情報 駅別乗降客数データ S12-25(2024年度版, CC BY 4.0)',
        'rid_note': 'JR系は乗車人員×2の推定乗降; 事業者間合算なし(公式方針); 各站取窗口内最新可用年份の最大運営者値',
        'sources': {
            'ekidata': 'https://www.ekidata.jp/ (saitamasaitama/ekidata-json 2022-09-21 snapshot)',
            'ridership': 'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html',
            'colors': 'takumif/railway_colors_japan + Wikipedia 日本の鉄道ラインカラー一覧/infobox 核对',
            'kana': '人工例外 > OSM name:ja-Hira > Wikidata P1814; roma由kana确定性黑本式转换(无汉字转读)',
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
    # バージョン自動注入: git short hash で ?v=N を統一
    ver = subprocess.check_output(
        ['git', 'rev-parse', '--short', 'HEAD'],
        cwd=REPO_ROOT, text=True).strip()
    for fn in ('index.html', 'app.js', 'sw.js'):
        p = os.path.join(web_dir, fn)
        src = open(p, encoding='utf-8').read()
        src = re.sub(r'\?v=[a-zA-Z0-9]+', f'?v={ver}', src)
        if fn == 'sw.js':
            src = re.sub(r"eki-sagashi-v[a-zA-Z0-9]+", f'eki-sagashi-v{ver}', src)
        open(p, 'w', encoding='utf-8').write(src)
    print(f'version: {ver}')
    print(f"stations: {len(stations)}  kana: {kana_ok}  roma: {roma_ok}  rid: {with_val}  "
          f"line_color: {line_colored}/{line_total}  bytes: {len(raw)}  {time.time()-t0:.1f}s")


if __name__ == '__main__':
    build()
