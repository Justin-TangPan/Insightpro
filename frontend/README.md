# 小雷达前端

这是小雷达 v1.1.0 的 Next.js 16 / React 19 前端。项目采用 App Router、TypeScript、Tailwind CSS 4 和 Recharts，通过同源 `/api/*` 访问服务接口。页面覆盖首页简讯、五类情报业务、事件详情、管理员运营工作台和用户方案实践。

## 启动

```bash
npm ci
npm run dev
```

本地地址为 <http://localhost:3000>。默认代理到 `http://127.0.0.1:8000`；容器环境通过 `API_PROXY_TARGET=http://insight-backend:8000` 覆盖。

Supabase 登录和注册还需要在根目录 `.env` 配置：

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## 目录约定

| 路径 | 内容 |
|---|---|
| `src/app/` | 页面、根布局和全局样式 |
| `src/components/` | 侧边栏、搜索、Insight-Agent Shell 和通用 UI |
| `src/lib/` | API、认证、Workbench 数据契约和 Supabase 客户端 |
| `next.config.ts` | standalone 输出和 `/api` 同源代理 |

交互式 AI 入口由 `src/app/layout.tsx` 挂载的 `InsightAgentShell` 提供。`public/chat.js` 与 `/api/chat` 是未挂载的兼容实现，不构成产品入口。

## 质量门禁

```bash
npm run lint
npm run build
```

生产镜像使用 standalone 输出。正式部署统一从仓库根目录执行 `sudo bash scripts/deploy-docker.sh`，脚本会运行后端测试、前端 lint、双端镜像构建和完整健康检查。完整页面、接口和架构信息见根目录 [README](../README.md) 与 [架构清单](../doc/技术架构与业务架构清单.md)。
