// 索引构建 Web Worker (ES Module): buildIndex をバックグラウンドで実行
import { buildIndex } from './search.js';

self.onmessage = function (e) {
  const { stations, canon } = e.data;
  const idx = buildIndex(stations, canon);
  self.postMessage({ entries: idx.entries });
};
