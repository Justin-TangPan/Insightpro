# InsightPro 前端

这是 InsightPro 的 Next.js 16 / React 19 前端。项目采用 App Router、TypeScript、Tailwind CSS 4 和 Recharts，通过同源 `/api/*` 访问 FastAPI。

## 启动

```bash
npm ci
npm run dev
```

本地地址为 <http://localhost:3000>。默认代理到 `http://127.0.0.1:8000`；容器环境通过 `API_PROXY_TARGET=http://backend:8000` 覆盖。

Supabase 登录和注册还需要在根目录 `.env` 配置：

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## 目录约定

| 路径 | 内容 |
|---|---|
| `src/app/` | 页面、根布局和全局样式 |
| `src/components/` | 侧边栏、搜索、聊天助手和通用 UI |
| `src/lib/` | API、认证和 Supabase 客户端 |
| `public/chat.js` | 全局聊天助手运行脚本与快捷问题 |
| `prisma/schema.prisma` | 后端 public 表的数据契约镜像 |
| `next.config.ts` | standalone 输出和 `/api` 同源代理 |

全局聊天助手由 `src/app/layout.tsx` 挂载，生产环境地址来自 `window.__CHAT_API_URL__`。导航或核心能力变更时，应同步更新 `public/chat.js` 和后端 `routers/chat.py` 的知识说明。

## 质量门禁

```bash
npm run lint
npx prisma validate
npm run build
```

生产镜像使用 standalone 输出，正式部署统一从仓库根目录执行 `sudo ./scripts/deploy-docker.sh`。完整页面、接口和架构信息见根目录 [README](../README.md) 与 [架构清单](../doc/技术架构与业务架构清单.md)。
