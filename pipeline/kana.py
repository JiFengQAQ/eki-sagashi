# -*- coding: utf-8 -*-
"""站名读音: 可信来源(人工例外 > OSM > Wikidata) 只做读音; roma 从 kana 确定性黑本式转换
不变量: roma == kana2roma(kana) 对每个站成立; 无可信读音的站 kana/roma 为空(不猜)"""
import json
import os
import re

from normalize import canonical_kanji, norm_kana, norm_station_name

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 人工确认读音(键=站名canonical, 值=平假名); 最高优先级, 覆盖外部数据错误
EXCEPTIONS = {
    '鹿児島': 'かごしま', '鹿児島中央': 'かごしまちゅうおう',
    '我孫子': 'あびこ', '姪浜': 'めいのはま',
    '市ヶ谷': 'いちがや', '御茶ノ水': 'おちゃのみず',
    '渋谷': 'しぶや', '新宿': 'しんじゅく', '代々木': 'よよぎ',
    '東京': 'とうきょう', '大阪': 'おおさか', '新潟': 'にいがた',
    '函館': 'はこだて', '旭川': 'あさひかわ', '札幌': 'さっぽろ',
    '横浜': 'よこはま', '名古屋': 'なごや', '京都': 'きょうと',
    '神戸': 'こうべ', '広島': 'ひろしま', '博多': 'はかた',
    '高輪ゲートウェイ': 'たかなわげーとうぇい',
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
    '上野': 'うえの', '池袋': 'いけぶくろ',
    '秋葉原': 'あきはばら', '吉祥寺': 'きちじょうじ', '立川': 'たちかわ',
    '横須賀': 'よこすか', '成田': 'なりた', '羽田空港': 'はねだくうこう',
    '成田空港': 'なりたくうこう', '関西空港': 'かんさいくうこう',
    '中部国際空港': 'ちゅうぶこくさいくうこう', '福岡空港': 'ふくおかくうこう',
}

# 同名异读站: (站名, 都道府県) -> 平假名
PREF_EXCEPTIONS = {
    ('日本橋', '東京都'): 'にほんばし',
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
        out[name] = norm_kana(kana)
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
        en = (t.get('name:en') or '').strip()
        if kana or roma or en:
            out[name] = (norm_kana(kana) if kana else '',
                         roma.strip(),
                         en)
    return out


_PAREN_RE = re.compile(r'[（(][^）)]*[)）]')


def _clean_kana(kana, st_name):
    """按ekidata站名清洗假名: norm(片->平/ー展开) ->
    括号: 站名含括号 -> 剥括号内容(别名读音); 站名无括号 -> 去括号字符保留内容(注音)
    尾えき: ekidata站名(norm)不含駅时剥除"""
    k = norm_kana(kana)
    k = _PAREN_RE.sub('', k) if ('（' in st_name or '(' in st_name) \
        else k.replace('（', '').replace('）', '').replace('(', '').replace(')', '')
    k = k.replace('＊', '').replace('*', '')
    if not norm_station_name(st_name).endswith('駅') and k.endswith('えき'):
        k = k[:-2]
    return k.strip()


# ---------- kana -> roma 确定性黑本式 ----------

_ROWS = {
    'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
    'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
    'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
    'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
    'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
    'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
    'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
    'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
    'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
    'わ': 'wa', 'を': 'o', 'ん': 'n',
    'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go',
    'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
    'だ': 'da', 'ぢ': 'ji', 'づ': 'zu', 'で': 'de', 'ど': 'do',
    'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo',
    'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po',
    'ぁ': 'a', 'ぃ': 'i', 'ぅ': 'u', 'ぇ': 'e', 'ぉ': 'o',
    'ゃ': 'ya', 'ゅ': 'yu', 'ょ': 'yo',
    'ゔ': 'vu',
}
_YOON = {'き': 'ky', 'し': 'sh', 'ち': 'ch', 'に': 'ny', 'ひ': 'hy',
         'み': 'my', 'り': 'ry', 'ぎ': 'gy', 'じ': 'j', 'ぢ': 'j',
         'び': 'by', 'ぴ': 'py'}
# 外来语小假名组合(大假名+ぁぃぅぇぉ): 前字+小字 -> 罗马音
_SMALL_COMBO = {
    'うぇ': 'we', 'うぃ': 'wi', 'うぉ': 'wo', 'うぁ': 'wa',
    'いぇ': 'ye',
    'ゔぁ': 'va', 'ゔぃ': 'vi', 'ゔぇ': 've', 'ゔぉ': 'vo',
    'ふぁ': 'fa', 'ふぃ': 'fi', 'ふぇ': 'fe', 'ふぉ': 'fo',
    'てぃ': 'ti', 'てゅ': 'tyu', 'とぅ': 'tu',
    'でぃ': 'di', 'でゅ': 'dyu', 'どぅ': 'du',
    'しぇ': 'she', 'じぇ': 'je', 'ちぇ': 'che', 'ぢぇ': 'je',
    'つぁ': 'tsa', 'つぃ': 'tsi', 'つぇ': 'tse', 'つぉ': 'tso',
    'くぁ': 'kwa', 'くぃ': 'kwi', 'くぇ': 'kwe', 'くぉ': 'kwo',
    'ぐぁ': 'gwa', 'ぐぃ': 'gwi', 'ぐぇ': 'gwe', 'ぐぉ': 'gwo',
    'きぇ': 'kye', 'ぎぇ': 'gye', 'にぇ': 'nye', 'ひぇ': 'hye',
    'びぇ': 'bye', 'ぴぇ': 'pye', 'みぇ': 'mye', 'りぇ': 'rye',
}


def _kana_to_roma(kana, long_vowel):
    """确定性黑本式转换; long_vowel=True 时お段长音展开为 ou (搜索变体用)"""
    out = []
    prev_ch = ''
    i = 0
    while i < len(kana):
        ch = kana[i]
        if ch in 'ゃゅょ':
            combo = prev_ch + ch
            if combo in _SMALL_COMBO:
                out[-1] = _SMALL_COMBO[combo]
            elif prev_ch in _YOON:
                out[-1] = _YOON[prev_ch] + _ROWS[ch][1:]
            else:
                out.append(_ROWS.get(ch, ch))
            prev_ch = ''
            i += 1
            continue
        if ch in 'ぁぃぅぇぉ':
            combo = prev_ch + ch
            if combo in _SMALL_COMBO:
                out[-1] = _SMALL_COMBO[combo]
            else:
                out.append(_ROWS.get(ch, ch))
            prev_ch = ''
            i += 1
            continue
        if ch == 'っ':
            out.append('__TSU__')
            prev_ch = ''
            i += 1
            continue
        out.append(_ROWS.get(ch, ch))
        prev_ch = ch
        i += 1
    res = ''
    for j, s in enumerate(out):
        if s == '__TSU__':
            nxt = out[j + 1] if j + 1 < len(out) else ''
            if nxt and nxt != '__TSU__':
                res += nxt[0]
            continue
        res += s
    # 撥音: ん+b/p/m -> m(黑本式双写: shimbashi, shimmachi)
    res = re.sub(r'n([bpm])', r'm\1', res)
    if long_vowel:
        # 長音展开形: お段長音 ou/oo 原样(とうきょう->toukyou), う段 uu 原样
        return res
    # 无長音形: お段長音(ou/oo)缩 o; う段長音(uu)保留(空港->kuuko)
    return res.replace('ou', 'o').replace('oo', 'o')


def kana2roma(kana):
    """标准黑本式无長音表记: お段長音->o, う段長音保留 uu"""
    return _kana_to_roma(kana, long_vowel=False)


def kana2roma_ou(kana):
    """長音展开形(搜索变体): とうきょう->toukyou, くうこう->kuukou"""
    return _kana_to_roma(kana, long_vowel=True)


def load_wiki_kana(path=None):
    """Wikipedia 首句注音(wikitext首段抓取, 人工校对): 站名 -> 平假名
    仅用于补 OSM/WD 缺口; 已清洗(剥えき/ていりゅうじょう/含・丢弃/错位重定向丢弃)"""
    if path is None:
        path = os.path.join(_REPO_ROOT, 'data', 'raw', 'wiki_kana.json')
    if not os.path.exists(path):
        return {}
    return {k: v for k, v in json.load(open(path, encoding='utf-8')).items() if v}


def build_kana(stations, wd=None, osm=None, wiki=None):
    """每站返回(id -> (kana, romaji, romaji_ou, en));
    读音优先级: PREF_EXCEPTIONS > EXCEPTIONS > OSM > Wikidata > Wikipedia注音; 都无则留空
    roma/roma_ou 由 kana 确定性转换, 不依赖汉字"""
    if wd is None:
        wd = load_wd_kana()
    if osm is None:
        osm = load_osm_kana()
    if wiki is None:
        wiki = load_wiki_kana()
    result = {}
    for st in stations:
        name = st['name']
        norm = canonical_kanji(norm_station_name(name))
        kana, en = '', ''
        pf = (name, st.get('pref', ''))
        if pf in PREF_EXCEPTIONS:
            kana = PREF_EXCEPTIONS[pf]
        elif norm in EXCEPTIONS:
            kana = EXCEPTIONS[norm]
        else:
            os_entry = osm.get(norm)
            if os_entry and os_entry[0]:
                kana = os_entry[0]
            elif norm in wd:
                kana = wd[norm]
            elif name in wiki:
                kana = wiki[name]
            if os_entry:
                en = os_entry[2]
        kana = _clean_kana(kana, name) if kana else ''
        roma = kana2roma(kana) if kana else ''
        roma_ou = kana2roma_ou(kana) if kana else ''
        result[st['id']] = (kana, roma, roma_ou, en)
    return result
