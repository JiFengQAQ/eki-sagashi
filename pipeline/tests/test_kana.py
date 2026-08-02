# -*- coding: utf-8 -*-
import pytest
from ekidata import load_ekidata
from kana import load_wd_kana, load_osm_kana, build_kana


class TestLoadSources:
    def test_wd_kana(self):
        wd = load_wd_kana()
        assert len(wd) > 5000
        # 行徳 -> ぎょうとく (样本里见过, 去尾えき)
        assert wd.get('行徳') == 'ぎょうとく'
        assert wd.get('新宿') == 'しんじゅく'

    def test_osm_kana(self):
        osm = load_osm_kana()
        assert len(osm) > 3000
        assert osm.get('新子安')[0] == 'しんこやす'

    def test_osm_romaji(self):
        osm = load_osm_kana()
        assert osm.get('新子安')[1] == 'shinkoyasu'


class TestBuildKana:
    @classmethod
    def setup_class(cls):
        eki = load_ekidata()
        cls.stations = eki['stations']
        cls.kana = build_kana(cls.stations)

    def test_coverage(self):
        no_kana = [s['name'] for s in self.stations if not self.kana[s['id']][0]]
        no_roma = [s['name'] for s in self.stations if not self.kana[s['id']][1]]
        assert len(no_kana) / len(self.stations) < 0.005
        assert len(no_roma) / len(self.stations) < 0.005

    def test_known_readings(self):
        cases = {
            '新宿': 'しんじゅく',
            '代々木': 'よよぎ',
            '東京': 'とうきょう',
            '大阪': 'おおさか',
            '新子安': 'しんこやす',
            '市ケ谷': 'いちがや',
            '御茶ノ水': 'おちゃのみず',
        }
        for name, expect in cases.items():
            st = next(s for s in self.stations if s['name'] == name)
            assert self.kana[st['id']][0] == expect, name

    def test_romaji(self):
        st = next(s for s in self.stations if s['name'] == '新宿')
        assert self.kana[st['id']][1] == 'shinjuku'
        st = next(s for s in self.stations if s['name'] == '東京')
        assert self.kana[st['id']][1] == 'tokyo'

    def test_kagoshima_exception(self):
        # pykakasi 鹿児島->かこしま 错误, 例外词典修正
        st = next(s for s in self.stations if s['name'] == '鹿児島中央')
        assert self.kana[st['id']][0] == 'かごしまちゅうおう'
