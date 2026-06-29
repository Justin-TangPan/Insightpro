# InsightWeb 项目规则

## 变更后自动重启

每次代码变更完成后，必须立即重新部署前后端服务，无需等待用户要求。

### 部署步骤

1. **后端部署**（如果修改了 `backend/` 下的代码）：
   ```powershell
   # 停止旧进程
   Stop-Process -Id (netstat -ano | Select-String ":8000" | ForEach-Object { $_ -split '\s+' | Select-Object -Last 1 }) -Force -ErrorAction SilentlyContinue
   # 启动新进程
   cd C:\Users\Administrator\Desktop\Project\traeproject\insight-web\backend
   .\venv\Scripts\python.exe main.py
   ```

2. **前端部署**（如果修改了 `frontend/` 下的代码）：
   ```powershell
   cd C:\Users\Administrator\Desktop\Project\traeproject\insight-web\frontend
   npm run build
   # 停止旧进程
   Stop-Process -Id (netstat -ano | Select-String ":3000" | ForEach-Object { $_ -split '\s+' | Select-Object -Last 1 }) -Force -ErrorAction SilentlyContinue
   # 启动新进程
   npx.cmd next start -p 3000
   ```

3. **验证**：
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/   # 应返回 200
   curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/   # 应返回 200
   ```

## 看门狗

- 看门狗脚本：`scripts/watchdog.ps1`（监控 3000 和 8000 端口，每 30 秒检测一次）
- 通过计划任务 `InsightProWatchdog` 实现开机自启
- 如果看门狗未运行，手动启动：`scripts/watchdog.ps1`
- 看门狗日志：`scripts/watchdog.log`
