export type FocusEvent = {
  id: string;
  vendor: string;
  happened_at: string;
  date_basis: string;
  type: string;
  board: string;
  title: string;
  summary: string;
  why: string;
  importance: number;
  sources: { name: string; url: string }[];
  image_url?: string;
};

export type FocusType = "新 Agent" | "新产品" | "新模型" | "新项目" | "新应用" | "新平台能力" | "重大更新";
export type RecentFocus = { event: FocusEvent; type: FocusType; date: string; dateBasis: "published" | "observed" | "source" | "version" };

const priority = (type: FocusType) => type === "新 Agent" ? 0 : type === "新产品" || type === "新应用" ? 1 : type === "新模型" ? 2 : type === "新项目" ? 3 : type === "新平台能力" ? 4 : 5;
const announcement = /brand.new|newly launched|first.*(?:release|launch)|launch(?:es|ed)?|introduc|announc|debut|unveil|release|released|\bis live\b|推出|发布|上线|开放使用|正式可用|首次/i;
const update = /update|updated|upgrade|version|版本|升级|更新|v\d+(?:\.\d+)+/i;
const lowValue = /case study|customer story|实践案例|客户案例|教程|使用指南|how.to|how to use|最佳实践|文档更新|documentation update|release notes|changelog|blog post|文章介绍|in action|same quality|lower cost|put to the test|hardcore tasks|benchmark|性能对比|成本降低/i;
const modelVersion = /\b(?:gpt|gemini|qwen|deepseek|llama|glm)\s*[-v ]?\d+(?:\.\d+)*|kimi\s*k\d+(?:\.\d+)*|claude\s+(?:sonnet|opus|haiku)\s*\d+(?:\.\d+)*/i;
const newCapability = /new capability|new feature|now supports|adds? support|introduc(?:es|ing)? .{0,24}(?:memory|feature|capability)|新增能力|新增支持|新增功能|新能力|新功能|能力上线|(?:原生|新增|提供).{0,12}支持/i;

export function focusType(event: FocusEvent): FocusType | null {
  const text = `${event.type} ${event.title} ${event.summary}`;
  const headline = event.title;
  if (event.board === "solutions" || lowValue.test(text)) return null;
  const launched = announcement.test(headline);
  const aiRelated = /\bai\b|agent|智能体|模型|大模型|llm|copilot|generative|生成式/i.test(text);
  const agent = /agent|智能体/i.test(headline);
  const model = /模型|大模型|\bllm\b|\bmodel\b/i.test(headline) || modelVersion.test(headline) || (/\bk\d+(?:\.\d+)+\b/i.test(headline) && /模型|\bmodel\b/i.test(text));
  if (event.board === "github") return launched && !update.test(headline) ? "新项目" : null;
  if (agent && launched && !update.test(headline)) return "新 Agent";
  if (model && launched && !/policy|策略|api|接口/i.test(headline)) return "新模型";
  if (event.board === "apps" && newCapability.test(text) && aiRelated) return "新平台能力";
  if (launched && !update.test(headline) && event.board === "apps") return "新应用";
  if (launched && !update.test(headline) && aiRelated && event.board === "competitors") return "新产品";
  if (newCapability.test(text) && aiRelated) return "新平台能力";
  if (update.test(headline) && aiRelated && /major|important|significant|重大|重要|全新版本|旗舰|大版本/i.test(text)) return "重大更新";
  return null;
}

export function selectRecentFocus(events: FocusEvent[], asOf: string, limit = 5): RecentFocus[] {
  const asOfDay = Date.parse(`${asOf.slice(0, 10)}T00:00:00Z`);
  if (!Number.isFinite(asOfDay) || limit <= 0) return [];
  const recent: (RecentFocus & { age: number })[] = [];
  const older: (RecentFocus & { age: number })[] = [];
  for (const event of events) {
    const type = focusType(event);
    let date = event.happened_at.slice(0, 10);
    let dateBasis: RecentFocus["dateBasis"] = event.date_basis === "observed" ? "observed" : "published";
    if (dateBasis === "observed") {
      const anchor = event.sources.find(source => /#(?:update|release)-\d{4}-\d{1,2}-\d{1,2}/i.test(source.url))?.url.match(/#(?:update|release)-(\d{4})-(\d{1,2})-(\d{1,2})(?:-|$)/i);
      if (anchor) {
        const candidate = new Date(Date.UTC(Number(anchor[1]), Number(anchor[2]) - 1, Number(anchor[3])));
        if (candidate.getUTCFullYear() === Number(anchor[1]) && candidate.getUTCMonth() === Number(anchor[2]) - 1 && candidate.getUTCDate() === Number(anchor[3]) && candidate.toISOString().slice(0, 10) <= date) {
          date = candidate.toISOString().slice(0, 10);
          dateBasis = "source";
        }
      }
    }
    const headlineDate = event.title.match(/^(20\d{2}-\d{2}-\d{2})\b/)?.[1];
    const headlineDay = Date.parse(`${headlineDate}T00:00:00Z`);
    if (headlineDate && Number.isFinite(headlineDay) && new Date(headlineDay).toISOString().slice(0, 10) === headlineDate && headlineDate <= date && Date.parse(`${date}T00:00:00Z`) - headlineDay <= 29 * 86400000) {
      date = headlineDate;
      dateBasis = "published";
    }
    if (type === "新模型" && dateBasis === "observed") {
      const suffix = `${event.title} ${event.summary}`.match(/\b[A-Za-z][A-Za-z0-9.-]*-(0[1-9]|1[0-2])([0-3]\d)\b/);
      if (suffix) {
        const observed = Date.parse(`${date}T00:00:00Z`);
        const candidate = new Date(Date.UTC(Number(date.slice(0, 4)), Number(suffix[1]) - 1, Number(suffix[2])));
        if (candidate.getUTCMonth() === Number(suffix[1]) - 1 && candidate.getUTCDate() === Number(suffix[2]) && observed >= candidate.getTime() && observed - candidate.getTime() <= 29 * 86400000) {
          date = candidate.toISOString().slice(0, 10);
          dateBasis = "version";
        }
      }
    }
    const day = Date.parse(`${date}T00:00:00Z`);
    if (!type || !Number.isFinite(day) || day > asOfDay) continue;
    const age = Math.floor((asOfDay - day) / 86400000);
    if (age > 29) continue;
    (age < 7 ? recent : older).push({ event, type, date, dateBasis, age });
  }
  const sort = (a: RecentFocus & { age: number }, b: RecentFocus & { age: number }) =>
    a.age - b.age || priority(a.type) - priority(b.type) || b.event.importance - a.event.importance ||
    b.event.sources.length - a.event.sources.length || a.age - b.age;
  recent.sort(sort);
  older.sort(sort);
  return [...recent, ...older].slice(0, limit).map(({ event, type, date, dateBasis }) => ({ event, type, date, dateBasis }));
}
