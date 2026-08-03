# -*- coding: utf-8 -*-
"""ekidata 免费CSV加载:站(按组码合并)、线路、运营商、市町村解析"""
import csv
import os
import re

_MUNI_RE = re.compile(r'^(.+?[市区町村])')

PREF_NAMES = [
    '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
    '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
    '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
    '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
    '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
    '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
    '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県',
]


def parse_muni(addr):
    """地址->(市町村, 区/郡);无市町村返回(None,None);先剥离已知都道府県名"""
    s = addr or ''
    for p in PREF_NAMES:
        if s.startswith(p):
            s = s[len(p):]
            break
    m = _MUNI_RE.match(s)
    if not m:
        return None, None
    muni = m.group(1)
    rest = s[m.end():]
    ward = ''
    wm = re.match(r'^([^市町村]+?区)', rest)
    if wm and muni.endswith('市'):
        ward = wm.group(1)
    gun = ''
    gm = re.match(r'^(.+?郡)(.+?[町村])$', muni)
    if gm:
        gun, muni = gm.group(1), gm.group(2)
    return muni, ward or gun


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_ekidata(raw_dir=None):
    if raw_dir is None:
        raw_dir = os.path.join(_REPO_ROOT, 'data', 'raw')

    def read(name):
        with open(os.path.join(raw_dir, name), encoding='utf-8') as f:
            return list(csv.DictReader(f))

    stations = read('station.csv')
    lines = read('line.csv')
    companies = read('company.csv')
    prefs = {p['pref_cd']: p['pref_name'] for p in read('pref.csv')}
    comp_name = {c['company_cd']: c['company_name'] for c in companies}
    line_company = {l['line_cd']: l['company_cd'] for l in lines}
    line_info = {l['line_cd']: l for l in lines}

    active = [s for s in stations if s['e_status'] == '0']
    by_id = {}
    for s in active:
        gid = s['station_g_cd']
        # 同组异名(剥「駅」/括号后) = 不同物理站, 拆分独立; 同名才合并
        from normalize import norm_station_name
        key = (gid, norm_station_name(s['station_name']))
        st = by_id.get(key)
        if st is None:
            st = {
                'id': key[0],
                'name': s['station_name'],
                'pref': prefs.get(s['pref_cd'], ''),
                'muni': '',
                'ward': '',
                'lat': float(s['lat']) if s['lat'] else 0.0,
                'lon': float(s['lon']) if s['lon'] else 0.0,
                'lines': [],
            }
            muni, ward = parse_muni(s['address'])
            st['muni'] = muni or ''
            st['ward'] = ward or ''
            by_id[key] = st
        lc = s['line_cd']
        li = line_info.get(lc, {})
        st['lines'].append({
            'code': lc,
            'name': li.get('line_name', ''),
            'company': comp_name.get(line_company.get(lc, ''), ''),
            'kana': li.get('line_name_k', ''),
        })
    # 同组同线路去重
    for st in by_id.values():
        seen = set()
        uniq = []
        for l in st['lines']:
            key = (l['code'], l['name'])
            if key not in seen:
                seen.add(key)
                uniq.append(l)
        st['lines'] = uniq
    # id 唯一化: 同组拆分出的多站 id 加序号
    id_seen = {}
    for st in by_id.values():
        if st['id'] in id_seen:
            id_seen[st['id']] += 1
            st['id'] = f"{st['id']}-{id_seen[st['id']]}"
        else:
            id_seen[st['id']] = 1

    return {
        'stations': list(by_id.values()),
        'by_id': by_id,
        'active_count': len(by_id),
        'lines': lines,
        'line_info': line_info,
        'companies': companies,
        'comp_name': comp_name,
        'line_company': line_company,
    }
