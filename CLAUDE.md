# InsightWeb 项目规则

## 版本记录

每次完成可验证整改、功能变更、依赖调整或架构迁移后，必须同步更新 `log/versions.md`。

- 使用内部小版本号递增，例如 `0.0.8` → `0.0.9`。
- 记录日期必须使用实际日期。
- 内容至少包含：修复/新增/调整、验证结果、已知遗留。
- 如果本次变更只完成了阶段性整改，也要记录当前阶段的验证状态，避免代码状态和项目说明脱节。

## 智能助手

- 智能助手必须全局挂载在 `frontend/src/app/layout.tsx`，通过 `frontend/public/chat.js` 加载。
- 生产部署不得回退到 `localhost` 作为助手 API 地址，必须由 `window.__CHAT_API_URL__` 注入实际后端地址。
- 调整主导航、核心模块名称或路由时，必须同步更新 `backend/routers/chat.py` 的助手知识库和 `frontend/public/chat.js` 的快捷问题。
- 如果助手不可用，必须在本轮整改中验证 `/api/chat` 或 `/api/chat/stream` 的错误原因并记录。

## 变更后自动重启

每次代码变更完成后，必须立即重新部署前后端服务，无需等待用户要求。

### 部署步骤

1. **提交已验证变更并部署 Docker 双容器**：
   ```bash
   ./scripts/deploy-docker.sh
   ```

2. **验证**：
   ```bash
   ./scripts/health-check.sh full
   docker ps --filter name=insight-
   ```

## 看门狗

- Linux Docker 部署由 `insight-docker-health-guard.timer` 负责健康守护；使用 `scripts/health-check.sh full` 检查。
