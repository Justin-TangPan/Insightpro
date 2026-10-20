export type Mode = "floating" | "split" | "full";

export type Message = {
  role: "user" | "assistant";
  content: string;
  artifacts?: Artifact[];
  failed?: boolean;
};

export type Context = {
  context_id?: string;
  title: string;
  summary?: string;
  context_type: string;
  content?: string;
  metadata?: Record<string, unknown>;
  source_url?: string;
  related_entities?: { title: string }[];
  supplement?: string;
  excluded_sections?: string[];
};

export type Session = {
  id: string;
  title: string;
  context_type: string;
  context_title: string;
  context_snapshot?: Context;
  task_key?: string;
  task_title?: string;
  task_status?: string;
  default_prompt?: string;
  conversation?: Message[];
};

export type Artifact = {
  id: string;
  session_id?: string;
  title: string;
  filename?: string;
  mime_type?: string;
  size_bytes?: number;
  type: string;
  knowledge_status: string;
  created_at: string;
  content?: string;
};

export type ActionProposal = {
  id: string;
  action:
    | "create_requirement_draft"
    | "create_solution_draft"
    | "append_note"
    | "update_draft_content";
  payload: Record<string, unknown>;
  status: string;
};

export type Interaction = {
  request_id: string;
  session_id: string;
  question: string;
  choices: string[];
  multi_select?: boolean;
};

export const nextActions: Record<string, string[]> = {
  technology_research: ["收纳为方案实践", "对比技术路线", "规划 PoC"],
  technology_value: ["收纳为方案实践", "深入研究", "规划 PoC"],
  solution_analysis: ["技术架构分析", "收纳为方案实践", "规划 PoC"],
  solution_architecture: ["规划 PoC", "完善方案实践", "开始实现"],
  solution_design: ["规划 PoC", "开始实现", "生成技术材料"],
  requirement_analysis: ["完善背景", "形成方案实践", "关联已有实践"],
  requirement_refine: ["确认背景", "形成方案实践", "规划 PoC"],
  poc_plan: ["开始验证", "开始实现", "生成部署材料"],
  validation: ["回到架构设计", "开始实现", "生成测试报告"],
  implementation: ["查看工作文件", "开始验证", "生成部署材料"],
};

export const nextActionVariants: Record<string, string[][]> = {
  technology_research: [
    ["提炼关键结论", "补充竞品对比", "列出 PoC 验证项"],
    ["判断落地价值", "识别技术风险", "生成调研摘要"],
    ["输出选型建议", "拆解依赖条件", "形成决策清单"],
  ],
  technology_value: [
    ["量化业务价值", "识别落地依赖", "给出是否验证建议"],
    ["分析替代方案", "补齐风险证据", "生成决策摘要"],
  ],
  solution_analysis: [
    ["提炼方案亮点", "识别架构限制", "给出适用边界"],
    ["对比替代路线", "补充风险与缺口", "整理决策摘要"],
  ],
  solution_architecture: [
    ["输出组件关系", "检查集成边界", "列出架构风险"],
    ["补齐非功能要求", "生成部署拓扑", "规划验证路径"],
  ],
  solution_practice: [
    ["校对实践背景", "补齐事实与缺口", "整理方案目录"],
    ["生成架构契约", "规划实施步骤", "检查交付材料"],
  ],
  solution_design: [
    ["细化实施阶段", "补充验收标准", "识别设计风险"],
    ["输出组件清单", "规划部署路径", "生成技术摘要"],
  ],
  requirement_analysis: [
    ["补齐需求缺口", "提炼验收标准", "识别范围风险"],
    ["整理业务目标", "拆解非功能要求", "形成需求摘要"],
  ],
  requirement_refine: [
    ["检查需求边界", "补充约束条件", "生成确认清单"],
    ["完善验收标准", "整理待确认项", "形成可执行草稿"],
  ],
  poc_plan: [
    ["定义成功指标", "拆解验证步骤", "列出环境依赖"],
    ["补充退出条件", "识别 PoC 风险", "生成执行清单"],
  ],
  validation: [
    ["列出验证证据", "检查通过标准", "整理测试范围"],
    ["补充异常场景", "生成验证报告", "规划后续处置"],
  ],
  implementation: [
    ["拆解文件变更", "制定测试策略", "检查实现风险"],
    ["生成执行计划", "识别依赖阻塞", "准备部署材料"],
  ],
  materials: [
    ["整理交付目录", "检查引用完整性", "生成材料摘要"],
    ["补充待确认内容", "统一术语格式", "导出交付清单"],
  ],
};

export const taskStages: Record<string, string> = {
  technology_research: "理解",
  technology_value: "理解",
  solution_analysis: "理解",
  solution_architecture: "设计",
  solution_design: "设计",
  requirement_analysis: "理解",
  requirement_refine: "设计",
  poc_plan: "验证",
  validation: "验证",
  implementation: "实现",
  materials: "交付",
};
