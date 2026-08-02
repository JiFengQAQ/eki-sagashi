// 可找到性矩阵: 用真实前端 search.js 测试 各输入格式 × 前缀长度
// 用法: node verify/search_matrix.mjs <stations.json路径> <canon.json路径> <ids.json路径> <out.json路径>
import { readFileSync, writeFileSync } from 'node:fs';
import { buildIndex, search } from '../web/search.js';

const [, , stationsPath, canonPath, idsPath, outPath] = process.argv;
const stations = JSON.parse(readFileSync(stationsPath, 'utf-8'));
const canon = JSON.parse(readFileSync(canonPath, 'utf-8'));
const ids = JSON.parse(readFileSync(idsPath, 'utf-8'));

const idx = buildIndex(stations, canon);
const byId = new Map(stations.map((s, i) => [s.id, i]));

const results = {};
for (const id of ids) {
  const st = stations[byId.get(id)];
  if (!st) continue;
  const qs = {};
  // 汉字: 原形前缀
  for (let n = 1; n <= Math.min(4, [...st.name].length); n++) {
    qs[`kanji_${n}`] = [...st.name].slice(0, n).join('');
  }
  // 假名(平)
  for (let n = 1; n <= Math.min(4, st.kana.length); n++) {
    qs[`kana_${n}`] = st.kana.slice(0, n);
  }
  // 罗马音(含长音剥离后的输入形态)
  for (let n = 1; n <= Math.min(4, st.roma.length); n++) {
    qs[`roma_${n}`] = st.roma.slice(0, n);
  }
  const row = {};
  for (const [key, q] of Object.entries(qs)) {
    const hits = search(idx, q, 10);
    row[key] = hits.some(s => s.id === id);
  }
  // 补齐不存在的前缀测试(站名/读音长度不足): 标记 null(报告显示为—)
  for (let n = 1; n <= 4; n++) {
    if (row[`kanji_${n}`] === undefined) row[`kanji_${n}`] = null;
    if (row[`kana_${n}`] === undefined) row[`kana_${n}`] = null;
    if (row[`roma_${n}`] === undefined) row[`roma_${n}`] = null;
  }
  results[id] = { name: st.name, checked: row };
}
writeFileSync(outPath, JSON.stringify(results, null, 1));
console.log(`matrix done: ${Object.keys(results).length} stations`);
