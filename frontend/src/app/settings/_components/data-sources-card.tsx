"use client";

import { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";

type Dataset = { key: string; total: number; latest_at: string | null };
type Run = { status?: string; started_at?: string; error?: string };
type Task = { key: string; name: string; schedule: string; next_run_at: string; last_run?: Run };

const labels: Record<string, string> = {
  github_trending: "GitHub 趋势", baidu_hotsearch: "百度热搜", competitor_news: "友商动态",
  aliyun_solutions: "阿里云方案", huawei_solutions: "华为云方案", vendor_ai_applications: "AI 应用官方动态",
};
const taskDatasets: Record<string, string[]> = {
  github_daily: ["github_trending"], solution_catalogs_daily: ["aliyun_solutions", "huawei_solutions"],
  community_insights_daily: ["baidu_hotsearch"], competitor_daily: ["competitor_news"], ai_applications_daily: ["vendor_ai_applications"],
};
const date = (value?: string | null) => value ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }) : "暂无";
const status = (task?: Task) => task?.last_run?.status === "success" ? "成功" : task?.last_run?.status === "failed" ? "失败" : task?.last_run?.status === "running" ? "运行中" : "尚无记录";

export function DataSourcesCard() {
  const { user, loading } = useAuth();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (loading || user?.app_metadata?.role !== "admin") return;
    authenticatedFetch(`${API}/api/admin/collection`).then(response => {
      if (!response.ok) throw new Error("加载失败");
      return response.json();
    }).then(data => { setDatasets(data.datasets || []); setTasks(data.tasks || []); })
      .catch(() => setError("数据采集状态加载失败"));
  }, [loading, user]);

  const datasetByKey = Object.fromEntries(datasets.map(item => [item.key, item]));
  return <section className="ui-card lg:col-span-2" aria-labelledby="data-source-title">
    <div className="ui-card-header"><Database className="h-4 w-4 text-ink-muted" /><h3 id="data-source-title" className="type-h3 text-ink">数据采集状态</h3></div>
    {error ? <p role="alert" className="py-5 text-sm text-danger">{error}</p> : <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {tasks.filter(task => taskDatasets[task.key]).map(task => <article key={task.key} className="rounded-xl border border-grid p-4">
        <h4 className="text-sm font-semibold text-ink">{task.name}</h4>
        <dl className="mt-3 space-y-2 text-xs">
          {taskDatasets[task.key].map(key => <div key={key} className="flex justify-between gap-2"><dt className="text-ink-muted">{labels[key]}</dt><dd className="text-right text-ink">{datasetByKey[key] ? `${datasetByKey[key].total} 条 · ${date(datasetByKey[key].latest_at)}` : "暂无数据"}</dd></div>)}
          <div className="flex justify-between gap-2"><dt className="text-ink-muted">计划 / 最近状态</dt><dd className="text-right text-ink">{task.schedule} · {status(task)}</dd></div>
        </dl>
        {task.last_run?.status === "failed" && task.last_run.error && <p className="mt-2 line-clamp-2 text-xs text-danger">{task.last_run.error}</p>}
      </article>)}
    </div>}
  </section>;
}
