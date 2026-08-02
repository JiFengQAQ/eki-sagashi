# -*- coding: utf-8 -*-
import pytest
from kinjo import load_kinjo_rules, build_line_orders, classify


class TestKinjo:
    @classmethod
    def setup_class(cls):
        cls.rules = load_kinjo_rules()
        cls.orders = build_line_orders()
        cls.regions = ['東京', '大阪', '福岡', '新潟', '仙台']

    def in_regions(self, name):
        return classify(name, self.rules, self.orders)

    def test_tokyo_inside(self):
        for name in ['新宿', '東京', '宇都宮', '黒磯', '大宮', '横浜', '千葉', '高崎',
                     '長野', '白馬', '水戸', '銚子', '熱海', '伊東']:
            assert '東京' in self.in_regions(name), f'{name} 应在東京近郊区間'

    def test_tokyo_outside(self):
        for name in ['那須塩原', '南小谷', '函館', '鹿児島中央', '札幌', '新潟', '仙台',
                     '金沢', '福井', '新宿御苑前']:
            assert '東京' not in self.in_regions(name), f'{name} 不应在東京近郊区間'

    def test_osaka(self):
        for name in ['大阪', '京都', '神戸', '奈良', '天王寺', '新大阪', '三ノ宮',
                     '姫路', '和歌山', '米原', '柘植', '関西空港']:
            assert '大阪' in self.in_regions(name), f'{name} 应在大阪近郊区間'
        assert '大阪' not in self.in_regions('福井')
        assert '大阪' not in self.in_regions('鳥取')

    def test_fukuoka(self):
        for name in ['博多', '小倉', '門司港', '鳥栖', '吉塚', '折尾', '行橋']:
            assert '福岡' in self.in_regions(name), f'{name} 应在福岡近郊区間'
        assert '福岡' not in self.in_regions('久留米')

    def test_niigata(self):
        for name in ['新潟', '新発田', '柏崎', '長岡', '直江津', '弥彦', '新津']:
            assert '新潟' in self.in_regions(name), f'{name} 应在新潟近郊区間'
        assert '新潟' not in self.in_regions('糸魚川')

    def test_sendai(self):
        for name in ['仙台', '郡山', '福島', '山形', '新庄', '石巻', '女川', '利府', '平泉']:
            assert '仙台' in self.in_regions(name), f'{name} 应在仙台近郊区間'
        assert '仙台' not in self.in_regions('盛岡')

    def test_coverage(self):
        # 全部规则解析成功: 每区域至少5条线路规则
        for r in self.regions:
            assert len(self.rules[r]) >= 5, r

    def test_all_stations_classified(self):
        # 分类器对全站可运行(不抛异常)
        from ekidata import load_ekidata
        eki = load_ekidata()
        for st in eki['stations'][:200]:
            classify(st['name'], self.rules, self.orders)
