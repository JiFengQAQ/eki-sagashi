# -*- coding: utf-8 -*-
import pytest
from ekidata import load_ekidata, parse_muni


class TestParseMuni:
    def test_normal_city(self):
        assert parse_muni('北海道函館市若松町12-13') == ('函館市', '')
        assert parse_muni('函館市亀田本町') == ('函館市', '')

    def test_ordinance_designated_city(self):
        assert parse_muni('京都市下京区烏丸通塩小路下ル東塩小路町') == ('京都市', '下京区')
        assert parse_muni('札幌市手稲区手稲星置1条9丁目') == ('札幌市', '手稲区')
        assert parse_muni('さいたま市大宮区錦町') == ('さいたま市', '大宮区')

    def test_county_village(self):
        assert parse_muni('亀田郡七飯町大字大中山') == ('七飯町', '亀田郡')
        assert parse_muni('北安曇郡白馬村北城') == ('白馬村', '北安曇郡')

    def test_special_ward(self):
        assert parse_muni('東京都新宿区西新宿') == ('新宿区', '')
        assert parse_muni('東京都千代田区丸の内1-9-1') == ('千代田区', '')

    def test_no_muni_returns_none(self):
        assert parse_muni('') == (None, None)
        assert parse_muni('東京都') == (None, None)


class TestLoadEkidata:
    @classmethod
    def setup_class(cls):
        cls.data = load_ekidata()

    def test_station_count(self):
        assert len(self.data['stations']) >= 8500
        assert self.data['active_count'] == len(self.data['stations'])

    def test_lines_count(self):
        assert len(self.data['lines']) >= 600

    def test_station_fields(self):
        s = next(x for x in self.data['stations'] if x['id'] == '1130207')  # 代々木
        assert s['name'] == '代々木'
        assert s['pref'] == '東京都'
        assert s['muni'] == '渋谷区'
        line_names = {l['name'] for l in s['lines']}
        assert 'JR山手線' in line_names
        assert 'JR中央・総武線' in line_names
        assert '都営大江戸線' in line_names

    def test_kyoto_station(self):
        s = next((x for x in self.data['stations'] if x['id'] == '1160120'), None)  # 京都駅
        if s:
            assert s['muni'] == '京都市'
            assert s['ward'] == '下京区'
            assert len(s['lines']) == 7

    def test_hakodate_station(self):
        s = next(x for x in self.data['stations'] if x['id'] == '1110101')
        assert s['name'] == '函館'
        assert s['pref'] == '北海道'
        assert s['muni'] == '函館市'

    def test_muni_coverage(self):
        missing = [s['id'] for s in self.data['stations'] if not s['muni']]
        assert missing == []

    def test_company_attached(self):
        s = next(x for x in self.data['stations'] if x['id'] == '1130207')
        ops = {l['company'] for l in s['lines']}
        assert 'JR東日本' in ops

    def test_coords_present(self):
        s = next(x for x in self.data['stations'] if x['id'] == '1130207')
        assert abs(s['lat'] - 35.683) < 0.01
        assert abs(s['lon'] - 139.702) < 0.01
