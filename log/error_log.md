# 错误日志

## [2026-05-30] - Build Error: Export Github doesn't exist

### 错误描述
在运行 `npm run dev` 时，Next.js 报错：`Export Github doesn't exist in target module "lucide-react"`。

### 原因分析
`lucide-react` 库中，GitHub 的图标组件名称为 `GithubIcon` (或 `Github`)，在某些版本中导出名称可能存在差异。当前环境下应使用 `GithubIcon`。

### 解决方案
修改 [page.tsx](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/page.tsx) 中的引用：
- `import { Github }` -> `import { GithubIcon }`
- 使用图标处 `icon: Github` -> `icon: GithubIcon`

### 状态
已修复。
