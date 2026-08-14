# -*- coding: utf-8 -*-
"""Wikipedia 首句注音批量抓取: 对无读音站从 ja.wikipedia 抓取 wikitext 首段,
提取「駅名（かな）」或「駅名（かなえき）」模式. 含消歧义/重定向错位防御.
用法: python3 fetch_wiki_kana.py [--dry-run] [--limit N]"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIONS_PATH = os.path.join(_REPO_ROOT, 'data', 'stations.json')
OUT_PATH = os.path.join(_REPO_ROOT, 'data', 'raw', 'wiki_kana.json')

UA = 'eki-sagashi/1.0 (https://eki.jifeng.plus; station kana enrichment)'

# 注音提取: 「駅名（かな）」「駅名（かなえき）」「駅名（かなていりゅうじょう）」
# 粗体兼容('{0,3}), ・含む多読みは破棄
_PAREN_KANA_RE = re.compile(
    r"'{0,3}([^'（(\n]{1,30})'{0,3}（([あ-んー・]+(?:えき|ていりゅうじょう)?)）"
)
# 剥除尾部
_TAILS = ['ていりゅうじょう', 'えき']


def _fetch_wikitext(title):
    """Wikipedia API で wikitext 首段(rsection=0)を取得. リダイレクト追従."""
    params = urllib.parse.urlencode({
        'action': 'parse', 'page': title, 'prop': 'wikitext',
        'section': 0, 'format': 'json', 'formatversion': 2,
        'redirects': 1,
    })
    url = f'https://ja.wikipedia.org/w/api.php?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            d = json.loads(resp.read().decode('utf-8'))
        return d.get('parse', {}).get('wikitext', ''), d.get('parse', {}).get('title', '')
    except Exception:
        return '', ''


def _extract_kana(wikitext, station_name):
    """wikitext 首段から注音を抽出. 安全ガード付き.
    戻り値: (kana, reason) — kana='' の場合 reason に理由"""
    if not wikitext:
        return '', 'empty wikitext'
    # 消歧义ページ検出
    if '{{aimai}}' in wikitext or '{{曖昧さ回避' in wikitext:
        return '', 'disambiguation page'
    m = _PAREN_KANA_RE.search(wikitext)
    if not m:
        return '', 'no kana pattern found'
    name_in_text, kana = m.group(1), m.group(2)
    # ・含む多読みは信頼性低いので破棄
    if '・' in kana:
        return '', f'multiple readings: {kana}'
    # 尾部剥除
    for tail in _TAILS:
        if kana.endswith(tail):
            kana = kana[:-len(tail)]
            break
    # リダイレクト错位防御: 駅名とテキスト内名が一致しない場合
    # ただし「駅」あり/なしの差は許容
    norm_name = station_name.rstrip('駅')
    norm_text = name_in_text.rstrip('駅')
    if norm_name != norm_text and not norm_text.startswith(norm_name):
        return '', f'name mismatch: {name_in_text} vs {station_name}'
    if not kana:
        return '', 'empty after tail strip'
    return kana, 'ok'


def fetch_missing_kana(stations, existing, dry_run=False, limit=None):
    """无读音站に対してWikipedia注音をバルク取得"""
    targets = [s for s in stations if not s.get('kana') and s['name'] not in existing]
    if limit:
        targets = targets[:limit]
    print(f'対象: {len(targets)}駅')
    results = {}
    errors = {}
    for i, st in enumerate(targets):
        name = st['name']
        title = f'{name}駅'
        wt, resolved = _fetch_wikitext(title)
        kana, reason = _extract_kana(wt, name)
        if kana:
            results[name] = kana
        else:
            errors[name] = reason
        if (i + 1) % 50 == 0:
            print(f'  {i+1}/{len(targets)} done, {len(results)} found, {len(errors)} failed')
        time.sleep(0.3)  # rate limit
    print(f'完了: {len(results)}駅取得成功, {len(errors)}駅失敗')
    if errors:
        from collections import Counter
        reasons = Counter(errors.values())
        print('失敗理由分布:')
        for r, n in reasons.most_common(10):
            print(f'  {r}: {n}')
    return results, errors


def main():
    dry_run = '--dry-run' in sys.argv
    limit = None
    if '--limit' in sys.argv:
        i = sys.argv.index('--limit')
        limit = int(sys.argv[i + 1])
    stations = json.load(open(STATIONS_PATH, encoding='utf-8'))
    existing = {}
    if os.path.exists(OUT_PATH):
        existing = json.load(open(OUT_PATH, encoding='utf-8'))
        print(f'既存 wiki_kana: {len(existing)}件')
    new_results, errors = fetch_missing_kana(stations, existing, dry_run, limit)
    if dry_run:
        print('DRY RUN — 書き込みなし')
        for k, v in list(new_results.items())[:20]:
            print(f'  {k} → {v}')
        return
    if new_results:
        existing.update(new_results)
        with open(OUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=1, sort_keys=True)
        print(f'書き込み完了: {OUT_PATH} ({len(existing)}件, +{len(new_results)}新規)')


if __name__ == '__main__':
    main()
