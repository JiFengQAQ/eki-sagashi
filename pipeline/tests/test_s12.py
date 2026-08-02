# -*- coding: utf-8 -*-
import pytest
from s12 import load_s12, join_ridership


class TestLoadS12:
    @classmethod
    def setup_class(cls):
        cls.s12 = load_s12()

    def test_feature_count(self):
        assert len(self.s12['units']) >= 9000

    def test_known_values_2024(self):
        u = self.s12['units'].get(('新宿', '東日本旅客鉄道'))
        assert u is not None
        assert u['passengers']['2024'] == 1333618
        u = self.s12['units'].get(('渋谷', '東急電鉄'))
        assert u is not None
        assert u['passengers']['2024'] == 1770430
        u = self.s12['units'].get(('大阪', '西日本旅客鉄道'))
        assert u is not None
        assert u['passengers']['2024'] == 751006

    def test_known_values_2019(self):
        u = self.s12['units'].get(('新宿', '東日本旅客鉄道'))
        assert u['passengers']['2019'] == 1578732
        u = self.s12['units'].get(('渋谷', '東急電鉄'))
        assert u['passengers']['2019'] == 1381618
        u = self.s12['units'].get(('大阪', '西日本旅客鉄道'))
        assert u['passengers']['2019'] == 845370

    def test_year_range(self):
        for u in self.s12['units'].values():
            for y in range(2011, 2025):
                assert str(y) in u['passengers']


class TestJoinRidership:
    @classmethod
    def setup_class(cls):
        cls.s12 = load_s12()
        cls.rid = join_ridership(cls.s12)

    def test_station_count(self):
        assert len(self.rid) >= 8500

    def test_coverage(self):
        with_val = sum(1 for r in self.rid.values() if r['rid']['v'])
        assert with_val / len(self.rid) >= 0.75

    def test_shinjuku(self):
        r = self.rid['1130207']  # 代々木? 用名称查
        # 新宿 = 新宿 group 1130207? 实际是 1130207? 找新宿
        shinjuku = next(v for v in self.rid.values() if v['name'] == '新宿')
        assert shinjuku['rid']['v'] == 1578732
        assert shinjuku['rid']['y'] == 2019
        # 运营商明细含JR
        ops = {p['op'] for p in shinjuku['per']}
        assert '東日本旅客鉄道' in ops

    def test_shibuya(self):
        shibuya = next(v for v in self.rid.values() if v['name'] == '渋谷')
        assert shibuya['rid']['v'] == 1381618
        assert shibuya['rid']['y'] == 2019

    def test_osaka(self):
        osaka = next(v for v in self.rid.values() if v['name'] == '大阪')
        # 大阪駅: JR西 845370(2019) vs 大阪メトロ御堂筋線 442297(2019)? 取最大
        assert osaka['rid']['v'] == 845370

    def test_tokyo_jr_central_fallback(self):
        # 東京 JR東海: 2015-2018 均为0, 2019 有值 -> 取2019
        tokyo = next(v for v in self.rid.values() if v['name'] == '東京')
        jr_central = [p for p in tokyo['per'] if p['op'] == '東海旅客鉄道']
        assert jr_central and jr_central[0]['y'] == 2019
        assert jr_central[0]['v'] == 188476

    def test_no_data_station(self):
        # 至少存在无数据站(rid.v 为 None), 且不影响其他站
        assert any(r['rid']['v'] is None for r in self.rid.values())

    def test_rid_ordering_known(self):
        # 新宿 > 大阪 > 函館
        vals = {r['name']: r['rid']['v'] for r in self.rid.values()}
        assert vals['新宿'] > vals['大阪'] > vals['函館'] > 0

    def test_igr_alias(self):
        # 第三セクター别名匹配
        igr = [v for v in self.rid.values() if v['name'] == '盛岡']
        assert igr
        ops = {p['op'] for p in igr[0]['per']}
        assert 'アイジーアールいわて銀河鉄道' in ops
