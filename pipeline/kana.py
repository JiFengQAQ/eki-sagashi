# -*- coding: utf-8 -*-
"""站名读音合并:Wikidata P1814 + OSM name:ja-Hira/ja_rm 优先, pykakasi 兜底, 例外词典修正"""
import json
import os

import pykakasi

from normalize import canonical_kanji, norm_kana, norm_roma, norm_station_name

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# pykakasi 已知错误/常见专有名词修正(键=站名, 值=平假名)
EXCEPTIONS = {
    '鹿児島': 'かごしま', '鹿児島中央': 'かごしまちゅうおう',
    '我孫子': 'あびこ', '姪浜': 'めいのはま',
    '市ヶ谷': 'いちがや', '御茶ノ水': 'おちゃのみず',
    '渋谷': 'しぶや', '新宿': 'しんじゅく', '代々木': 'よよぎ',
    '東京': 'とうきょう', '大阪': 'おおさか', '新潟': 'にいがた',
    '函館': 'はこだて', '旭川': 'あさひかわ', '札幌': 'さっぽろ',
    '横浜': 'よこはま', '名古屋': 'なごや', '京都': 'きょうと',
    '神戸': 'こうべ', '広島': 'ひろしま', '博多': 'はかた',
    '那覇': 'なは', '松山': 'まつやま', '高知': 'こうち',
    '徳島': 'とくしま', '金沢': 'かなざわ', '富山': 'とやま',
    '長野': 'ながの', '甲府': 'こうふ', '静岡': 'しずおか',
    '岐阜': 'ぎふ', '大津': 'おおつ', '奈良': 'なら',
    '和歌山': 'わかやま', '鳥取': 'とっとり', '松江': 'まつえ',
    '山口': 'やまぐち', '佐賀': 'さが', '長崎': 'ながさき',
    '熊本': 'くまもと', '大分': 'おおいた', '宮崎': 'みやざき',
    '千葉': 'ちば', '水戸': 'みと', '宇都宮': 'うつのみや',
    '前橋': 'まえばし', '秋田': 'あきた', '盛岡': 'もりおか',
    '青森': 'あおもり', '山形': 'やまがた', '仙台': 'せんだい',
    '福島': 'ふくしま', '郡山': 'こおりやま', '高崎': 'たかさき',
    '大宮': 'おおみや', '川崎': 'かわさき', '鎌倉': 'かまくら',
    '小田原': 'おだわら', '熱海': 'あたみ', '沼津': 'ぬまづ',
    '浜松': 'はままつ', '豊橋': 'とよはし', '岡崎': 'おかざき',
    '四日市': 'よっかいち', '新大阪': 'しんおおさか', '新神戸': 'しんこうべ',
    '姫路': 'ひめじ', '岡山': 'おかやま', '倉敷': 'くらしき',
    '福山': 'ふくやま', '下関': 'しものせき', '小倉': 'こくら',
    '久留米': 'くるめ', '別府': 'べっぷ', '八代': 'やつしろ',
    '八戸': 'はちのへ', '新函館北斗': 'しんはこだてほくと',
    '福岡': 'ふくおか', '新横浜': 'しんよこはま', '品川': 'しながわ',
    '上野': 'うえの', '渋谷': 'しぶや', '池袋': 'いけぶくろ',
    '秋葉原': 'あきはばら', '吉祥寺': 'きちじょうじ', '立川': 'たちかわ',
    '横須賀': 'よこすか', '成田': 'なりた', '羽田空港': 'はねだくうこう',
    '成田空港': 'なりたくうこう', '関西空港': 'かんさいくうこう',
    '中部国際空港': 'ちゅうぶこくさいくうこう', '福岡空港': 'ふくおかくうこう',
}


def load_wd_kana(path=None):
    if path is None:
        path = os.path.join(_REPO_ROOT, 'data', 'raw', 'wd_stations.json')
    d = json.load(open(path, encoding='utf-8'))
    out = {}
    for r in d['results']['bindings']:
        lbl = r.get('stationLabel', {})
        if lbl.get('xml:lang') != 'ja':
            continue
        name = canonical_kanji(norm_station_name(lbl.get('value', '')))
        if not name:
            continue
        kana = r.get('kana', {}).get('value', '')
        if not kana:
            continue
        kana = norm_kana(kana)
        if kana.endswith('えき'):
            kana = kana[:-2]
        out[name] = kana
    return out


def load_osm_kana(path=None):
    if path is None:
        path = os.path.join(_REPO_ROOT, 'data', 'raw', 'osm_stations.json')
    d = json.load(open(path, encoding='utf-8'))
    out = {}
    for e in d.get('elements', []):
        t = e.get('tags', {})
        name = canonical_kanji(norm_station_name(t.get('name') or t.get('name:ja') or ''))
        if not name:
            continue
        kana = t.get('name:ja-Hira') or t.get('name:ja_kana') or ''
        roma = t.get('name:ja_rm') or ''
        if kana or roma:
            out[name] = (norm_kana(kana) if kana else '', norm_roma(roma) if roma else '')
    return out


_kakasi = None


def _pykakasi():
    global _kakasi
    if _kakasi is None:
        _kakasi = pykakasi.kakasi()
    return _kakasi


def _pykakasi_kana(text):
    return ''.join(item['hira'] for item in _pykakasi().convert(text))


def _pykakasi_roma(text):
    return norm_roma(''.join(item['hepburn'] for item in _pykakasi().convert(text)))


def build_kana(stations, wd=None, osm=None):
    """每站返回(id -> (kana, romaji)); 优先级: OSM > Wikidata > pykakasi(+例外);
    查找键用canonical_kanji(ケ->ヶ、々展开), 与WD/OSM表记统一"""
    if wd is None:
        wd = load_wd_kana()
    if osm is None:
        osm = load_osm_kana()
    result = {}
    for st in stations:
        name = st['name']
        norm = canonical_kanji(norm_station_name(name))
        kana, roma = '', ''
        os_entry = osm.get(norm)
        if os_entry and os_entry[0]:
            kana = os_entry[0]
        elif norm in wd:
            kana = wd[norm]
        else:
            kana = norm_kana(EXCEPTIONS.get(name, _pykakasi_kana(name)))
        if os_entry and os_entry[1]:
            roma = os_entry[1]
        else:
            roma = _pykakasi_roma(name)
        result[st['id']] = (kana, roma)
    return result
