import { tool } from "@opencode-ai/plugin"

const routes = {
  overview: "/homepage/modules",
  hotspots: "/github-trending?since=daily",
  solutions: "/solutions/aliyun",
} as const

export default tool({
  description: "读取 InsightPro 当前公共数据。用于查询首页概览、技术热点、阿里云解决方案或公共搜索；不包含用户私有数据。",
  args: {
    dataset: tool.schema.enum(["overview", "hotspots", "solutions", "search"]),
    query: tool.schema.string().max(100).optional(),
    limit: tool.schema.number().min(1).max(30).default(10),
  },
  async execute({ dataset, query, limit }) {
    if (dataset === "search" && !query?.trim()) return "公共搜索需要 query。"
    const base = process.env.INSIGHT_PUBLIC_API_URL || "http://host.docker.internal:8000/api"
    const path = dataset === "search"
      ? `/search?q=${encodeURIComponent(query!.trim())}&page_size=${limit}`
      : routes[dataset]
    const response = await fetch(base + path, { signal: AbortSignal.timeout(15000) })
    if (!response.ok) throw new Error(`InsightPro public API ${response.status}`)
    const data: any = await response.json()
    if (dataset === "overview" && Array.isArray(data))
      data.splice(0, data.length, ...data.filter((item) => ["hotspots", "solutions"].includes(item?.id)))
    for (const key of ["items", "results"])
      if (Array.isArray(data?.[key])) data[key] = data[key].slice(0, limit)
    if (Array.isArray(data)) data.splice(limit)
    return JSON.stringify(data)
  },
})
