# -*- coding: utf-8 -*-
import json
import os
import pytest

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')


class TestBuiltData:
    @classmethod
    def setup_class(cls):
        cls.stations = json.load(open(os.path.join(DATA, 'stations.json'), encoding='utf-8'))
        cls.meta = json.load(open(os.path.join(DATA, 'meta.json'), encoding='utf-8'))

    def test_station_count(self):
        assert len(self.stations) >= 8500

    def test_kana_coverage(self):
        # 覆盖率是数据源(Wikidata/OSM)事实; 正确性不变量是 kana非空 <=> roma非空
        miss = [s for s in self.stations if not s.get('kana')]
        assert len(miss) / len(self.stations) < 0.25
        assert all((bool(s.get('kana')) == bool(s.get('roma'))) for s in self.stations)

    def test_roma_coverage(self):
        miss = [s for s in self.stations if not s.get('roma')]
        assert len(miss) / len(self.stations) < 0.25

    def test_rid_coverage(self):
        with_val = [s for s in self.stations if s.get('rid', {}).get('v')]
        assert len(with_val) / len(self.stations) >= 0.75

    def test_muni_coverage(self):
        miss = [s for s in self.stations if not s.get('muni')]
        assert miss == []

    def test_shinjuku(self):
        s = next(x for x in self.stations if x['name'] == '新宿')
        assert s['rid']['v'] == 1578732
        assert s['rid']['y'] == 2019
        assert s['kana'] == 'しんじゅく'
        line_names = {l['n'] for l in s['lines']}
        assert 'JR山手線' in line_names
        assert '都営大江戸線' in line_names

    def test_line_colors_present(self):
        s = next(x for x in self.stations if x['name'] == '新宿')
        colored = [l for l in s['lines'] if l.get('c')]
        assert len(colored) >= 2
        yamanote = next(l for l in s['lines'] if l['n'] == 'JR山手線')
        assert yamanote['c'] == '#9acd32'

    def test_station_fields_complete(self):
        for s in self.stations[:50]:
            for f in ('id', 'name', 'kana', 'roma', 'pref', 'muni', 'lat', 'lon'):
                assert f in s, (s['name'], f)

    def test_meta(self):
        assert self.meta['station_count'] == len(self.stations)
        assert self.meta['kana_coverage'] >= 0.75
        assert self.meta['rid_coverage'] >= 0.75
        assert self.meta['sources']
        assert self.meta['built_at']

    def test_kyoto_ward(self):
        s = next(x for x in self.stations if x['name'] == '京都')
        assert s['muni'] == '京都市'
        assert s['ward'] == '下京区'

    def test_no_data_station_has_null_rid(self):
        no = [s for s in self.stations if not s.get('rid', {}).get('v')]
        assert no
        for s in no:
            assert s['rid']['v'] is None or s['rid']['v'] == 0
