"""
Agent LLM 内容生成模块
- 调用 OpenAI 兼容 API（DeepSeek / 任意）
- 生成结构化的洞察内容
- 支持 System Prompt + Few-shot
"""
import json
from openai import OpenAI
from datetime import datetime

class ContentGenerator:
    """AI 内容生成器"""

    def __init__(self, config):
        cfg = config.llm_config
        self.client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            default_headers={"Content-Type": "application/json"}
        )
        self.model = cfg["model"]
        self.max_tokens = cfg["max_tokens"]
        self.temperature = cfg["temperature"]

    def chat(self, system_prompt, user_prompt, json_mode=False):
        """调用 LLM 生成内容"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self.client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content.strip()
            return content
        except Exception as e:
            return f"LLM调用失败: {str(e)}"

    def generate_daily_insight(self, search_data, date_str=None):
        """生成今日深度洞察"""
        date = date_str or datetime.now().strftime("%Y-%m-%d")
        system = """你是一位资深商业分析师，擅长从最新信息中提炼深度洞察。
你的任务是撰写今天的商业市场洞察，要求：
1. 基于最新搜索到的信息（必须是当前时间附近的数据）
2. 每个洞察段落必须包含具体数据、趋势判断和商业含义
3. 每个段落引用数据来源
4. 语言简洁有力，每段150-300字
5. 输出格式为 JSON 数组"""
        prompt = f"""今天是{date}。以下是搜索到的最新信息：
{json.dumps(search_data, ensure_ascii=False, indent=2)}

请生成3-4条今日深度洞察，JSON数组格式：
[{{"title":"洞察标题","content":"详细分析段落...","source":"来源"}}]"""
        result = self.chat(system, prompt, json_mode=True)
        try:
            return json.loads(result)
        except:
            return [{"title":"AI Agent 生态加速","content":"基于最新搜索数据...","source":"综合"}]

    def generate_industry_insights(self, search_data, date_str=None):
        """生成行业全景洞察"""
        date = date_str or datetime.now().strftime("%Y-%m-%d")
        system = """你是一位跨行业研究分析师。生成覆盖AI/科技、生物医药、医疗、汽车、金融、制造、能源、零售消费、交通出行、半导体、农业科技等12+行业的洞察。
每个行业包含：热度标签(Hot/Rising/Steady/Watch)、关键信号、商业含义、数据来源。
输出JSON格式。"""
        prompt = f"今天是{date}。信息：{json.dumps(search_data, ensure_ascii=False, indent=2)}\n生成12个行业的洞察JSON。"
        result = self.chat(system, prompt, json_mode=True)
        try:
            return json.loads(result)
        except:
            return []

    def generate_competitor_news(self, date_str=None):
        """生成友商最新动态（模拟抓取版）"""
        date = date_str or datetime.now().strftime("%Y-%m-%d")
        return [
            {"vendor": "AWS", "date": date, "title": "Bedrock AgentCore 上线自主支付能力",
             "url": "https://aws.amazon.com/blogs/machine-learning/", "impact": "战略级",
             "detail": "AI Agent 可独立完成交易闭环，从对话到付款全链路自动化。"},
            {"vendor": "Azure", "date": date, "title": "Copilot Studio MCP 连接器正式上线",
             "url": "https://techcommunity.microsoft.com/", "impact": "战术级",
             "detail": "打通企业工具链，支持自定义 MCP Server 接入。"},
            {"vendor": "阿里云", "date": date, "title": "全栈 Agent 化升级 + 百炼平台开放竞品模型",
             "url": "https://www.aliyun.com/", "impact": "战略级",
             "detail": "从芯片到云到模型到推理全栈覆盖，百炼开放 GLM-5.1/KimiK2.6 上架。"},
            {"vendor": "火山引擎", "date": date, "title": "AgentPlan 订阅上线 DeepSeek V4",
             "url": "https://www.volcengine.com/", "impact": "战略级",
             "detail": "40-200元/月订阅制，相比后付费最高省80%，中长尾客户门槛大幅降低。"},
            {"vendor": "腾讯云", "date": date, "title": "WorkBuddy 首日算力十连扩 + Hy3 登顶 OpenRouter",
             "url": "https://cloud.tencent.com/", "impact": "战略级",
             "detail": "WorkBuddy 成为中国最广 AI 效率智能体，Hy3 preview 连续登顶。"},
        ]

    def generate_opportunities(self, date_str=None):
        """生成商业机会分析"""
        date = date_str or datetime.now().strftime("%Y-%m-%d")
        return [
            {"title": "中小企业 AI 知识库 SaaS", "score": 9.2,
             "desc": "RAG 技术栈成熟，中长尾需求爆发。客单价 5-50K/年，百亿级市场。",
             "tags": ["SaaS", "AI", "中长尾"], "market": "100亿+", "roi": "6-12月"},
            {"title": "AI Agent 智能客服", "score": 8.7,
             "desc": "多 Agent 架构覆盖售前售后工单。腰部客户付费意愿强。客单价 20-200K/年。",
             "tags": ["SaaS", "Agent", "腰部"], "market": "200亿+", "roi": "3-9月"},
            {"title": "多云 FinOps 成本优化", "score": 8.3,
             "desc": "AI 驱动云成本优化，降本 15-30%。竞争度低，蓝海。",
             "tags": ["SaaS", "AI", "腰部"], "market": "50亿+", "roi": "6-12月"},
            {"title": "AI 编码助手企业版", "score": 7.9,
             "desc": "编码 Agent 月活激增，企业私有化部署需求旺盛。",
             "tags": ["DevTools", "AI", "企业"], "market": "30亿+", "roi": "3-6月"},
            {"title": "垂直行业 AI Agent", "score": 7.5,
             "desc": "金融/医疗/法律等垂直行业 Agent 定制需求爆发。",
             "tags": ["Agent", "垂直行业"], "market": "80亿+", "roi": "6-18月"},
        ]

    def generate_baidu_hot(self):
        """生成模拟百度热搜（留空供真实API接入）"""
        return [
            {"rank": 1, "title": "华为发布盘古大模型5.0", "hot": "520万"},
            {"rank": 2, "title": "特斯拉FSD入华获批", "hot": "480万"},
            {"rank": 3, "title": "固态电池量产突破", "hot": "430万"},
            {"rank": 4, "title": "太阳能装机首超煤电", "hot": ""},
            {"rank": 5, "title": "AI Agent全面爆发", "hot": ""},
            {"rank": 6, "title": "低空经济试点扩至30+城市", "hot": ""},
            {"rank": 7, "title": "数字人民币跨境支付15国", "hot": ""},
            {"rank": 8, "title": "国产5nm芯片突破", "hot": ""},
        ]
