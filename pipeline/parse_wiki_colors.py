# -*- coding: utf-8 -*-
"""解析 Wikipedia ラインカラー一覧 HTML -> (运营商section, 表格行名, [hex])
按 h2/h3/h4 标题分 section, 表格行归属其 section"""
import json
import re

html = open('/home/ubuntu/eki-sagashi/data/raw/wiki_line_colors.html', encoding='utf-8').read()

# 用 BeautifulSoup 更稳
try:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.select_one('#mw-content-text') or soup
except ImportError:
    content = None

results = []
if content:
    cur_section = []
    for el in content.find_all(['h2', 'h3', 'h4', 'table', 'p']):
        if el.name in ('h2', 'h3', 'h4'):
            txt = re.sub(r'\[.*?\]', '', el.get_text()).strip()
            cur_section = [txt] if el.name == 'h2' else cur_section[:1] + [txt]
        elif el.name == 'table':
            for tr in el.find_all('tr'):
                tds = tr.find_all(['td', 'th'])
                if not tds:
                    continue
                first = re.sub(r'\s+', ' ', tds[0].get_text()).strip()
                if not first or first == '-':
                    continue
                hexes = []
                for t in tr.find_all('td'):
                    style = t.get('style', '') or ''
                    for h in re.findall(r'background:\s*(#[0-9a-fA-F]{6})', style):
                        if h not in hexes:
                            hexes.append(h)
                if not hexes:
                    continue
                results.append({
                    'sections': list(cur_section),
                    'name': first,
                    'hexes': hexes,
                })

json.dump(results, open('/tmp/wiki_colors_sections.json', 'w'), ensure_ascii=False, indent=1)
print(f'解析出 {len(results)} 行')
# 看広島電鉄 section
for r in results:
    if any('広島' in s for s in r['sections']):
        print(f"  [{r['sections']}] {r['name']:20s} {r['hexes']}")