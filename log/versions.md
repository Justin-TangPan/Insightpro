# 版本日志

## [0.0.7] - 2026-05-30

### 新增
- **每日洞察全系统升级**：
    - **首页门户化**：重构了 Dashboard，使其成为“今日商业市场洞察”的门户，集成行业、热点、新闻、机会四个核心板块。
    - **子版块详情页**：新增了四个详细分析页面：
        - [行业全景洞察](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/industry/page.tsx)
        - [技术热点追踪](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/hotspots/page.tsx)
        - [商业快讯监测](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/news/page.tsx)
        - [商业机会洞察](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/opportunities/page.tsx)
    - **侧边栏导航**：升级了侧边栏，支持“今日洞察”子版块的快捷导航。
    - **外部链接集成**：所有新闻、项目、行业动态均已集成外部超链接，确保信息的真实性与可追溯性。
- **后端引擎优化**：
    - 新增 `/api/daily-insight` 接口，支持多维度数据的聚合。
    - 优化了 AI 提示词工程，以生成更具深度和实战建议的商业研报。
