import { nextActions, nextActionVariants } from "./types";
import type { Context } from "./types";

export function recommendedActions(taskKey: string, turn: number) {
  const variants = nextActionVariants[taskKey];
  if (variants?.length) return variants[turn % variants.length];
  return nextActions[taskKey] || ["继续处理", "生成实施建议"];
}

export function freeChatPrompts(pathname: string, title = "当前页面") {
  const subject = title.trim().slice(0, 24) || "当前页面";
  if (subject !== "当前页面")
    return [
      `"${subject}"解决什么问题？`,
      `分析"${subject}"的关键风险`,
      `提炼"${subject}"的核心结论`,
      `如何验证"${subject}"的可行性？`,
    ];
  if (pathname.includes("hotspots"))
    return [
      "这个项目解决什么问题？",
      "评估成熟度和落地风险",
      "给出 PoC 验证建议",
      "对比可替代技术",
    ];
  if (pathname.includes("solutions"))
    return [
      "提炼这个方案的关键能力",
      "分析架构与适用边界",
      "整理成解决方案实践",
      "列出实施风险",
    ];
  if (pathname.includes("workbench"))
    return [
      "继续完善当前方案",
      "检查背景信息缺口",
      "规划下一步实施",
      "生成可交付材料",
    ];
  return [
    "帮我提炼页面关键信息",
    "分析潜在风险和机会",
    "给出下一步行动建议",
    "把内容整理成方案实践",
  ];
}

export function contextItems(context?: Context) {
  if (!context) return [];
  return [
    context.summary && "对象描述",
    context.content && "业务内容",
    Object.keys(context.metadata || {}).length && "结构化信息",
    context.source_url && "来源链接",
    context.related_entities?.length && "关联业务对象",
  ].filter(Boolean) as string[];
}

export const formatBytes = (size = 0) =>
  size < 1024
    ? `${size} B`
    : `${(size / 1024).toFixed(size < 10240 ? 1 : 0)} KB`;
