# Travel Hub - 前端应用

这是"新疆行程管家服务流程数字化"项目的现代化前端应用，基于 React 18 + TypeScript + Tailwind CSS 构建。

## 功能特性

- 🎯 **仪表盘** - 实时统计和通知概览
- 🗺️ **行程管理** - 创建、编辑、删除行程信息
- 🔔 **通知中心** - 管理通知模板和发送历史
- ⚙️ **偏好设置** - 配置通知渠道和频率限制
- 📊 **数据分析** - 通知性能和用户满意度分析
- 💬 **国际化** - 中文界面支持

## 技术栈

- **框架**: React 18
- **语言**: TypeScript 5
- **样式**: Tailwind CSS
- **构建**: Vite 5
- **HTTP客户端**: Axios
- **图标**: Lucide React

## 快速开始

### 环境要求

- Node.js >= 18.0
- npm 或 yarn 或 pnpm

### 安装

```bash
# 安装依赖
npm install

# 或使用 yarn
yarn install
```

### 开发

```bash
# 启动开发服务器
npm run dev

# 访问 http://localhost:5173
```

### 构建

```bash
# 生产构建
npm run build

# 预览构建结果
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── components/          # 可复用组件
│   │   ├── Sidebar.tsx      # 侧边栏导航
│   │   ├── Header.tsx       # 页面头部
│   │   ├── Card.tsx         # 卡片容器
│   │   ├── Button.tsx       # 按钮组件
│   │   ├── Badge.tsx        # 标签组件
│   │   └── Modal.tsx        # 模态框
│   ├── pages/               # 页面组件
│   │   ├── Dashboard.tsx    # 仪表盘
│   │   ├── Trips.tsx        # 行程管理
│   │   ├── Notifications.tsx # 通知中心
│   │   ├── Preferences.tsx  # 偏好设置
│   │   └── Analytics.tsx    # 数据分析
│   ├── App.tsx              # 应用主组件
│   ├── main.tsx             # 入口点
│   └── index.css            # 全局样式
├── index.html               # HTML 模板
├── vite.config.ts           # Vite 配置
├── tailwind.config.js       # Tailwind 配置
├── tsconfig.json            # TypeScript 配置
└── package.json             # 项目配置

## 页面说明

### 🎯 仪表盘
实时展示关键指标，包括：
- 今日发送通知数
- 活跃行程数
- 用户总数
- 待处理投诉数
- 最近的通知历史

### 🗺️ 行程管理
管理所有的旅行行程：
- 创建新行程
- 查看行程详情
- 编辑行程信息
- 删除已完成的行程

### 🔔 通知中心
管理通知模板和渠道：
- 创建和编辑模板
- 管理模板变量
- 查看发送统计
- 测试通知内容

### ⚙️ 偏好设置
配置系统参数：
- 启用/禁用通知渠道（短信、微信、邮件）
- 设置静默时段
- 配置频率限制
- 高级功能开关

### 📊 数据分析
查看系统性能数据：
- 通知成功率
- 渠道性能对比
- 热门行程排行
- 用户满意度趋势

## API 集成

前端通过 Axios 与后端 API 通信。代理配置在 `vite.config.ts` 中：

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

### 预期的 API 端点

- `GET /api/dashboard/stats` - 获取统计数据
- `GET /api/trips` - 获取行程列表
- `POST /api/trips` - 创建行程
- `PUT /api/trips/:id` - 更新行程
- `DELETE /api/trips/:id` - 删除行程
- `GET /api/notifications/templates` - 获取通知模板
- `POST /api/notifications/send` - 发送通知
- `GET /api/analytics/metrics` - 获取分析数据

## Workbench（首页四卡片）真实数据接入

新增的 Workbench 页面支持三种数据模式（通过 `VITE_WORKBENCH_DATA_MODE`）：

- `auto`（默认）：优先请求真实后端，失败自动回退 mock。
- `real`：只走真实后端 API。
- `mock`：只走前端本地 mock。

示例：

```bash
VITE_WORKBENCH_DATA_MODE=real npm run dev
```

如果你本地启动了后端但看不到足够数据，可运行仓库脚本自动灌入演示数据：

```bash
python scripts/seed_frontend_workbench_demo.py \
  --base-url http://127.0.0.1:8000 \
  --username admin \
  --password 123456
```

执行后刷新前端 `/dashboard`、`/tasks/todo`、`/groups/high-risk` 等页面即可看到真实后端驱动的数据。

## 样式定制

所有颜色和样式都通过 Tailwind CSS 管理，可在 `tailwind.config.js` 中定制：

```javascript
theme: {
  extend: {
    colors: {
      primary: '#3B82F6',
      secondary: '#8B5CF6',
      success: '#10B981',
      warning: '#F59E0B',
      danger: '#EF4444',
    }
  }
}
```

## 浏览器兼容性

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 许可证

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系我们

如有问题，请联系我们的开发团队。
