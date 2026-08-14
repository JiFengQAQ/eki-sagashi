# -*- coding: utf-8 -*-
import pytest
from ekidata import load_ekidata
from kana import (load_wd_kana, load_osm_kana, build_kana,
                  kana2roma, kana2roma_ou)


class TestLoadSources:
    def test_wd_kana(self):
        wd = load_wd_kana()
        assert len(wd) > 5000
        # 原始值(未按站名清洗, 尾えき保留在源数据)
        assert wd.get('新宿') == 'しんじゅくえき'

    def test_osm_kana(self):
        osm = load_osm_kana()
        assert len(osm) > 3000
        assert osm.get('新子安')[0] == 'しんこやす'

    def test_osm_romaji(self):
        # roma 由 kana 确定性派生; OSM name:ja_rm 字段保留但不再用于 roma 生成
        osm = load_osm_kana()
        assert osm.get('新子安')[1] == 'Shin-Koyasu'


class TestKana2Roma:
    """确定性黑本式转换: 不变量 roma == kana2roma(kana)"""

    def test_basic(self):
        assert kana2roma('しんじゅく') == 'shinjuku'
        assert kana2roma('とうきょう') == 'tokyo'
        assert kana2roma('おおさか') == 'osaka'
        assert kana2roma('きょうと') == 'kyoto'
        assert kana2roma('よこはま') == 'yokohama'

    def test_long_vowel(self):
        # お段長音缩 o; う段長音保留 uu
        assert kana2roma('ふくおかくうこう') == 'fukuokakuuko'
        assert kana2roma('ゆうらくちょう') == 'yuurakucho'
        assert kana2roma('はままつちょう') == 'hamamatsucho'
        assert kana2roma('おおいまち') == 'oimachi'
        assert kana2roma('こうぞうじ') == 'kozoji'

    def test_long_vowel_ou(self):
        # 展开形(搜索变体)
        assert kana2roma_ou('とうきょう') == 'toukyou'
        assert kana2roma_ou('くうこう') == 'kuukou'
        assert kana2roma_ou('おおさか') == 'oosaka'
        assert kana2roma_ou('ゆうらくちょう') == 'yuurakuchou'

    def test_youon(self):
        assert kana2roma('かごしまちゅうおう') == 'kagoshimachuuo'
        assert kana2roma('はらじゅく') == 'harajuku'
        assert kana2roma('ちょうふ') == 'chofu'
        assert kana2roma('よつや') == 'yotsuya'
        assert kana2roma('しんゆりがおか') == 'shinyurigaoka'

    def test_sokuon_hannin(self):
        assert kana2roma('しんばし') == 'shimbashi'
        assert kana2roma('にっぽんばし') == 'nippombashi'
        assert kana2roma('さくらしんまち') == 'sakurashimmachi'
        assert kana2roma('はっちょうぼり') == 'hacchobori'
        assert kana2roma('てんのうじ') == 'tennoji'

    def test_tsu_dzu(self):
        assert kana2roma('ながつた') == 'nagatsuta'
        assert kana2roma('つきじ') == 'tsukiji'

    def test_ei_kept(self):
        assert kana2roma('せいあいちゅうこうまえ') == 'seiaichuukomae'
        assert kana2roma('けいおうたませんたあ') == 'keiotamasentaa'


class TestBuildKana:
    @classmethod
    def setup_class(cls):
        eki = load_ekidata()
        cls.stations = eki['stations']
        cls.kana = build_kana(cls.stations)

    def test_no_pykakasi(self):
        # kana 非空时 roma 恒等于确定性转换, 无任何汉字转读残留
        for st in self.stations:
            k, r, r_ou, _ = self.kana[st['id']]
            if k:
                assert r == kana2roma(k), st['name']
                assert r_ou == kana2roma_ou(k), st['name']
            else:
                assert r == '' and r_ou == '', st['name']

    def test_no_garbage(self):
        for st in self.stations:
            for f in (0, 1, 2):
                v = self.kana[st['id']][f]
                assert 'kurikaesi' not in v and '*' not in v, st['name']
                assert not any(c in v for c in '（）()'), st['name']

    def test_coverage(self):
        # 覆盖率是数据源(Wikidata/OSM)事实; 有kana必有roma
        no_kana = [s['name'] for s in self.stations if not self.kana[s['id']][0]]
        no_roma = [s['name'] for s in self.stations if not self.kana[s['id']][1]]
        assert len(no_kana) == len(no_roma)
        assert len(no_kana) / len(self.stations) < 0.25

    def test_known_readings(self):
        cases = {
            '新宿': 'しんじゅく',
            '代々木': 'よよぎ',
            '東京': 'とうきょう',
            '大阪': 'おおさか',
            '新子安': 'しんこやす',
            '市ケ谷': 'いちがや',
            '御茶ノ水': 'おちゃのみず',
            '神戸': 'こうべ',
        }
        for name, expect in cases.items():
            st = next(s for s in self.stations if s['name'] == name)
            assert self.kana[st['id']][0] == expect, name

    def test_romaji(self):
        st = next(s for s in self.stations if s['name'] == '新宿')
        assert self.kana[st['id']][1] == 'shinjuku'
        st = next(s for s in self.stations if s['name'] == '東京')
        assert self.kana[st['id']][1] == 'tokyo'
        st = next(s for s in self.stations if s['name'] == '福岡空港')
        assert self.kana[st['id']][1] == 'fukuokakuuko'

    def test_exception_overrides_external(self):
        # 神戸: 外部源错读かんべ, 人工例外必须覆盖
        st = next(s for s in self.stations if s['name'] == '神戸')
        assert self.kana[st['id']][0] == 'こうべ'

    def test_same_name_diff_pref(self):
        # 东京日本橋 にほんばし; 大阪日本橋 にっぽんばし
        hits = [s for s in self.stations if s['name'] == '日本橋']
        by_pref = {s['pref']: self.kana[s['id']][0] for s in hits}
        assert by_pref.get('東京都') == 'にほんばし'
        assert by_pref.get('大阪府') == 'にっぽんばし'

    def test_exception_keys_are_normed(self):
        # EXCEPTIONS 键必须等于 norm 口径(剥括号/々展开), 否则 build_kana 匹配不到
        from kana import EXCEPTIONS
        from normalize import canonical_kanji, norm_station_name
        bad = [(k, canonical_kanji(norm_station_name(k))) for k in EXCEPTIONS
               if canonical_kanji(norm_station_name(k)) != k]
        assert bad == []

    def test_kagoshima_exception(self):
        st = next(s for s in self.stations if s['name'] == '鹿児島中央')
        assert self.kana[st['id']][0] == 'かごしまちゅうおう'
