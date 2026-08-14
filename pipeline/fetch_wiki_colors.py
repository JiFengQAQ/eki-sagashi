# -*- coding: utf-8 -*-
"""Wikipedia ラインカラー批量核实: 对 ekidata 缺色线, 搜 Wikipedia 条目 infobox 的
ラインカラー/文字色 参数, 输出建议 MANUAL 表. 只抓不写, 人工审查后并入 colors.py"""
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, 'pipeline')
from ekidata import load_ekidata
from colors import build_color_table, color_for

UA = 'eki-sagashi/1.0 (station line color enrichment)'

LINE_COLOR_RE = re.compile(r'ラインカラー\s*=\s*([#0-9a-fA-F]{3,8})', re.I)
TEXT_COLOR_RE = re.compile(r'文字色\s*=\s*([#0-9a-fA-F]{3,8})', re.I)


def api_get(params):
    url = 'https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def search_title(query):
    import json
    d = json.loads(api_get({
        'action': 'query', 'list': 'search', 'srsearch': query,
        'srlimit': 3, 'format': 'json', 'formatversion': 2,
    }))
    return [h['title'] for h in d['query']['search']]


def get_wikitext(title):
    import json
    d = json.loads(api_get({
        'action': 'parse', 'page': title, 'prop': 'wikitext',
        'section': 0, 'format': 'json', 'formatversion': 2, 'redirects': 1,
    }))
    return d.get('parse', {}).get('wikitext', ''), d.get('parse', {}).get('title', '')


def find_color(op, line):
    """返回 (色, 依据条目名)"""
    base = re.sub(r'[（(].*?[)）]', '', line)
    # 候选查询词
    cands = []
    if base:
        cands.append(f'{op}{base}')
        cands.append(base)
        if '系統' in base or base.endswith('線'):
            cands.append(f'{op} {base}')
    for q in cands[:3]:
        try:
            titles = search_title(q)
        except Exception:
            continue
        for t in titles[:2]:
            try:
                wt, resolved = get_wikitext(t)
            except Exception:
                continue
            m = LINE_COLOR_RE.search(wt)
            if m:
                return m.group(1).upper(), resolved
            m = TEXT_COLOR_RE.search(wt)
            if m:
                return m.group(1).upper(), resolved
        time.sleep(0.2)
    return None, ''


def main():
    import json
    eki = load_ekidata()
    comp = {c['company_cd']: c['company_name'] for c in eki['companies']}
    t = build_color_table()
    missing = []
    for l in eki['lines']:
        if l['e_status'] != '0':
            continue
        op = comp.get(l['company_cd'], '')
        if not color_for(t, l['line_name'], op):
            missing.append((op, l['line_name']))
    missing = [m for m in missing if m not in (('JR東日本', 'JR成田エクスプレス'),)]

    results = []
    for i, (op, line) in enumerate(missing):
        color, src = find_color(op, line)
        results.append((op, line, color, src))
        print(f'{i+1}/{len(missing)} {op} | {line} → {color or "FAIL"} {src}')
        time.sleep(0.3)

    with open('/tmp/wiki_colors.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    ok = sum(1 for r in results if r[2])
    print(f'\n合计 {len(results)} 条, 找到色 {ok} 条. 结果已存 /tmp/wiki_colors.json')


if __name__ == '__main__':
    main()
