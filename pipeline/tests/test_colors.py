# -*- coding: utf-8 -*-
import pytest
from colors import build_color_table, color_for


class TestColorTable:
    @classmethod
    def setup_class(cls):
        cls.table = build_color_table()

    def test_jr_base_lines(self):
        assert color_for(self.table, 'JR山手線', 'JR東日本') == '#9acd32'
        assert color_for(self.table, 'JR中央線(快速)', 'JR東日本') == '#f15a22'
        assert color_for(self.table, 'JR中央・総武線', 'JR東日本') == '#ffd400'
        assert color_for(self.table, 'JR東海道本線(東京～熱海)', 'JR東日本') == '#f68b1e'
        assert color_for(self.table, '大阪環状線', 'JR西日本') == '#e80000'
        assert color_for(self.table, 'JR常磐線(上野～取手)', 'JR東日本') == '#00b261'

    def test_jr_running_system(self):
        assert color_for(self.table, 'JR埼京線', 'JR東日本') == '#00ac9a'
        assert color_for(self.table, 'JR湘南新宿ライン', 'JR東日本') == '#e31f26'
        assert color_for(self.table, '上野東京ライン', 'JR東日本') == '#7b2d8e'
        assert color_for(self.table, '宇都宮線', 'JR東日本') == '#f68b1e'
        assert color_for(self.table, 'JR高崎線', 'JR東日本') == '#f68b1e'
        assert color_for(self.table, 'JR横須賀線', 'JR東日本') == '#0067c0'
        assert color_for(self.table, 'JR京浜東北線', 'JR東日本') == '#00b2e5'

    def test_shinkansen(self):
        assert color_for(self.table, '東海道新幹線', 'JR東海') == '#0072ba'
        assert color_for(self.table, '東北新幹線', 'JR東日本') == '#008000'
        assert color_for(self.table, '山形新幹線', 'JR東日本') == '#ee7b28'
        assert color_for(self.table, '秋田新幹線', 'JR東日本') == '#ed4399'

    def test_tokyo_metro(self):
        assert color_for(self.table, '東京メトロ銀座線', '東京メトロ') == '#ff9500'
        assert color_for(self.table, '東京メトロ丸ノ内線', '東京メトロ') == '#f62e36'
        assert color_for(self.table, '東京メトロ半蔵門線', '東京メトロ') == '#8f76d6'

    def test_toei(self):
        assert color_for(self.table, '都営大江戸線', '東京都交通局') == '#b6007a'
        assert color_for(self.table, '都営新宿線', '東京都交通局') == '#b0bf1e'

    def test_osaka_metro(self):
        assert color_for(self.table, '大阪メトロ御堂筋線', '大阪市高速電気軌道') == '#e5171f'

    def test_private(self):
        assert color_for(self.table, '京王線', '京王電鉄') == '#dd0077'
        assert color_for(self.table, '小田急小田原線', '小田急電鉄') == '#2288cc'
        assert color_for(self.table, '東急東横線', '東急電鉄') == '#da0442'
        assert color_for(self.table, '東武東上線', '東武鉄道') == '#004098'
        assert color_for(self.table, '近鉄南大阪線', '近畿日本鉄道') == '#028e46'

    def test_no_color(self):
        assert color_for(self.table, 'JR東北新幹線(八戸～青森)', 'JR東日本') is not None
        # 无官方色的线路 -> None(灰)
        assert color_for(self.table, '架空線', '架空会社') is None

    def test_coverage(self):
        # 全线路颜色覆盖率(含ekidata line_color_c兜底)
        import csv
        from ekidata import load_ekidata
        from colors import attach_colors
        eki = load_ekidata()
        comp = {c['company_cd']: c['company_name'] for c in eki['companies']}
        colored = 0
        total = 0
        for l in eki['lines']:
            if l['e_status'] != '0':
                continue
            total += 1
            c = color_for(self.table, l['line_name'], comp.get(l['company_cd'], ''))
            if not c:
                raw = l.get('line_color_c', '')
                if raw:
                    c = '#' + raw.lower()
            if c:
                colored += 1
        print(f'\nline color coverage: {colored}/{total} ({colored/total*100:.1f}%)')
        assert colored / total >= 0.80
