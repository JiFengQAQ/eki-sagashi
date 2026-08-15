# -*- coding: utf-8 -*-
"""S12 补充管线: ekidata 缺的运行中站, 从国土数値情報 S12 提取补充
S12 含 8,621 站名, ekidata 2022-09 快照系统性缺站(七戸十和田等新干线站都缺).
判定规则:
  1. S12_006==1(有客流记录)
  2. 站名归一化后不在 ekidata 站名集
  3. 2023/2024 年有客流值(运行中; 废线站废线后无值)
  4. 坐标与最近 ekidata 站距离 > 300m(防同站异名重复)"""
import csv
import json
import math
import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RAW = os.path.join(_REPO_ROOT, 'data', 'raw')

# S12 字段: 客流 2011→S12_009, 每年+4
_FIELD = lambda y: f'S12_{9 + (y - 2011) * 4:03d}'


def norm_name(n):
    n = re.sub(r'^JR', '', n or '')
    n = re.sub(r'[（(].*?[)）]', '', n)
    return re.sub(r'[・･.\s　]', '', n)


def _dist(lat1, lon1, lat2, lon2):
    # 简易经纬度距离(米)
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_pref_map():
    rows = list(csv.DictReader(open(os.path.join(_RAW, 'pref.csv'), encoding='utf-8')))
    return {r['pref_cd']: r['pref_name'] for r in rows}


def supplement_from_s12(ekidata_stations, s12_units=None):
    """返回补充站列表. s12_units 为 s12.load_s12() 的 units 或 None(自行加载)"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from s12 import load_s12
    if s12_units is None:
        s12_units = load_s12()['units']

    ek_names = {norm_name(s['name']) for s in ekidata_stations}
    ek_coords = [(s['lat'], s['lon']) for s in ekidata_stations if s.get('lat')]
    pref_map = load_pref_map()

    # 按(归一化站名)聚合 S12 unit, 去重
    by_name = {}
    for (name, op), u in s12_units.items():
        nn = norm_name(name)
        if nn in by_name:
            by_name[nn].append((name, u))
        else:
            by_name[nn] = [(name, u)]

    out = []
    for nn, entries in sorted(by_name.items()):
        if nn in ek_names or not nn:
            continue
        # 运行中判定: 2023 或 2024 有客流
        running = False
        for _, u in entries:
            for y in ('2023', '2024'):
                v = u['passengers'].get(y)
                if v and v > 0:
                    running = True
        if not running:
            continue
        # 合并同站多运营商: 取客流最大的
        best = None
        best_v = 0
        for name, u in entries:
            for y in ('2024', '2023'):
                v = u['passengers'].get(y) or 0
                if v > best_v:
                    best_v = v
                    best = (name, u)
                    break
        if not best:
            continue
        name, u = best
        # 坐标: S12 LineString 取中点
        # units 结构不含坐标, 从 raw geojson 补
        out.append({'name': name, 'op': u['op'], 'routes': sorted(u['routes']),
                    'passengers': u['passengers']})
    return out


# 补充站的都道府県(2026-08 Nominatim reverse geocode 一次批查, 确定性数据)
SUPPLEMENT_PREF = {
    'くりこま高原': '宮城県', 'ほうらい丘': '滋賀県', 'もたて山': '滋賀県',
    'ガーラ湯沢': '新潟県', 'ケーブル坂本': '滋賀県', 'ケーブル延暦寺': '滋賀県',
    'ケーブル比叡': '京都府', 'ベイサイド･ステーション': '千葉県', '七戸十和田': '青森県',
    '上毛高原': '群馬県', '乙原': '大分県', '体験坑道': '青森県', '傘松': '京都府',
    '八栗山上': '香川県', '八栗登山口': '香川県', '六甲ケーブル下': '兵庫県',
    '六甲山上': '兵庫県', '十国峠山頂': '静岡県', '十国峠山麓': '静岡県',
    '多宝塔': '京都府', '大山ケーブル': '神奈川県', '大観峰': '富山県',
    '安中榛名': '群馬県', '室堂': '富山県', '宮脇': '茨城県', '山上': '福岡県',
    '山麓': '福岡県', '御岳山': '東京都', '摩耶ケーブル': '兵庫県',
    '新大牟田': '福岡県', '新尾道': '広島県', '新岩国': '山口県', '新玉名': '熊本県',
    '本庄早稲田': '埼玉県', '東京ディズニーシー･ステーション': '千葉県',
    '東京ディズニーランド･ステーション': '千葉県', '東広島': '広島県',
    '水沢江刺': '岩手県', '清滝': '東京都', '滝本': '東京都', '白石蔵王': '宮城県',
    '第一イン新湊クロスベイ前': '富山県', '筑波山頂': '茨城県', '美女平': '富山県',
    '虹': '兵庫県', '阿夫利神社': '神奈川県', '雲泉寺': '大分県',
    '青函トンネル記念館': '青森県', '高尾山': '東京都', '黒部平': '富山県',
    '黒部湖': '富山県',
}

# 补充站的市町村(同一次Nominatim批查的city字段)
SUPPLEMENT_MUNI = {
    'くりこま高原': '栗原市', 'ほうらい丘': '大津市', 'もたて山': '大津市',
    'ガーラ湯沢': '湯沢町', 'ケーブル坂本': '大津市', 'ケーブル延暦寺': '大津市',
    'ケーブル比叡': '京都市', 'ベイサイド･ステーション': '浦安市', '七戸十和田': '七戸町',
    '上毛高原': 'みなかみ町', '乙原': '別府市', '体験坑道': '外ヶ浜町', '傘松': '宮津市',
    '八栗山上': '高松市', '八栗登山口': '高松市', '六甲ケーブル下': '神戸市',
    '六甲山上': '神戸市', '十国峠山頂': '函南町', '十国峠山麓': '函南町',
    '多宝塔': '京都市', '大山ケーブル': '伊勢原市', '大観峰': '立山町',
    '安中榛名': '安中市', '室堂': '立山町', '宮脇': 'つくば市', '山上': '北九州市',
    '山麓': '北九州市', '御岳山': '青梅市', '摩耶ケーブル': '神戸市',
    '新大牟田': '大牟田市', '新尾道': '尾道市', '新岩国': '岩国市', '新玉名': '玉名市',
    '本庄早稲田': '本庄市', '東京ディズニーシー･ステーション': '浦安市',
    '東京ディズニーランド･ステーション': '浦安市', '東広島': '東広島市',
    '水沢江刺': '奥州市', '清滝': '八王子市', '滝本': '青梅市', '白石蔵王': '白石市',
    '第一イン新湊クロスベイ前': '射水市', '筑波山頂': 'つくば市', '美女平': '立山町',
    '虹': '神戸市', '阿夫利神社': '伊勢原市', '雲泉寺': '別府市',
    '青函トンネル記念館': '外ヶ浜町', '高尾山': '八王子市', '黒部平': '立山町',
    '黒部湖': '立山町',
}


# 手动新站: 数据源(ekidata 2022-09 / S12 2024年度)未覆盖的开业新站
# 坐标/读音以 Wikipedia 条目为准
# 2023-2025 年开业新站全量(2026-08-15 Wikipedia「NNNN年の鉄道」整理)
MANUAL_NEW_STATIONS = [
    # 2023-08-26: 宇都宮ライトレール (芳賀・宇都宮LRT)
    {'id': 'manual-utsunomiya-higashi', 'name': '宇都宮駅東口', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55905, 'lon': 139.89946, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'うつのみやえきひがしぐち', 'opened': '2023-08-26'},
    {'id': 'manual-higashi-shukugo', 'name': '東宿郷', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55826, 'lon': 139.90406, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ひがししゅくごう', 'opened': '2023-08-26'},
    {'id': 'manual-ekihigashi-koen', 'name': '駅東公園前', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55796, 'lon': 139.90814, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'えきひがしこうえんまえ', 'opened': '2023-08-26'},
    {'id': 'manual-mine', 'name': '峰', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55753, 'lon': 139.91628, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'みね', 'opened': '2023-08-26'},
    {'id': 'manual-yoto3', 'name': '陽東3丁目', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55728, 'lon': 139.92323, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ようとうさんちょうめ', 'opened': '2023-08-26'},
    {'id': 'manual-utsunomiya-u-yoto', 'name': '宇都宮大学陽東キャンパス', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55704, 'lon': 139.93019, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'うつのみやだいがくようとうキャンパス', 'opened': '2023-08-26'},
    {'id': 'manual-hiraishi', 'name': '平石', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55507, 'lon': 139.93927, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ひらいし', 'opened': '2023-08-26'},
    {'id': 'manual-hiraishi-sho', 'name': '平石中央小学校前', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55483, 'lon': 139.94476, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ひらいしちゅうおうしょうがっこうまえ', 'opened': '2023-08-26'},
    {'id': 'manual-hiyamajoseki', 'name': '飛山城跡', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.54836, 'lon': 139.96342, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'とびやまじょうせき', 'opened': '2023-08-26'},
    {'id': 'manual-seiryo-koko', 'name': '清陵高校前', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.54495, 'lon': 139.9763, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'せいりょうこうこうまえ', 'opened': '2023-08-26'},
    {'id': 'manual-seihara-shimin', 'name': '清原地区市民センター前', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.54764, 'lon': 139.98424, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'せいはらちくしみんせんたあまえ', 'opened': '2023-08-26'},
    {'id': 'manual-green-stadium', 'name': 'グリーンスタジアム前', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.55583, 'lon': 139.98255, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ぐりいんすたじあむまえ', 'opened': '2023-08-26'},
    {'id': 'manual-yuinomori-nishi', 'name': 'ゆいの杜西', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.56716, 'lon': 139.98625, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ゆいのもりにし', 'opened': '2023-08-26'},
    {'id': 'manual-yuinomori-chuo', 'name': 'ゆいの杜中央', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.56772, 'lon': 139.99297, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ゆいのもりちゅうおう', 'opened': '2023-08-26'},
    {'id': 'manual-yuinomori-higashi', 'name': 'ゆいの杜東', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.56761, 'lon': 139.99879, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'ゆいのもりひがし', 'opened': '2023-08-26'},
    {'id': 'manual-hagadai', 'name': '芳賀台', 'pref': '栃木県', 'muni': '宇都宮市', 'ward': '',
     'lat': 36.56639, 'lon': 140.00539, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'はがだい', 'opened': '2023-08-26'},
    {'id': 'manual-hagacho-kanri', 'name': '芳賀町工業団地管理センター前', 'pref': '栃木県', 'muni': '芳賀町', 'ward': '',
     'lat': 36.56497, 'lon': 140.01067, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'はがちょうこうぎょうだんちかんりせんたあまえ', 'opened': '2023-08-26'},
    {'id': 'manual-kashinomori-koen', 'name': 'かしの森公園前', 'pref': '栃木県', 'muni': '芳賀町', 'ward': '',
     'lat': 36.57238, 'lon': 140.01456, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'かしのもりこうえんまえ', 'opened': '2023-08-26'},
    {'id': 'manual-haga-takanezawa', 'name': '芳賀・高根沢工業団地', 'pref': '栃木県', 'muni': '芳賀町', 'ward': '',
     'lat': 36.57844, 'lon': 140.01201, 'lines': [{'name': '宇都宮ライトレール線', 'company': '宇都宮ライトレール'}],
     'kana': 'はがたかねざわこうぎょうだんち', 'opened': '2023-08-26'},
    # 2023-04-01: 福岡市地下鉄七隈線延伸 (博多-天神南)
    {'id': 'manual-kushida-jinja', 'name': '櫛田神社前', 'pref': '福岡県', 'muni': '福岡市', 'ward': '博多区',
     'lat': 33.59129, 'lon': 130.41153, 'lines': [{'name': '七隈線', 'company': '福岡市'}],
     'kana': 'くしだじんじゃまえ', 'opened': '2023-04-01'},
    # 2024-03-25: 広電宮島線新站
    {'id': 'manual-matsukawamachi', 'name': '松川町', 'pref': '広島県', 'muni': '広島市', 'ward': '中区',
     'lat': 34.39111, 'lon': 132.47127, 'lines': [{'name': '広電１号線(宇品線)', 'company': '広島電鉄'}],
     'kana': 'まつかわまち', 'opened': '2024-03-25'},
    # 2025-03-15: 越後線新站
    {'id': 'manual-kamitokoro', 'name': '上所', 'pref': '新潟県', 'muni': '新潟市', 'ward': '中央区',
     'lat': 37.90694, 'lon': 139.04528, 'lines': [{'name': '越後線', 'company': '東日本旅客鉄道'}],
     'kana': 'かみところ', 'opened': '2025-03-15'},
]


def _s12_geojson():
    import zipfile
    z = zipfile.ZipFile(os.path.join(_RAW, 'S12-25_GML.zip'))
    return json.loads(z.read('S12-25_GML/UTF-8/S12-25_NumberOfPassengers.geojson'))


def build_supplement(ekidata_stations):
    """完整补充: 站名/坐标/线路/运营商/客流/都道府県"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from s12 import load_s12, _pick_window
    s12 = load_s12()['units']
    ek_names = {norm_name(s['name']) for s in ekidata_stations}
    pref_map = load_pref_map()
    g = _s12_geojson()

    # 从 geojson 建 (归一化站名, 运营商) -> 坐标/代码/线路
    meta = {}
    for f in g['features']:
        p = f['properties']
        if p['S12_006'] != 1:
            continue
        nn = norm_name(p['S12_001'])
        key = (nn, p['S12_002'])
        coords = f['geometry']['coordinates']
        mid_lat = sum(c[1] for c in coords) / len(coords)
        mid_lon = sum(c[0] for c in coords) / len(coords)
        meta.setdefault(key, []).append({
            'lat': mid_lat, 'lon': mid_lon,
            'code': p['S12_001c'], 'line': p['S12_003'],
        })

    # 候选: 归一化名不在 ekidata, 运行中
    cands = {}
    for (name, op), u in s12.items():
        nn = norm_name(name)
        if nn in ek_names or not nn:
            continue
        running = any((u['passengers'].get(y) or 0) > 0 for y in ('2023', '2024'))
        if not running:
            continue
        cands.setdefault(nn, []).append((u['name'], op, u))  # 原始名(S12_001)

    ek_coords = [(s['lat'], s['lon']) for s in ekidata_stations if s.get('lat')]

    stations = []
    for nn, entries in sorted(cands.items()):
        # 取 2024 客流最大的运营商记录
        best = None
        best_v = -1
        for name, op, u in entries:
            v = u['passengers'].get('2024') or u['passengers'].get('2023') or 0
            if v > best_v:
                best_v = v
                best = (name, op, u)
        name, op, u = best
        ms = meta.get((nn, op)) or meta.get((nn, u['op'])) or []
        if not ms:
            continue
        m = ms[0]
        # 坐标去重: 与最近 ekidata 站距离
        dmin = min(_dist(m['lat'], m['lon'], la, lo) for la, lo in ek_coords) if ek_coords else 1e9
        if dmin < 300:
            continue
        # 都道府県: 硬编码表(S12无此字段, Nominatim批查)
        pref = SUPPLEMENT_PREF.get(name, '')
        muni = SUPPLEMENT_MUNI.get(name, '')
        # 线路: 该站所有线路
        lines = sorted({x['line'] for x in ms})
        # 合并所有运营商的线路+客流
        all_lines = {}
        all_rid = {}
        for n2, op2, u2 in entries:
            for r in u2['routes']:
                all_lines.setdefault(r, op2)
            v2024 = u2['passengers'].get('2024')
            v2023 = u2['passengers'].get('2023')
            if v2024:
                all_rid[op2] = v2024
            elif v2023:
                all_rid[op2] = v2023
        stations.append({
            'id': 's12-' + m['code'],
            'name': name,
            'pref': pref,
            'muni': muni,
            'ward': '',
            'lat': round(m['lat'], 5),
            'lon': round(m['lon'], 5),
            'lines_raw': [{'name': r, 'company': all_lines[r]} for r in lines],
            'rid_v': max(all_rid.values()) if all_rid else None,
            'rid_y': 2024 if any(u2['passengers'].get('2024') for _, _, u2 in entries) else 2023,
        })
    return stations


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ekidata import load_ekidata
    eki = load_ekidata()
    sup = build_supplement(eki['stations'])
    print(f'补充站: {len(sup)}')
    for s in sup:
        print(f"  {s['name']} ({s['pref']}) rid={s['rid_v']} lines={[l['name'] for l in s['lines_raw']]}")
