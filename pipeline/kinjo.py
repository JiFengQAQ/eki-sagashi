# -*- coding: utf-8 -*-
"""大都市近郊区間分类器: 解析维基「大都市近郊区間 (JR)」线路-范围规则 + ekidata join.csv 站序图"""
import csv
import json
import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = ['東京', '大阪', '福岡', '新潟', '仙台']

# 维基线路名 -> ekidata 线路名前缀规范化(去JR/去括号)
def _norm_line(name):
    s = name
    s = re.sub(r'^JR', '', s)
    s = re.sub(r'[（(].*?[)）]', '', s)
    return s


def _clean_station(s):
    """[[橋本駅 (神奈川県)|橋本駅]] -> 橋本; 東京駅 -> 東京"""
    m = re.search(r'\[\[([^\]|]*?)(?:\|([^\]]*?))?\]\]', s)
    if m:
        s = m.group(2) or m.group(1)
    s = s.replace('駅', '')
    return s.strip()


def load_kinjo_rules(path=None):
    """解析wikitext -> {区域: [(线路norm名, 起点, 终点, 是否全线)]}"""
    if path is None:
        path = os.path.join(_REPO_ROOT, 'data', 'raw', 'kinjo_jr.json')
    d = json.load(open(path, encoding='utf-8'))
    wt = d['parse']['wikitext']
    rules = {r: [] for r in REGIONS}
    # 只解析 一覧 section
    start = wt.find('== 大都市近郊区間一覧 ==')
    end = wt.find('== 大都市近郊区間と他の運賃制度の特例 ==')
    if start < 0 or end < 0:
        return rules
    seg = wt[start:end]
    cur_region = None
    cur_line = None
    for line in seg.split('\n'):
        m = re.match(r'^=== (.+)近郊区間 ===$', line.strip())
        if m and m.group(1) in REGIONS:
            cur_region = m.group(1)
            cur_line = None
            continue
        if cur_region is None:
            continue
        s = line.strip()
        # 线路行: * [[線名]] ... 或 * [[線名]]：A - B（全線）
        m = re.match(r'^\*\s*\[\[([^\]|]+?)(?:\|[^\]]*?)?\]\]', s)
        if m and not s.startswith('**'):
            cur_line = m.group(1)
            rest = s[m.end():]
            if '（全線）' in rest:
                rules[cur_region].append((_norm_line(cur_line), None, None, True))
            else:
                rng = re.search(r'：\s*(.+?)(?:{{|$)', rest)
                if rng:
                    sta = [_clean_station(x) for x in re.split(r'\s*-\s*', rng.group(1))]
                    if len(sta) >= 2:
                        rules[cur_region].append((_norm_line(cur_line), sta[0], sta[-1], False))
            continue
        # 子行: ** 本線/支線：...A - B（全線）
        m = re.match(r'^\*\*\s*(?:本線|支線)[^：]*?[:：]\s*(.*)$', s)
        if m and cur_line:
            rest = m.group(1)
            if '（全線）' in rest:
                rules[cur_region].append((_norm_line(cur_line), None, None, True))
            else:
                sta = [_clean_station(x) for x in re.split(r'\s*-\s*', rest) if x.strip()]
                if len(sta) >= 2:
                    rules[cur_region].append((_norm_line(cur_line), sta[0], sta[-1], False))
    return rules


# 维基线路名(近郊区間规则用) -> ekidata norm线路名组
LINE_GROUP = {
    '東海道本線': ['東海道本線', '琵琶湖線', '京都線', '神戸線'],
    '東北本線': ['東北本線', '宇都宮線'],
    '奥羽本線': ['奥羽本線', '山形線'],
    '大糸線': ['大糸線', '北アルプス線'],
    '総武本線': ['総武本線', '中央・総武線'],
    '福知山線': ['福知山線', '宝塚線'],
    '桜島線': ['桜島線', 'ゆめ咲線'],
    '片町線': ['片町線', '学研都市線'],
    '桜井線': ['桜井線', '万葉まほろば線'],
    '阪和線': ['阪和線', '羽衣線'],
    '山陽本線': ['山陽本線', '神戸線'],
}


def build_line_orders(raw_dir=None):
    """ekidata join.csv -> {维基线路norm名: {站名: 邻接站名集合}}"""
    if raw_dir is None:
        raw_dir = os.path.join(_REPO_ROOT, 'data', 'raw')
    name_of = {}
    with open(os.path.join(raw_dir, 'station.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            name_of.setdefault(row['station_cd'], row['station_name'])
    norm_of = {}
    with open(os.path.join(raw_dir, 'line.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            norm_of.setdefault(row['line_cd'], _norm_line(row['line_name']))
    raw_orders = {}
    with open(os.path.join(raw_dir, 'join.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ln = norm_of.get(row['line_cd'])
            if not ln:
                continue
            n1 = name_of.get(row['station_cd1'])
            n2 = name_of.get(row['station_cd2'])
            if not n1 or not n2:
                continue
            g = raw_orders.setdefault(ln, {})
            g.setdefault(n1, set()).add(n2)
            g.setdefault(n2, set()).add(n1)
    orders = {}
    for wiki_line, group in LINE_GROUP.items():
        g = {}
        for ln in group:
            sub = raw_orders.get(ln)
            if not sub:
                continue
            for k, v in sub.items():
                g.setdefault(k, set()).update(v)
        if g:
            orders[wiki_line] = g
    for ln, g in raw_orders.items():
        orders.setdefault(ln, g)
    return orders


def _on_path(graph, a, b, s):
    """s 是否在 a->b 的路径上(BFS找一条路径, 检查s在路径站集中)"""
    if a not in graph or b not in graph or s not in graph:
        return False
    if s == a or s == b:
        return True
    # BFS 记录前驱, 重建 a->b 路径
    prev = {a: None}
    queue = [a]
    found = False
    while queue:
        cur = queue.pop(0)
        if cur == b:
            found = True
            break
        for nb in graph.get(cur, ()):
            if nb not in prev:
                prev[nb] = cur
                queue.append(nb)
    if not found:
        return False
    path = set()
    cur = b
    while cur is not None:
        path.add(cur)
        cur = prev.get(cur)
    return s in path


def classify(name, rules, orders):
    """按线路范围规则判定站名所属区域; 返回区域列表"""
    found = []
    for region, rs in rules.items():
        for line_norm, a, b, full in rs:
            g = orders.get(line_norm)
            if not g:
                continue
            if full:
                if name in g:
                    found.append(region)
                    break
            else:
                if _on_path(g, a, b, name):
                    found.append(region)
                    break
    return found


# 府县全站规则: (pref_cd, 是否需JR系) -> 区域
PREF_RULES = {
    (11, True): '東京',   # 埼玉県 JR全站
    (12, True): '東京',   # 千葉県 JR全站
    (13, True): '東京',   # 東京都 JR東日本在来線全站(近似: 任何JR线)
    (14, True): '東京',   # 神奈川県 同上
    (27, True): '大阪',   # 大阪府 JR全站
    (29, True): '大阪',   # 奈良県 JR全站
}


def classify_station(st, rules, orders):
    """完整分类: 线路规则 + 府县规则; 返回区域列表"""
    regions = classify(st['name'], rules, orders)
    is_jr = any(l['company'] in ('JR北海道', 'JR東日本', 'JR東海', 'JR西日本', 'JR四国', 'JR九州')
                for l in st['lines'])
    pref_cd = st.get('pref_cd')
    for (p, jr), region in PREF_RULES.items():
        if pref_cd == p and (not jr or is_jr) and region not in regions:
            regions.append(region)
    return regions
