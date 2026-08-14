// 站名搜索: 归一化(与Python管道同语义) + 前缀索引 + rid排序
// 纯函数, 浏览器/Node 通用

const KANJI_RE = /[\u3400-\u9fff\uf900-\ufaff]/;

const MACRON_MAP = { ā: 'a', ē: 'e', ī: 'i', ō: 'o', ū: 'u' };

// 长音符展开: ー 按前行假名展开(オ段->う)
const VOWEL_AFTER = (() => {
  const m = {};
  // 行 -> 段vowel: あ段->あ い段->い う段->う え段->え お段->う
  const rows = {
    'あかさたなはまやらわがざだばぱ': 'あ',
    'いきしちにひみりぎじぢびぴ': 'い',
    'うくすつぬふむゆるぐずづぶぷ': 'う',
    'えけせてねへめれげぜでべぺ': 'え',
    'おこそとのほもよろをごぞどぼぽ': 'う',
  };
  for (const [chs, vow] of Object.entries(rows)) {
    for (const ch of chs) m[ch] = vow;
  }
  const small = 'ぁぃぅぇぉゃゅょ';
  const smallV = 'あいうえおあうう';
  for (let i = 0; i < small.length; i++) m[small[i]] = smallV[i];
  m['ゔ'] = 'う';
  return m;
})();

function expandLongVowel(s) {
  let out = '';
  for (const ch of s) {
    if (ch === 'ー' && out) {
      const prev = out[out.length - 1];
      out += VOWEL_AFTER[prev] || '';
      continue;
    }
    out += ch;
  }
  return out;
}

// 查询/索引统一归一化
export function normalizeQuery(input, canon) {
  let s = String(input || '').normalize('NFKC');
  s = s.replace(/駅$/, '');
  // 罗马音(纯ASCII+长音符号+数字)
  if (/^[a-z0-9āēīōūĀĒĪŌŪ\s'\-]+$/i.test(s)) {
    return s.toLowerCase()
      .replace(/[āēīōū]/g, ch => MACRON_MAP[ch])
      .replace(/[\s'\-]/g, '');
  }
  // ケ/ヵ 夹汉字间 -> ヶ (在片假名转换前处理)
  const arr0 = [...s];
  s = arr0.map((ch, i) => {
    if ((ch === 'ケ' || ch === 'ヵ') && i > 0 && i < arr0.length - 1 &&
        KANJI_RE.test(arr0[i - 1]) && KANJI_RE.test(arr0[i + 1])) {
      return 'ヶ';
    }
    return ch;
  }).join('');
  // 片假名->平假名(0x30a1-0x30f4; ヵヶ=0x30f5/0x30f6 保留)
  s = s.replace(/[\u30a1-\u30f4]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0x60));
  s = expandLongVowel(s);
  const arr = [...s];
  const out = arr.map((ch, i) => {
    if (ch === '々') {
      return i > 0 && KANJI_RE.test(arr[i - 1]) ? arr[i - 1] : ch;
    }
    if (KANJI_RE.test(ch)) return canon[ch] || ch;
    return ch;
  });
  return out.join('');
}

// 构建索引: 排序键数组 + 二分
export function buildIndex(stations, canon) {
  const entries = []; // {k, id, ex} ex=1: クエリが駅名/かな/romaの先頭完全一致
  for (let i = 0; i < stations.length; i++) {
    const st = stations[i];
    const keys = new Map(); // key -> exact(1/0)
    const add = (raw, exact) => {
      const k = raw && String(raw);
      if (!k) return;
      const prev = keys.get(k) || 0;
      keys.set(k, Math.max(prev, exact));
    };
    add(normalizeQuery(st.name, canon), 1);
    add(st.kana, 1);
    add(st.roma, 1);
    add(st.roma_ou || st.roma, 1);
    if (Array.isArray(st.al)) {
      for (const a of st.al) add(normalizeQuery(a, canon), 0);
    }
    if (st.en) add(normalizeQuery(st.en, canon), 0);
    for (const [k, ex] of keys) entries.push({ k, id: i, ex });
  }
  entries.sort((a, b) => (a.k < b.k ? -1 : a.k > b.k ? 1 : 0));
  return { stations, entries, canon };
}

function lowerBound(arr, q) {
  let lo = 0, hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (arr[mid].k < q) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function search(idx, query, limit) {
  const q = normalizeQuery(query, idx.canon);
  if (!q) return [];
  const { stations, entries } = idx;
  const lo = lowerBound(entries, q);
  const ids = new Set();
  const exactIds = new Set(); // 字段全文精确匹配的站(优先, 与查询长度无关)
  // 前缀匹配: 从 lo 开始扫到前缀不匹配
  for (let i = lo; i < entries.length; i++) {
    const e = entries[i];
    if (!e.k.startsWith(q)) break;
    ids.add(e.id);
    if (e.ex && e.k === q) exactIds.add(e.id);
  }
  // 精确匹配站全收集(数量少), rest 按 rid 顺序受 limit 限制
  const exactResult = [];
  const restResult = [];
  for (let i = 0; i < stations.length; i++) {
    if (!ids.has(i)) continue;
    if (exactIds.has(i)) {
      exactResult.push(stations[i]);
    } else if (restResult.length < limit) {
      restResult.push(stations[i]);
    }
  }
  return exactResult.concat(restResult).slice(0, limit);
}
