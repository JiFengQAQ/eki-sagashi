# 部署

线上地址: **https://eki.jifeng.plus**（纯静态 PWA）

## 架构

```
Internet → Cloudflare Edge (TLS 通配证书 *.jifeng.plus)
  → CNAME eki.jifeng.plus → tunnel.tencent1.jifeng.plus
  → cloudflared (tencent1 VPS, token 模式)
  → nginx 127.0.0.1:80 (vhost: eki.jifeng.plus)
  → /var/www/eki-sagashi/ (静态文件: index.html + stations.json 2.9MB + canon.json)
```

## 部署步骤（数据更新后）

```bash
# 1. 重建数据
cd ~/eki-sagashi && python3 pipeline/build_data.py
# 2. 同步到部署目录
sudo cp -r ~/eki-sagashi/web/* /var/www/eki-sagashi/
sudo chown -R www-data:www-data /var/www/eki-sagashi
# 3. nginx 配置已就位, 无需改 (vhost: /etc/nginx/sites-enabled/eki.kkk.jifeng.plus)
```

## CF 侧（dashboard, 极少变更）

- Published application route: `eki.jifeng.plus → http://localhost:80`（tunnel.tencent1.jifeng.plus）
- 不要用二级子域（如 eki.kkk.jifeng.plus）— CF 通配证书只覆盖 `*.jifeng.plus`，二级子域 TLS 握手失败
- 无 Access 策略（默认公开）

## 验证

```bash
curl -s -o /dev/null -w "%{http_code}" https://eki.jifeng.plus/   # 200
curl -s https://eki.jifeng.plus/stations.json | head -c 100        # JSON
```

## 部署操作笔记（2026-08-03）

- CF Dashboard 操作走 WSL webtop Chromium CDP（cross-device-cdp-browser skill）:
  本机 Turnstile 机器人检测过不去; WSL webtop 有用户登录会话
- React 表单必须真实键盘输入 (Input.insertText), JS 注入 value 不触发 state
- CDP 截图坐标 = viewport × devicePixelRatio(1.5), 点击要用换算后的 viewport 坐标
- /home/ubuntu 权限 750, nginx(www-data) 读不了 → 部署目录必须放 /var/www
