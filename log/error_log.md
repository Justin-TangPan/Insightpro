# 已关闭问题记录

本文件只保留仍有排障价值的已关闭问题；当前发布风险与验证结果统一记录在 `log/versions.md`。

## 2026-05-30：Lucide GitHub 图标导出错误

- 现象：前端开发构建提示 `Export Github doesn't exist in target module "lucide-react"`。
- 原因：代码使用了与当时依赖版本不一致的图标导出名。
- 处理：改用该版本实际提供的 GitHub 图标组件。
- 状态：已关闭，当前前端 ESLint 和生产构建通过。

如问题再次出现，以当前 `frontend/package.json`、实际导出和构建日志为准，不复用历史本地路径。
