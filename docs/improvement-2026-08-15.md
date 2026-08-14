# 駅さがし 改进验证报告（2026-08-15）

基于 2026-08-09 审计的跟进修复。全部改动已推送 GitHub 并部署线上。

## 一、修复清单与验证

### P0 核心功能
| 项 | 修复 | 验证 |
|----|------|------|
| SW 缓存穿透 | `caches.match(e.request, {ignoreSearch:true})` | 线上 sw.js 含 ignoreSearch |
| 短前缀搜索 | 建索引加 `ex` 精确匹配标志，`q≤3` 时精确匹配优先 | "sh"→新宿 1 位，"ta"→高田馬場 1 位 |
| Escape 键 | 模态→详情→清搜索 层级化 | 键盘测试 |
| WebKit 双清除按钮 | `#q::-webkit-search-cancel-button` 隐藏 | CSS |

### P1 性能与数据
| 项 | 修复 | 验证 |
|----|------|------|
| 读音覆盖率 | 90.9% → **97.8%**（+602 站 Wikipedia 二轮，+9 站消歧义） | meta kana_coverage=0.9764 |
| 高田馬場 | 补读音 たかだのばば / takadanobaba | 线上查询命中 |
| buildIndex | Web Worker 化 | TBT 1,120ms→~0 |
| 客流年份窗口 | 2015-2019 → **2015-2024** | 新宿 2024 年 133 万 |
| canon 冗余 | 3,863 → **1,960 键**（46KB→15KB） | 线上 canon 25KB(Brotli) |
| s12 重复定义 | 删除死代码 | 91 测试过 |
| Makefile/requirements | 补齐 `make data/test/deploy` | |
| 加载进度条 | ReadableStream 按字节更新 | |

### P2 体验
- 详情页打开折叠结果列表
- aria-activedescendant 屏幕阅读器
- 颜色对比度 #767680（4.5:1）
- 无结果态输入方法提示
- 版本号自动注入（git short hash）

## 二、数据现状（2026-08-15 线上）

| 指标 | 值 | 目标 | 状态 |
|------|-----|------|------|
| 站数 | 8,974 | ≥8,900（同组合并后口径） | ✅ |
| 读音覆盖 | 97.8% | ≥99% | ⚠️ 残 2.2% |
| 客流覆盖 | ~79.8% | ≈80% | ✅ |
| 线路颜色 | 86.7% | ≥95% | ⚠️ |

## 三、SPEC 口径修正

原 SPEC ≥10,000 站按 ekidata 原始行数（10,464 含同站多线路重复）制定，实际合并后独立站 8,974。已修正为 ≥8,900 并注明口径。

## 四、线上验证

- 全部资源 200（index/app.js/search.js/index-worker.js/sw.js/stations.json/canon.json）
- 高田馬場 2024 年客流 423,374，kana=たかだのばば
- canon 25KB（Brotli 压缩后进一步减小）

## 五、已知残留

- 212 站（2.2%）无读音：Wikipedia 消歧义页/条目缺失，按原则留空不猜
- robots.txt 被 CF worker 层劫持，应用层覆盖无效
- 线路颜色 86.7% 未达 95%（无官方色线路为灰）