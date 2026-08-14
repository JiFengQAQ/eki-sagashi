// 駅さがし アプリ: 検索UI + 詳細表示 + テーマ
import { buildIndex, search } from './search.js?v=7208a11';

(function () {
  'use strict';

  const qEl = document.getElementById('q');
  const resultsEl = document.getElementById('results');
  const detailEl = document.getElementById('detail');
  const hintEl = document.getElementById('hint');
  const metaLine = document.getElementById('metaLine');

  let idx = null;
  let stations = [];
  let activeIndex = -1;
  let currentResults = [];

  // ---------- 数値表示 ----------
  function fmt(n) {
    if (n == null) return null;
    if (n >= 10000) return (n / 10000).toFixed(1) + '万人';
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function dotColor(line) {
    return line.c || null;
  }

  function renderLineDot(line) {
    const c = dotColor(line);
    return `<span class="line-dot ${c ? '' : 'no-color'}" style="${c ? 'background:' + c : ''}" aria-hidden="true"></span>`;
  }

  function renderRidBadge(st) {
    const v = st.rid && st.rid.v;
    if (!v) return '<span class="rid-badge na">データなし</span>';
    return `<span class="rid-badge">${fmt(v)}<span class="unit">人/日 (${st.rid.y}年度)</span></span>`;
  }

  function stationSub(st) {
    const parts = [st.pref];
    if (st.muni) parts.push(st.muni + (st.ward ? ' ' + st.ward : ''));
    return parts.join(' ');
  }

  // ---------- 検索 ----------
  function runSearch() {
    const q = qEl.value;
    const list = q.trim() ? search(idx, q, 50) : [];
    currentResults = list;
    activeIndex = -1;
    renderResults(list, q);
    qEl.setAttribute('aria-expanded', list.length > 0 ? 'true' : 'false');
    if (list.length) {
      hintEl.style.display = 'none';
    } else if (q.trim()) {
      hintEl.style.display = 'none';
    } else {
      hintEl.style.display = '';
    }
    if (typeof updateClearBtn === 'function') updateClearBtn();
  }

  function renderResults(list, q) {
    resultsEl.innerHTML = '';
    if (!q.trim()) {
      return;
    }
    if (!list.length) {
      const li = document.createElement('li');
      li.className = 'empty-note';
      li.innerHTML = '該当する駅が見つかりません<br><span class="empty-hint">ひらがな・カタカナ・ローマ字・簡体漢字でも試してみてください</span>';
      resultsEl.appendChild(li);
      return;
    }
    list.forEach((st, i) => {
      const li = document.createElement('li');
      li.className = 'result-item';
      li.id = 'res-' + i;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      const lines = st.lines.slice(0, 3).map(renderLineDot).join('');
      const more = st.lines.length > 3 ? `<span class="result-sub"><span class="sep">ほか${st.lines.length - 3}路線</span></span>` : '';
      li.innerHTML =
        `<span class="line-dots">${lines}</span>` +
        `<span class="result-main">` +
        `<span class="result-name">${escapeHtml(st.name)}</span>` +
        `<span class="result-sub">${escapeHtml(st.kana)}<span class="sep">·</span>${escapeHtml(stationSub(st))}${more ? more : ''}</span>` +
        `</span>` +
        renderRidBadge(st);
      li.addEventListener('click', () => { openDetail(st); });
      resultsEl.appendChild(li);
    });
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // 英文名是否等价于罗马音(归一化: 小写+去空格/连字符/撇号后相同)
  function sameAsRoma(en, roma) {
    if (!roma) return false;
    const norm = s => String(s).toLowerCase().replace(/[\s'\-]/g, '');
    return norm(en) === norm(roma);
  }

  function setActive(i) {
    const items = resultsEl.querySelectorAll('.result-item');
    items.forEach((el, k) => {
      el.classList.toggle('active', k === i);
      el.setAttribute('aria-selected', k === i ? 'true' : 'false');
    });
    if (i >= 0 && items[i]) {
      qEl.setAttribute('aria-activedescendant', items[i].id);
    } else {
      qEl.removeAttribute('aria-activedescendant');
    }
  }

  // ---------- 詳細 ----------
  function openDetail(st) {
    resultsEl.innerHTML = '';
    hintEl.style.display = 'none';
    let html = `<h2>${escapeHtml(st.name)}</h2>`;
    const readings = [st.kana, st.roma].filter(Boolean).join(' / ');
    html += `<p class="readings">${escapeHtml(readings)}</p>`;
    if (st.en && !sameAsRoma(st.en, st.roma)) {
      html += `<p class="readings">${escapeHtml(st.en)}</p>`;
    }
    html += `<p class="place">${escapeHtml(stationSub(st))}</p>`;

    html += `<h3>路線</h3><div class="line-list">`;
    st.lines.forEach((l) => {
      const c = dotColor(l);
      html += `<span class="line-chip"><span class="dot ${c ? '' : 'no-color'}" style="${c ? 'background:' + c : ''}"></span>${escapeHtml(l.n)}</span>`;
    });
    html += `</div>`;

    if (st.per && st.per.length) {
      html += `<h3>乗降人員</h3><table class="per-table"><thead><tr><th>事業者</th><th>路線</th><th class="num">人/日</th><th class="num">年度</th></tr></thead><tbody>`;
      st.per.forEach((p) => {
        let note = p.note ? `<div style="color:var(--text-3);font-size:11px">${escapeHtml(p.note)}</div>` : '';
        html += `<tr><td>${escapeHtml(p.op)}</td><td>${escapeHtml(p.line)}${note}</td><td class="num">${fmt(p.v)}</td><td class="num">${p.y}</td></tr>`;
      });
      html += `</tbody></table>`;
    }

    html += `<div class="detail-links">` +
      `<a class="btn" href="https://ja.wikipedia.org/wiki/${encodeURIComponent(st.name + '駅')}" rel="noopener" target="_blank">Wikipedia</a>` +
      (st.lat ? `<a class="btn" href="https://www.openstreetmap.org/?mlat=${st.lat}&mlon=${st.lon}#map=16/${st.lat}/${st.lon}" rel="noopener" target="_blank">OpenStreetMap</a>` : '') +
      (st.lat ? `<a class="btn" href="https://maps.apple.com/?ll=${st.lat},${st.lon}&q=${encodeURIComponent(st.name)}" rel="noopener" target="_blank">Apple Maps</a>` : '') +
      `</div>`;

    detailEl.innerHTML = html;
    detailEl.hidden = false;
    detailEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    updateClearBtn();
  }

  // ---------- クリアボタン ----------
  const clearBtn = document.getElementById('clearBtn');

  function updateClearBtn() {
    const show = qEl.value.length > 0 || !detailEl.hidden;
    clearBtn.hidden = !show;
  }

  clearBtn.addEventListener('click', () => {
    qEl.value = '';
    detailEl.hidden = true;
    runSearch();
    qEl.focus();
    updateClearBtn();
  });

  // ---------- イベント ----------
  let timer = null;
  qEl.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(runSearch, 40);
    updateClearBtn();
  });
  qEl.addEventListener('keydown', (e) => {
    const items = resultsEl.querySelectorAll('.result-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (items.length) {
        activeIndex = (activeIndex + 1) % items.length;
        setActive(activeIndex);
        items[activeIndex].scrollIntoView({ block: 'nearest' });
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (items.length) {
        activeIndex = (activeIndex - 1 + items.length) % items.length;
        setActive(activeIndex);
        items[activeIndex].scrollIntoView({ block: 'nearest' });
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && currentResults[activeIndex]) {
        openDetail(currentResults[activeIndex]);
      } else if (currentResults.length === 1) {
        openDetail(currentResults[0]);
      }
    } else if (e.key === 'Escape') {
      const modal = document.getElementById('aboutModal');
      if (!modal.hidden) {
        modal.hidden = true;
      } else if (!detailEl.hidden) {
        detailEl.hidden = true;
        updateClearBtn();
      } else {
        qEl.value = '';
        runSearch();
      }
    }
  });
  document.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip[data-q]');
    if (chip) {
      qEl.value = chip.dataset.q;
      runSearch();
      qEl.focus();
    }
  });
  document.getElementById('aboutBtn').addEventListener('click', () => {
    document.getElementById('aboutModal').hidden = false;
  });
  document.getElementById('aboutClose').addEventListener('click', () => {
    document.getElementById('aboutModal').hidden = true;
  });
  document.getElementById('aboutModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('aboutModal')) {
      document.getElementById('aboutModal').hidden = true;
    }
  });

  // ---------- プログレス付きfetch ----------
  async function fetchWithProgress(url, onProgress) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${url}: ${res.status}`);
    const total = +res.headers.get('content-length') || 0;
    let loaded = 0;
    const reader = res.body.getReader();
    const chunks = [];
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      loaded += value.length;
      if (total) onProgress(loaded / total);
    }
    const buf = new Uint8Array(loaded);
    let offset = 0;
    for (const c of chunks) { buf.set(c, offset); offset += c.length; }
    return JSON.parse(new TextDecoder().decode(buf));
  }

  // ---------- 索引構築 (Web Worker / fallback: main thread) ----------
  function buildIndexAsync(stations, canon) {
    return new Promise((resolve, reject) => {
      if (!window.Worker) {
        // Worker未対応: メインスレッドで実行
        import('./search.js?v=7208a11').then(({ buildIndex }) => {
          resolve(buildIndex(stations, canon));
        }).catch(reject);
        return;
      }
      const w = new Worker('index-worker.js?v=7208a11', { type: 'module' });
      w.onmessage = (e) => {
        w.terminate();
        resolve({ stations, entries: e.data.entries, canon });
      };
      w.onerror = (err) => {
        w.terminate();
        // Worker失敗時はメインスレッドにフォールバック
        import('./search.js?v=7208a11').then(({ buildIndex }) => {
          resolve(buildIndex(stations, canon));
        }).catch(reject);
      };
      w.postMessage({ stations, canon });
    });
  }

  // ---------- 初期化 ----------
  async function init() {
    const loadBar = document.getElementById('loadBar');
    const fill = loadBar.querySelector('.load-bar-fill');
    try {
      loadBar.hidden = false;
      const [stationsData, canon] = await Promise.all([
        fetchWithProgress('stations.json?v=7208a11', p => { fill.style.width = (p * 90) + '%'; }),
        fetch('canon.json?v=7208a11').then(r => r.json()),
      ]);
      fill.style.width = '95%';
      stations = stationsData;
      idx = await buildIndexAsync(stations, canon);
      fill.style.width = '100%';
      metaLine.textContent =
        `${stations.length.toLocaleString('ja-JP')}駅 · 乗降人員データ ${stations.filter(s => s.rid && s.rid.v).length.toLocaleString('ja-JP')}駅 · 2022年9月時点の路線`;
      runSearch();
    } catch (err) {
      metaLine.textContent = 'データの読み込みに失敗しました。再読み込みしてください。';
      console.error(err);
    } finally {
      setTimeout(() => { loadBar.hidden = true; }, 300);
    }
  }

  init();
})();
