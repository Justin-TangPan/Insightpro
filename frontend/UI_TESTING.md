# UI 巡检

Playwright 巡检覆盖首页、五个情报板块、工作区，以及仪表盘、报告、知识库、历史记录、设置、搜索和管理端的 Sources、Events、Coverage、Email 页面；每页分别在桌面与手机视口打开。检查页面响应、主标题、空白主体、横向溢出和浏览器运行时异常，并在首页验证情报详情的进入/返回流程。

## 运行

```bash
cd frontend
npx playwright install chromium   # 首次运行安装浏览器
npm run test:ui
```

默认自动启动 Next.js 开发服务（`127.0.0.1:3100`）。已有服务或想检查某个环境时：

```bash
UI_TEST_BASE_URL=http://127.0.0.1:3000 npm run test:ui
```

HTML 报告位于 `frontend/ui-test-report/`；每个测试的截图、trace 和布局信息位于 `frontend/ui-test-results/`。受登录/权限保护的路由会按实际呈现内容检查；此巡检不创建账号、不提交表单，也不验证后端数据正确性。
