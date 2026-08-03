import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, '../../data');
const stations = JSON.parse(readFileSync(join(dataDir, 'stations.json'), 'utf-8'));
const canon = JSON.parse(readFileSync(join(dataDir, 'canon.json'), 'utf-8'));

const { normalizeQuery, buildIndex, search } = await import('../search.js');

const idx = buildIndex(stations, canon);

test('normalize: kanji', () => {
  assert.equal(normalizeQuery('新宿', canon), '新宿');
  assert.equal(normalizeQuery('新宿駅', canon), '新宿');
  assert.equal(normalizeQuery('涩谷', canon), '渋谷');
  assert.equal(normalizeQuery('新桥', canon), '新橋');
  assert.equal(normalizeQuery('东京', canon), '東京');
  assert.equal(normalizeQuery('横滨', canon), '横浜');
  assert.equal(normalizeQuery('市ケ谷', canon), '市ヶ谷');
  assert.equal(normalizeQuery('代々木', canon), '代代木');
});

test('normalize: kana', () => {
  assert.equal(normalizeQuery('しんじゅく', canon), 'しんじゅく');
  assert.equal(normalizeQuery('シンジュク', canon), 'しんじゅく');
  assert.equal(normalizeQuery('トーキョー', canon), 'とうきょう');
});

test('normalize: romaji', () => {
  assert.equal(normalizeQuery('Shinjuku', canon), 'shinjuku');
  assert.equal(normalizeQuery('Tōkyō', canon), 'tokyo');
  assert.equal(normalizeQuery('toukyou', canon), 'toukyou');
  assert.equal(normalizeQuery('Shin-Koyasu', canon), 'shinkoyasu');
  assert.equal(normalizeQuery('Ōsaka', canon), 'osaka');
});

test('search: kana finds station', () => {
  const r = search(idx, 'しんじゅく', 10);
  assert.ok(r.some(s => s.name === '新宿'));
});

test('search: katakana same as hiragana', () => {
  const a = search(idx, 'シンジュク', 10).map(s => s.id);
  const b = search(idx, 'しんじゅく', 10).map(s => s.id);
  assert.deepEqual(a, b);
});

test('search: romaji finds station', () => {
  const r = search(idx, 'shinjuku', 10);
  assert.ok(r.some(s => s.name === '新宿'));
  const r2 = search(idx, 'tokyo', 10);
  assert.ok(r2.some(s => s.name === '東京'));
});

test('search: ou variant', () => {
  const r = search(idx, 'toukyou', 10);
  assert.ok(r.some(s => s.name === '東京'));
});

test('search: macron stripped input', () => {
  const r = search(idx, 'Tōkyō', 10);
  assert.ok(r.some(s => s.name === '東京'));
});

test('search: simplified chinese', () => {
  const r = search(idx, '涩谷', 10);
  assert.ok(r.some(s => s.name === '渋谷'));
  const r2 = search(idx, '新桥', 10);
  assert.ok(r2.some(s => s.name === '新橋'));
});

test('search: prefix length 1', () => {
  const r = search(idx, '新', 50);
  assert.ok(r.some(s => s.name === '新宿'));
  const rk = search(idx, 'し', 50);
  assert.ok(rk.some(s => s.name === '新宿'));
  const rr = search(idx, 's', 50);
  assert.ok(rr.some(s => s.name === '新宿'));
});

test('search: prefix length 2', () => {
  const r = search(idx, '新宿', 10);
  assert.ok(r.some(s => s.name === '新宿'));
});

test('search: sorted by ridership desc', () => {
  const r = search(idx, 'しん', 20);
  assert.equal(r[0].name, '新宿'); // 新宿 rid 1,578,732 最大
  const vals = r.map(s => s.rid?.v ?? -1);
  for (let i = 1; i < vals.length; i++) {
    assert.ok(vals[i - 1] >= vals[i]);
  }
});

test('search: no-data stations sort last', () => {
  const r = search(idx, 'しん', 100);
  const noData = r.filter(s => !s.rid?.v);
  const withData = r.filter(s => s.rid?.v);
  if (noData.length && withData.length) {
    assert.ok(r.indexOf(noData[0]) > r.indexOf(withData[withData.length - 1]));
  }
});

test('search: empty query returns empty', () => {
  assert.deepEqual(search(idx, '', 10), []);
  assert.deepEqual(search(idx, '   ', 10), []);
});

test('search: limit respected', () => {
  const r = search(idx, 'し', 5);
  assert.ok(r.length <= 5);
});

test('search: station suffix in query', () => {
  const r = search(idx, '新宿駅', 10);
  assert.ok(r.some(s => s.name === '新宿'));
});

test('search: 大宮 romaji', () => {
  const r = search(idx, 'omiya', 10);
  assert.ok(r.some(s => s.name === '大宮'));
});

test('英語由来別名で検索できる (高輪ゲートウェイ → gateway)', () => {
  const hits = search(idx, 'gateway', 5).map(s => s.name);
  assert.ok(hits.includes('高輪ゲートウェイ'), 'gateway で高輪ゲートウェイが見つかる');
  const st = stations.find(s => s.name === '高輪ゲートウェイ');
  assert.equal(st.roma, 'takanawagateway', 'JR公式英文名が使われる');
});

test('英語名で検索できる (鹿島サッカースタジアム → kashima soccer)', () => {
  const hits = search(idx, 'kashima soccer', 5).map(s => s.name);
  assert.ok(hits.includes('鹿島サッカースタジアム（臨）'), 'kashima soccer で見つかる');
});

test('英語名で検索できる (新橋 → Shimbashi)', () => {
  const hits = search(idx, 'shimbashi', 5).map(s => s.name);
  assert.ok(hits.includes('新橋'), 'shimbashi で見つかる');
});

test('空港ターミナル駅: 成田第2/第3 は空港第２ビルにヒット', () => {
  for (const q of ['成田空港第2', '成田空港第3', '第2ターミナル']) {
    const hits = search(idx, q, 5).map(s => s.name);
    assert.ok(hits.some(n => n.includes('空港第２ビル')), `${q} で空港第２ビルが見つかる`);
  }
});

test('空港ターミナル駅: 羽田モノレール独立駅がある', () => {
  const names = stations.map(s => s.name);
  assert.ok(names.includes('羽田空港第1ターミナル'), 'モノレール第1ターミナル独立駅');
  assert.ok(names.includes('羽田空港第2ターミナル'), 'モノレール第2ターミナル独立駅');
  const st = stations.find(s => s.name === '羽田空港第2ターミナル');
  assert.ok(st.lines.some(l => l.n.includes('東京モノレール')), '東京モノレール路線を持つ');
});

test('長音の標準ヘボン式表記 (大阪→osaka, 京都→kyoto)', () => {
  for (const [name, roma] of [['大阪', 'osaka'], ['京都', 'kyoto'], ['東京', 'tokyo']]) {
    const st = stations.find(s => s.name === name);
    assert.equal(st.roma, roma, `${name} のromaは${roma}`);
    assert.ok(search(idx, roma, 5).some(s => s.name === name), `${roma} で見つかる`);
  }
});
