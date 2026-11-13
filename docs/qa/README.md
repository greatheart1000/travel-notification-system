# QA 验证材料

本目录保存产品验收用的报告、截图和复现方式，不再放在 `/tmp`。

- `product-v2-report.md`：本轮产品优化与视觉改版报告
- `screenshots/`：登录页、团队执行、行程列表、导游移动端、群提醒 AI 生成、规则内容展开、导游工作台、天气应急 Agent、AI 建议、导游移动端工作台、行程发送计划、每团发送模式、分岗位消息、岗位接收配置、团队执行发送模式、月亮旅行品牌、彩色改版后的行程/团队/工作台/发送计划/规则/账单、Unslop 后的登录/行程/团队/用户/工作台/发送计划

## 本地复现

1. 启动后端（QA 数据目录在仓库内 `var/qa-db`，已加入 `.gitignore`）：

```bash
cd /mnt/d/caijian/travel-notification-system
PYTHONPATH=src APP_ENV=dev \
TRAVEL_NOTIFICATION_DB_DIR="$PWD/var/qa-db" \
SEED_DEMO_DATA=false SEED_DEMO_USERS=false \
TRAVEL_NOTIFICATION_DEFAULT_PASSWORD=Demo123456 \
BOOTSTRAP_ADMIN_USERNAME=admin \
BOOTSTRAP_ADMIN_PASSWORD=Demo123456 \
SMS_PROVIDER=mock PAYMENT_PROVIDERS=mock \
RUN_SCHEDULER=false NOTIFICATION_QUEUE_INTERVAL_SECONDS=3600 \
.venv/bin/python -c "from app.api.http import run_http_server; run_http_server(host='127.0.0.1', port=3001)"
```

2. 初始化 3 个租户、21 个账号、20 条行程：

```bash
python3 scripts/qa_seed.py
```

3. 启动前端：

```bash
cd frontend && npm run dev -- --host 127.0.0.1
```

访问 `http://127.0.0.1:5173`，管理员 `admin / Demo123456`，导游 `zhaoyue / Demo123456`（赵玥）。
