# -*- coding: utf-8 -*-
"""国土数値情報 S12-25 駅別乗降客数:加载、与ekidata联表、2015-2019窗口年份选择"""
import json
import os
import zipfile

from ekidata import load_ekidata
from normalize import norm_operator, norm_station_name

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_YEARS = list(range(2011, 2025))
_WINDOW = list(range(2019, 2014, -1))  # 2019..2015 最新优先


def load_s12(zip_path=None):
    return {'units': _load_units(zip_path)}


def _field_for_year(y):
    # 2011->S12_009 ... 2024->S12_061: 每年4字段步进
    return f'S12_{9 + (y - 2011) * 4:03d}'


def _load_units(zip_path=None):
    if zip_path is None:
        zip_path = os.path.join(_REPO_ROOT, 'data', 'raw', 'S12-25_GML.zip')
    z = zipfile.ZipFile(zip_path)
    d = json.loads(z.read('S12-25_GML/UTF-8/S12-25_NumberOfPassengers.geojson'))
    units = {}
    for f in d['features']:
        p = f['properties']
        if p['S12_006'] != 1:
            continue
        name = norm_station_name(p['S12_001'])
        op = p['S12_002']
        key = (name, op)
        u = units.setdefault(key, {
            'name': p['S12_001'],
            'op': op,
            'group': p['S12_001g'],
            'passengers': {},
            'notes': {},
            'routes': set(),
        })
        u['routes'].add(p['S12_003'])
        for y in _YEARS:
            fld = _field_for_year(y)
            val = p.get(fld)
            prev = u['passengers'].get(str(y))
            if prev is None or (val and val > prev):
                u['passengers'][str(y)] = val
        note = p.get('S12_040')  # remarks2019
        if note:
            u['notes']['2019'] = note
    return units


def load_s12(zip_path=None):
    return {'units': _load_units(zip_path)}


def _pick_window(passengers):
    """2015-2019窗口内最新可用值; 全部无值返回(None,None)"""
    for y in _WINDOW:
        v = passengers.get(str(y))
        if v and v > 0:
            return v, y
    return None, None


def join_ridership(s12):
    """ekidata每站联S12:按(站名,运营商)匹配; 每运营商取窗口值; 站级取最大;
    新干线运营商不在ekidata线路中,按唯一站名回补"""
    eki = load_ekidata()
    units = s12['units']
    # 站名索引(用于新干线回补)
    name_index = {}
    for st in eki['stations']:
        name_index.setdefault(norm_station_name(st['name']), []).append(st['id'])

    result = {}
    for st in eki['stations']:
        per = []
        st_norm = norm_station_name(st['name'])
        for line in st['lines']:
            op = norm_operator(line['company'])
            if not op:
                continue
            key = (st_norm, op)
            u = units.get(key)
            if u is None:
                continue
            v, y = _pick_window(u['passengers'])
            if v is None:
                continue
            per.append({
                'op': op,
                'op_disp': u['op'],
                'line': sorted(u['routes'])[0],
                'v': v,
                'y': y,
                'note': u['notes'].get(str(y), ''),
            })
        # 新干线回补: S12 unit 线路名含新幹線 且 站名唯一
        for (sname, op), u in units.items():
            if sname != st_norm:
                continue
            routes = u['routes']
            if not any('新幹線' in r for r in routes):
                continue
            if len(name_index.get(sname, [])) != 1:
                continue
            v, y = _pick_window(u['passengers'])
            if v is None:
                continue
            if any(p['op'] == op for p in per):
                continue
            shink = sorted(r for r in routes if '新幹線' in r)
            per.append({
                'op': op,
                'op_disp': u['op'],
                'line': shink[0],
                'v': v,
                'y': y,
                'note': u['notes'].get(str(y), ''),
            })
        # 同运营商多线路合并(取大)
        merged = {}
        for p in per:
            key = p['op']
            if key not in merged or p['v'] > merged[key]['v']:
                merged[key] = p
        per = list(merged.values())
        if per:
            best = max(per, key=lambda p: p['v'])
            rid_v, rid_y = best['v'], best['y']
        else:
            rid_v, rid_y = None, None
        result[st['id']] = {
            'id': st['id'],
            'name': st['name'],
            'rid': {'v': rid_v, 'y': rid_y},
            'per': per,
        }
    return result
