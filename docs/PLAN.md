# 駅さがし 实现计划（PLAN）

> 依据 docs/SPEC.md v1.0（已评审批准）。每任务 = TDD 循环（红→绿→重构）+ commit。

## 任务清单

### T1 管道基础：归一化 normalize.py
- 文件: pipeline/normalize.py, pipeline/tests/test_normalize.py
- 函数: norm_kanji (NFKC→opencc s2t→JP新字体表→ケ/ヶ), norm_kana (片→平), norm_roma (小写/长音剥离/去空格), norm_station_name (去括号/駅尾), norm_operator (去株式会社+别名)
- 测试用例: 渋谷/涩谷/澁谷→渋谷; 新桥→新橋; 市ヶ谷/市ケ谷; tōkyō→tokyo; シンジュク→しんじゅく

### T2 ekidata 加载 + 市町村解析
- 文件: pipeline/ekidata.py, pipeline/tests/test_ekidata.py
- 解析 station/line/company/join/pref.csv; 按 station_g_cd 分组; parse_muni 地址→(pref, muni, ward)
- 测试: 函館→北海道/函館市; 京都市下京区→京都市/下京区; 亀田郡七飯町→七飯町; 全站解析率 100%

### T3 S12 客流联表 + 年份选择
- 文件: pipeline/s12.py, pipeline/tests/test_s12.py
- 载入 S12-25 geojson; duplicate=1 筛选; (站名,运营商)别名联表; 窗口年份选择(2019←2015); 每站取运营商最大值
- 测试: 新宿JR 2019=1,578,732; 东急涩谷 2019=1,381,618; JR西大阪 2019=845,370; 无数据站→None; 东京JR东海 2019=188,476(前几年为0的回退逻辑)

### T4 读音合并
- 文件: pipeline/kana.py, pipeline/tests/test_kana.py
- Wikidata(kana+coord) + OSM(ja-Hira/ja_rm) 按站名匹配; pykakasi 兜底; 例外词典
- 测试: 新宿→よよぎ; 鹿児島中央→かごしまちゅうおう(例外词典); 覆盖率≥99% 断言

### T5 颜色表
- 文件: pipeline/colors.py, pipeline/tests/test_colors.py
- takumif + ekidata line_color + 手补表(运行系统/东京地铁别名); 无色→None
- 测试: 山手線→#9acd32; 大阪環状線→#e80000; 埼京線→手补色; 銀座線→#ff9500

### T6 近郊区間分类器 kinjo.py
- 文件: pipeline/kinjo.py, pipeline/tests/test_kinjo.py
- 解析维基 wikitext(缓存); join.csv 建线路站序图; (线路,起讫)判定 + 府县全站规则
- 测试: 新宿∈东京; 宇都宮∈东京; 函館∉; 鹿児島中央∉; 長野∈(2026版); 梅田∈大阪; 博多∈福冈

### T7 集成 build_data.py
- 文件: pipeline/build_data.py
- 全流程 → data/stations.json + lines.json + meta.json(来源/日期/覆盖率/哈希)
- 断言: 站数≥10,000; kana覆盖率≥99%; 有客流数据站≈80%; 排序正确(最大值站=新宿)

### T8 前端 search.js
- 文件: web/search.js, web/tests/search.test.mjs (node:test)
- normalize_query 与管道同语义(独立JS实现); 索引构建(排序键数组+二分); 前缀搜索; rid 倒序排序; 上限50
- 测试: 全输入格式矩阵; 排序断言(新宿在'し'结果第一位); ō→o

### T9 前端 UI/PWA
- index.html/app.js/style.css/sw.js/manifest.json/icons
- combobox 键盘导航; 虚拟列表; 详情卡; 深色模式; 离线缓存
- 人工验收: 无 slop 文案(SPEC 4.3)

### T10 浏览器冒烟
- 本地 http 服务 + browser_navigate: 输入/点击/详情/离线/console 无错

### T11 验证套件 verify/
- 抽样(种子记录) → 维基对照(名/市町村/线路/颜色/客流sanity) → 可找到性矩阵 → 报告
- 测试: 40 站 × 全格式×前缀长度

### T12 部署
- VPS tencent1: nginx vhost + cloudflared ingress → eki.kkk.jifeng.plus; 线上验证

### T13 收尾
- 更新 skill japan-railway-station-data(S12 发现); README; 最终报告

## 命令备忘
- 管道测试: cd ~/eki-sagashi && python3 -m pytest pipeline/tests -q
- 前端测试: cd ~/eki-sagashi/web && node --test tests/
- 数据构建: python3 pipeline/build_data.py
- 验证: python3 -m pytest verify/tests -q && python3 verify/run_verification.py
