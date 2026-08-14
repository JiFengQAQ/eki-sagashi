// 全量可找到性测试: 对全部车站, 用各自 name/kana/roma 查询必须命中自己
// 暴露数据与索引不一致的静默错误
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, '../../data');
const stations = JSON.parse(readFileSync(join(dataDir, 'stations.json'), 'utf-8'));
const canon = JSON.parse(readFileSync(join(dataDir, 'canon.json'), 'utf-8'));

const { buildIndex, search } = await import('../search.js');
const idx = buildIndex(stations, canon);

test(`全量: 站名查询命中自己 (${stations.length}站)`, () => {
  const misses = [];
  for (const s of stations) {
    const r = search(idx, s.name, 50);
    if (!r.some(x => x.id === s.id)) misses.push(s.name);
  }
  assert.equal(misses.length, 0, `站名查询未命中: ${misses.slice(0, 20).join(', ')}`);
});

test(`全量: kana查询命中自己 (${stations.filter(s => s.kana).length}站)`, () => {
  const misses = [];
  for (const s of stations) {
    if (!s.kana) continue;
    const r = search(idx, s.kana, 50);
    if (!r.some(x => x.id === s.id)) misses.push(`${s.name}(${s.kana})`);
  }
  assert.equal(misses.length, 0, `kana查询未命中: ${misses.slice(0, 20).join(', ')}`);
});

test(`全量: roma查询命中自己 (${stations.filter(s => s.roma).length}站)`, () => {
  const misses = [];
  for (const s of stations) {
    if (!s.roma) continue;
    const r = search(idx, s.roma, 50);
    if (!r.some(x => x.id === s.id)) misses.push(`${s.name}(${s.roma})`);
  }
  assert.equal(misses.length, 0, `roma查询未命中: ${misses.slice(0, 20).join(', ')}`);
});
