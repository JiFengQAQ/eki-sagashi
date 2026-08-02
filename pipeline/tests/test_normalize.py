# -*- coding: utf-8 -*-
import pytest
from normalize import (canonical_kanji, norm_kana, norm_roma,
                       norm_station_name, norm_operator)


class TestCanonicalKanji:
    def test_jp_shinjitai_unchanged(self):
        assert canonical_kanji('渋谷') == '渋谷'
        assert canonical_kanji('横浜') == '横浜'
        assert canonical_kanji('広島') == '広島'
        assert canonical_kanji('函館') == '函館'

    def test_simplified_to_jp(self):
        assert canonical_kanji('涩谷') == '渋谷'
        assert canonical_kanji('新桥') == '新橋'
        assert canonical_kanji('东京') == '東京'
        assert canonical_kanji('横滨') == '横浜'
        assert canonical_kanji('广岛') == '広島'
        assert canonical_kanji('函馆') == '函館'
        assert canonical_kanji('关西') == '関西'

    def test_kyujitai_to_jp(self):
        assert canonical_kanji('澁谷') == '渋谷'
        assert canonical_kanji('橫濱') == '横浜'
        assert canonical_kanji('廣島') == '広島'
        assert canonical_kanji('驛') == '駅'
        assert canonical_kanji('鐵') == '鉄'
        assert canonical_kanji('圖') == '図'
        assert canonical_kanji('氣') == '気'
        assert canonical_kanji('邊') == '辺'

    def test_same_char_converge(self):
        # 三种写法收敛到同一canonical
        assert canonical_kanji('渋谷') == canonical_kanji('涩谷') == canonical_kanji('澁谷')

    def test_special_chars(self):
        # 干/斗/筑 不能被 opencc 错误统一
        assert canonical_kanji('干潟') == '干潟'
        assert canonical_kanji('北斗') == '北斗'
        assert canonical_kanji('築地') == '築地'
        assert canonical_kanji('筑波') == canonical_kanji('築波')
        assert canonical_kanji('工機前') == '工機前'
        assert canonical_kanji('龙ケ崎市') == '竜ヶ崎市'

    def test_repetition_mark(self):
        assert canonical_kanji('代々木') == '代代木'
        assert canonical_kanji('代代木') == '代代木'

    def test_ke_ga(self):
        assert canonical_kanji('市ケ谷') == '市ヶ谷'
        assert canonical_kanji('市ヶ谷') == '市ヶ谷'

    def test_non_kanji_untouched(self):
        assert canonical_kanji('御茶ノ水') == '御茶ノ水'


class TestNormKana:
    def test_katakana_to_hiragana(self):
        assert norm_kana('シンジュク') == 'しんじゅく'
        assert norm_kana('しんじゅく') == 'しんじゅく'

    def test_long_vowel_mark(self):
        assert norm_kana('トーキョー') == 'とうきょう'
        assert norm_kana('コーヒー') == 'こうひい'
        assert norm_kana('ケーキ') == 'けえき'
        assert norm_kana('とうきょう') == 'とうきょう'

    def test_handakuten_voiced(self):
        assert norm_kana('パンダ') == 'ぱんだ'


class TestNormRoma:
    def test_lowercase_and_macron(self):
        assert norm_roma('Tokyo') == 'tokyo'
        assert norm_roma('Tōkyō') == 'tokyo'
        assert norm_roma('Shinjuku') == 'shinjuku'
        assert norm_roma('Ōsaka') == 'osaka'

    def test_spaces_hyphens(self):
        assert norm_roma('Shin-Koyasu') == 'shinkoyasu'
        assert norm_roma('shin koyasu') == 'shinkoyasu'

    def test_ou_variant_generation(self):
        from normalize import roma_variants
        assert 'tokyo' in roma_variants('Tōkyō')
        assert 'toukyou' in roma_variants('Tōkyō')
        assert 'shinjuku' in roma_variants('shinjuku')


class TestNormStationName:
    def test_strip_station_suffix(self):
        assert norm_station_name('新宿駅') == '新宿'
        assert norm_station_name('新宿') == '新宿'

    def test_strip_brackets(self):
        assert norm_station_name('押上（京成）') == '押上'
        assert norm_station_name('押上(京成)') == '押上'

    def test_nfkc(self):
        assert norm_station_name('代々木') == '代々木'


class TestNormOperator:
    def test_strip_company(self):
        assert norm_operator('東日本旅客鉄道株式会社') == '東日本旅客鉄道'
        assert norm_operator('東日本旅客鉄道') == '東日本旅客鉄道'

    def test_alias(self):
        assert norm_operator('東京都交通局') == '東京都'
        assert norm_operator('東京都') == '東京都'
        assert norm_operator('東京急行電鉄') == '東急電鉄'
