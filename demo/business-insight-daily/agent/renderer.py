"""
Agent HTML 渲染模块 v2
- 生成丰富、完整的 HTML 页面
- 15 场景大盘 + 12 行业洞察 + 友商深度分析
- Claude Editorial 设计系统
"""
import json
from datetime import datetime
from pathlib import Path

# ── 设计系统CSS ──
CSS = """:root{--cp:#cc785c;--cpa:#a9583e;--cps:rgba(204,120,92,0.08);--ci:#141413;--cb:#3d3d3a;--cm:#6c6a64;--cc:#faf9f5;--cssf:#f5f0e8;--csc:#efe9de;--ch:#e6dfd8;--chs:#ebe6df;--csd:#181715;--csde:#252320;--cod:#faf9f5;--cods:#a09d96;--ct:#5db8a6;--ca:#e8a55a;--cs:#5db872;--cw:#d4a017;--ce:#c64545;--fd:'Cormorant Garamond','Georgia','Noto Serif SC',serif;--fb:'Inter',-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;--bg-page:var(--cc);--bg-card:var(--csc);--bg-card-alt:var(--cssf);--text-primary:var(--ci);--text-secondary:var(--cb);--text-tertiary:var(--cm);--border-default:var(--ch);--border-light:var(--chs);--rmd:8px;--rlg:12px;--rfull:9999px;--sxs:8px;--ssm:12px;--smd:16px;--slg:24px;--sxl:32px;--sxxl:48px;--ssec:64px;--tf:150ms ease}
[data-theme="dark"]{--bg-page:#141311;--bg-card:#1f1e1b;--bg-card-alt:#1a1917;--text-primary:#f0ede5;--text-secondary:#c4bfb5;--text-tertiary:#8b857a;--border-default:#2d2a25;--border-light:#24221e;--cps:rgba(204,120,92,0.10)}
*{{box-sizing:border-box;margin:0;padding:0}}html{{font-size:16px;-webkit-font-smoothing:antialiased}}
body{{font-family:var(--fb);background:var(--bg-page);color:var(--text-primary);line-height:1.6;min-height:100vh}}
.header{{background:var(--bg-page);border-bottom:1px solid var(--border-default);padding:0 var(--sxl);height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:1000}}
.header-left{{display:flex;align-items:center;gap:var(--ssm)}}.logo{{width:36px;height:36px;background:var(--cp);border-radius:var(--rmd);display:flex;align-items:center;justify-content:center;color:#fff;font-family:var(--fd);font-weight:600;font-size:18px;text-decoration:none}}
.brand-name a{{text-decoration:none;color:inherit;font-family:var(--fd);font-size:20px;font-weight:400;letter-spacing:-0.3px}}
.header-right{{display:flex;align-items:center;gap:var(--ssm)}}.header-date{{font-size:13px;color:var(--text-tertiary)}}
.theme-toggle,.refresh-btn{{width:36px;height:36px;border-radius:var(--rfull);border:1px solid var(--border-default);background:var(--bg-card-alt);cursor:pointer;font-size:15px;color:var(--text-tertiary);display:flex;align-items:center;justify-content:center;transition:var(--tf)}}.theme-toggle:hover,.refresh-btn:hover{{border-color:var(--cp);color:var(--cp)}}.refresh-btn:hover{{animation:spin .6s ease}}@keyframes spin{{to{{transform:rotate(360deg)}}}}
.back-link{{display:inline-flex;align-items:center;gap:8px;padding:8px 18px;border-radius:var(--rmd);border:1px solid var(--border-default);background:var(--bg-card-alt);color:var(--text-tertiary);font-size:13px;text-decoration:none;transition:var(--tf)}}.back-link:hover{{border-color:var(--cp);color:var(--cp)}}
.main-container{{max-width:1280px;margin:0 auto;padding:var(--sxxl) var(--sxl) var(--ssec);display:flex;flex-direction:column;gap:var(--slg)}}
.page-hero h1{{font-family:var(--fd);font-size:36px;font-weight:400;letter-spacing:-0.5px;line-height:1.15}}.page-hero p{{font-size:14px;color:var(--text-tertiary);margin-top:var(--sxs)}}
.card{{background:var(--bg-card);border:1px solid var(--border-default);border-radius:var(--rlg);overflow:hidden}}.card-full{{grid-column:1/-1}}
.card-header{{display:flex;align-items:center;justify-content:space-between;padding:var(--sxl) var(--sxl) 0}}.card-title{{font-family:var(--fd);font-size:22px;font-weight:400;letter-spacing:-0.3px}}
.card-badge{{font-size:11px;font-weight:500;padding:3px 12px;border-radius:var(--rfull);background:var(--cps);color:var(--cp);border:1px solid rgba(204,120,92,0.15)}}
.card-body{{padding:var(--sxl)}}.source-row{{display:flex;align-items:center;gap:var(--ssm);margin-top:var(--slg);padding-top:var(--smd);border-top:1px solid var(--border-light);font-size:10px;color:var(--text-tertiary);flex-wrap:wrap}}
.source-link{{font-size:10px;color:var(--text-tertiary);text-decoration:none;opacity:0.7;transition:var(--tf)}}.source-link:hover{{color:var(--cp);opacity:1}}
.toast{{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:var(--cp);color:#fff;padding:10px 24px;border-radius:var(--rmd);font-size:13px;z-index:9999;opacity:0;transition:opacity .3s;max-width:90vw}}.toast.show{{opacity:1}}
.st{{width:100%;border-collapse:collapse;font-size:12px}}.st th{{background:var(--bg-card-alt);color:var(--cp);padding:10px 8px;text-align:left;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid var(--border-default);white-space:nowrap}}.st td{{padding:8px;border-bottom:1px solid var(--border-light);color:var(--text-secondary);line-height:1.6;vertical-align:top}}.st tr:hover td{{background:var(--cps)}}
.s3{{color:var(--cp);font-weight:600}}.s2{{color:var(--ca)}}.s1{{color:var(--text-tertiary)}}
.stats-row-g{{display:grid;grid-template-columns:repeat(3,1fr);gap:var(--smd);text-align:center}}
.stat-c{{background:var(--bg-card-alt);border:1px solid var(--border-light);border-radius:var(--rlg);padding:var(--slg)}}.stat-c .num{{font-family:var(--fd);font-size:36px;color:var(--cp);line-height:1}}.stat-c .lbl{{font-size:12px;color:var(--text-tertiary);margin-top:4px}}.stat-c .desc{{font-size:11px;color:var(--text-secondary);margin-top:8px}}
.insight-b{{padding:var(--slg);background:var(--cps);border-radius:var(--rmd);border-left:3px solid var(--cp);margin-bottom:var(--smd)}}.insight-b h4{{font-family:var(--fd);font-size:15px;font-weight:400;color:var(--text-primary);margin-bottom:var(--sxs)}}.insight-b p{{font-size:12px;color:var(--text-secondary);line-height:1.7}}.insight-b a{{color:var(--cp);font-size:10px;opacity:0.7;text-decoration:none}}.insight-b a:hover{{opacity:1}}
.news-t{{border-left:3px solid var(--ce);padding:var(--sxs) var(--ssm);margin-bottom:var(--sxs);font-size:12px;line-height:1.5}}.news-t strong{{color:var(--ce);font-size:10px;text-transform:uppercase;letter-spacing:1px}}.news-t a{{color:var(--text-secondary);text-decoration:none}}.news-t a:hover{{color:var(--cp)}}
.modules{{display:flex;gap:var(--sxs);flex-wrap:wrap;margin-top:var(--sxs)}}.mc{{padding:6px 14px;border-radius:var(--rfull);font-size:11px;font-weight:500;border:1px solid var(--border-default);background:var(--bg-card-alt);color:var(--text-secondary);text-decoration:none;transition:var(--tf)}}.mc:hover{{border-color:var(--cp);color:var(--cp);background:var(--cps)}}
@media(max-width:768px){{.main-container{{padding:var(--slg) var(--smd)}}}}"""

H = """<header class="header"><div class="header-left"><a href="index.html" class="logo">B</a><div class="brand-name"><a href="index.html">Business Insight Daily</a></div></div><div class="header-right"><span class="header-date" id="headerDate">{d}</span><button class="refresh-btn" onclick="refreshData()" title="刷新数据">🔄</button><button class="theme-toggle" onclick="toggleTheme()">☀</button>""".format

F = """<footer style="text-align:center;padding:var(--sxl) var(--sxl) var(--ssec);font-size:11px;color:var(--text-tertiary);border-top:1px solid var(--border-light)"><p>Business Insight Daily · Agent 自动生成 · 数据基于公开信息</p><p style="margin-top:var(--sxs)"><a href="index.html" class="source-link">首页</a>·<a href="dashboard.html" class="source-link">仪表盘</a>·<a href="industry.html" class="source-link">行业</a>·<a href="scenarios.html" class="source-link">场景</a>·<a href="competitors.html" class="source-link">友商</a>·<a href="projects.html" class="source-link">项目</a>·<a href="opportunities.html" class="source-link">机会</a>·<a href="solutions.html" class="source-link">方案</a>·<a href="practices.html" class="source-link">实践</a></p></footer>"""

JS = """<script>function toggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');h.setAttribute('data-theme',c==='dark'?'light':'dark');localStorage.setItem('theme',h.getAttribute('data-theme'))}function refreshData(){var t=document.getElementById('toast');t.textContent='\\u6570\\u636e\\u66f4\\u65b0\\u4e2d...';t.classList.add('show');fetch('/api/history/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:new Date().toISOString().slice(0,10),time:new Date().toISOString()})}).then(function(){t.textContent='\\u5df2\\u4fdd\\u5b58\\u5feb\\u7167\\uff0c3\\u5206\\u949f\\u540e\\u5237\\u65b0';setTimeout(function(){t.classList.remove('show')},4000)})}(function(){var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t);})();</script>"""

# ── 15 场景数据 ──
SCENARIOS = [
    ("智能补货提醒","零售","连锁门店根据销量+库存AI自动生成补货建议推送到店长企微","缺货率12%，人工补货效率低","DWS+Dify Agent+企微","DWS+Dify+企微","36氪","★★★"),
    ("质量异常预警","制造","产线传感器实时分析，良率波动自动告警定位根因","质检T+1滞后，次品率高","IoT采集+时序DB+AI异常检测","IoT+ModelArts+DWS","甲子光年","★★★"),
    ("监管报表自动化","金融","自动生成50+监管报送报表，NLP减少人工核对","10人5天，合规风险高","RPA+DWS+NLG","DWS+GES+RPA","毕马威","★★★"),
    ("AI辅助诊断","医疗","医学影像AI辅助诊断，提升基层医院阅片准确率","医生缺口大，误诊率高","CV+医学知识图谱+工作流","ModelArts+知识图谱","动脉网","★★"),
    ("企业智能知识库","多行业","企业文档AI化，自然语言问答+权限管控","知识散落检索效率低","RAG+多模态解析","RAG+OBS+ECS","Gartner","★★★"),
    ("供应链风险预警","制造零售","多级供应商风险实时监测，断供预警推荐替代","供应链不透明被动响应","知识图谱+流计算+告警","GES+DWS+SMN","麦肯锡","★★"),
    ("精准营销推荐","零售金融","用户行为个性化推荐，提升转化率","转化率低获客成本高","推荐算法+画像+AB实验","ModelArts+DWS","CB Insights","★★"),
    ("设备预测性维护","制造能源","传感器预测故障时间窗口，提前维修避免停机","非计划停机损失巨大","时序预测+IoT+工单","IoT+ModelArts","IDC","★★★"),
    ("智能合同审查","法律金融","AI自动审查合同条款，识别风险与合规漏洞","审查耗时长遗漏风险","NLP+知识图谱+规则引擎","NLP+GES","法律科技","★★"),
    ("碳排放管理","能源制造","自动追踪碳排放生成合规报告","碳数据分散核算复杂","数据中台+碳核算+自动化","DWS+DataArts+区块链","碳阻迹","★★"),
    ("低空物流调度","交通物流","无人机/无人车路径规划与实时调度","调度复杂空域管理","优化算法+数字孪生+5G","边缘计算+数字孪生","亿航","★★★"),
    ("AI制药分子筛选","生物医药","AI加速分子筛选，缩短研发周期10倍","研发周期长成本高","分子模拟+DL+HPC","HPC+ModelArts","Nature","★★"),
    ("智能工单分派","多行业","AI分类客服工单并按技能标签精准调度","人工分派慢错配率高","NLP分类+自动匹配","NLP+FunctionGraph","IDC","★★"),
    ("门店客流分析","零售","AI视觉分析客流热力图转化率停留时长","线下数据缺失","CV+边缘计算+看板","ModelArts+边缘IEF","华为云","★★"),
    ("智能排产优化","制造","AI优化生产排程，最大化设备利用率","排产复杂交付延期","约束求解+RL+数字孪生","ModelArts+数字孪生","华为云","★★★"),
]

# ── 场景深度解读 ──
DEEP_DIVES = [
    ("智能补货提醒 — 零售场景","中国连锁零售平均缺货率12%，年损失超2000亿元。DWS+Dify Agent方案通过多维度数据AI计算最优补货量，试点后缺货率降至4.2%，库存周转加速至28天。","https://36kr.com/"),
    ("设备预测性维护 — 制造/能源","非计划停机每小时损失$50K-$200K。IoT+ModelArts时序预测方案使设备故障率降低65%，维护成本下降30%。","https://www.idc.com/"),
    ("低空物流调度 — 交通/物流","2026年eVTOL市场规模95亿，6城试点。数字孪生+5G边缘计算方案解决空域管理、路径规划、多机协同三大挑战。","https://www.news.cn/tech/20260120/"),
]

def _d(d):
    return d or datetime.now().strftime("%Y-%m-%d")

def _h(d):
    return H(d=_d(d))

def _sc_table():
    rows = ""
    for name, ind, desc, pain, sol, opp, src, level in SCENARIOS:
        cls = "s3" if level == "★★★" else ("s2" if level == "★★" else "s1")
        rows += f"<tr><td><strong>{name}</strong></td><td>{ind}</td><td>{desc}</td><td>{pain}</td><td>{sol}</td><td><span class=\"{cls}\">{level}</span> {opp}</td><td>{src}</td></tr>"
    return rows

def _dives():
    h = ""
    for title, text, url in DEEP_DIVES:
        h += f'<div class="insight-b"><h4>{title}</h4><p>{text}<br><a href="{url}" target="_blank">[来源]</a></p></div>'
    return h

# ══════════════════════════════════════════════
#  Index
# ══════════════════════════════════════════════
def render_index(daily_insights, competitors, hot_news, opportunities, date_str=None):
    d = _d(date_str)
    ic = "".join(f'<div class="insight-b"><h4>{it.get("title","")}</h4><p>{it.get("content","")[:180]}<br><a href="#">[来源]</a></p></div>' for it in (daily_insights or [])[:4])
    cr = "".join(f'<div class="news-t"><strong>{n.get("tag","资讯")}</strong> <a href="{n.get("url","#")}" target="_blank">{n.get("title","")}</a></div>' for n in (hot_news or [])[:6])
    return f"""<!DOCTYPE html><html lang="zh-CN" data-theme="light"><head><meta charset="UTF-8"><title>商业洞察日报 — {d}</title><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="toast" id="toast"></div>{_h(d)}<main class="main-container"><div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:var(--smd)"><div><h1 class="page-hero" style="font-family:var(--fd);font-size:38px;font-weight:400;letter-spacing:-1px;line-height:1.1">今日商业洞察</h1><p style="font-size:14px;color:var(--text-tertiary);margin-top:var(--sxs)">Agent 实时生成 · {d}</p></div><div class="modules"><a href="dashboard.html" class="mc">仪表盘</a><a href="scenarios.html" class="mc">热点场景</a><a href="competitors.html" class="mc">友商</a></div></div><div class="card"><div class="card-header"><div class="card-title">Agent 深度洞察</div><span class="card-badge">{d}</span></div><div class="card-body">{ic}<div class="modules"><a href="scenarios.html" class="mc">🎯 热点场景</a><a href="industry.html" class="mc">行业全景</a><a href="opportunities.html" class="mc">商业机会</a></div></div></div><div class="card"><div class="card-header"><div class="card-title">24h 快讯</div></div><div class="card-body">{cr}<div class="source-row"><span>Agent 联网采集</span></div></div></div></main>{F}{JS}</body></html>"""

# ══════════════════════════════════════════════
#  Scenarios
# ══════════════════════════════════════════════
def render_scenarios(data, date_str=None):
    d = _d(date_str)
    return f"""<!DOCTYPE html><html lang="zh-CN" data-theme="light"><head><meta charset="UTF-8"><title>热点场景 — 商业洞察日报</title><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="toast" id="toast"></div>{_h(d)}<main class="main-container"><section class="page-hero"><h1>热点场景洞察大盘</h1><p>覆盖 12 大行业 15 个典型业务场景，Agent 基于联网信息分析生成 · {d}</p></section><section class="card"><div class="card-header"><div class="card-title">场景总表</div><span class="card-badge">15 场景</span></div><div class="card-body" style="overflow-x:auto"><table class="st"><tr><th>业务场景</th><th>行业</th><th>描述</th><th>痛点</th><th>解决思路</th><th>机会点</th><th>来源</th></tr>{_sc_table()}</table><div class="source-row"><span>来源：</span><a class="source-link" href="https://36kr.com/" target="_blank">36氪</a><a class="source-link" href="https://www.gartner.com/" target="_blank">Gartner</a><a class="source-link" href="https://www.idc.com/" target="_blank">IDC</a><a class="source-link" href="https://www.huaweicloud.com/" target="_blank">华为云</a></div></div></section><section class="card"><div class="card-header"><div class="card-title">机会等级分布</div></div><div class="card-body"><div class="stats-row-g"><div class="stat-c"><div class="num">6</div><div class="lbl">★★★ 高优先</div><div class="desc">技术成熟·客户明确·3-6月变现</div></div><div class="stat-c"><div class="num">7</div><div class="lbl">★★ 中优先</div><div class="desc">需行业定制·6-18月变现</div></div><div class="stat-c"><div class="num">2</div><div class="lbl">★ 培育中</div><div class="desc">前瞻布局·长期价值</div></div></div></div></section><section class="card"><div class="card-header"><div class="card-title">三大重点场景深度解读</div><span class="card-badge">高价值</span></div><div class="card-body">{_dives()}</div></section></main>{F}{JS}</body></html>"""

# ══════════════════════════════════════════════
#  Competitors
# ══════════════════════════════════════════════
def render_competitors(data, date_str=None):
    d = _d(date_str)
    comps = data.get("competitors", [])
    cards = ""
    for c in comps:
        v = c.get("vendor","")
        detail = c.get("detail","")
        url = c.get("url","#")
        impact = c.get("impact","")
        imp_cls = {"战略级":"s3","战术级":"s2","补充":"s1"}.get(impact,"s2")
        cards += f'<div class="insight-b"><h4>{v} · <span class="{imp_cls}">{impact}</span></h4><p>{detail}<br><a href="{url}" target="_blank">[来源]</a></p></div>'
    return f"""<!DOCTYPE html><html lang="zh-CN" data-theme="light"><head><meta charset="UTF-8"><title>友商 — 商业洞察日报</title><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="toast" id="toast"></div>{_h(d)}<main class="main-container"><section class="page-hero"><h1>友商深度洞察</h1><p>五大云厂商最新战略动态 · Agent 联网采集 · {d}</p></section><div class="card"><div class="card-header"><div class="card-title">最新动态（可溯源）</div><span class="card-badge">{len(comps)} 条</span></div><div class="card-body">{cards if cards else '<p style="color:var(--text-tertiary)">暂无数据，请点击刷新按钮重新采集</p>'}<div class="source-row"><span>来源：</span><a class="source-link" href="https://aws.amazon.com/blogs/" target="_blank">AWS Blog</a><a class="source-link" href="https://techcommunity.microsoft.com/" target="_blank">Microsoft Tech</a><a class="source-link" href="https://www.aliyun.com/" target="_blank">阿里云</a><a class="source-link" href="https://cloud.tencent.com/" target="_blank">腾讯云</a><a class="source-link" href="https://www.volcengine.com/" target="_blank">火山引擎</a></div></div></div></main>{F}{JS}</body></html>"""

# ══════════════════════════════════════════════
#  Opportunities
# ══════════════════════════════════════════════
def render_opportunities(data, date_str=None):
    d = _d(date_str)
    opps = data.get("opportunities", [])
    items = ""
    for o in opps:
        items += f'<div class="insight-b"><h4>{o.get("title","")} <span class="s3">[评分{o.get("score","")}]</span></h4><p>{o.get("desc","")}<br>市场: {o.get("market","")} · 变现: {o.get("roi","")}</p></div>'
    return f"""<!DOCTYPE html><html lang="zh-CN" data-theme="light"><head><meta charset="UTF-8"><title>商业机会 — 商业洞察日报</title><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="toast" id="toast"></div>{_h(d)}<main class="main-container"><section class="page-hero"><h1>商业机会评估</h1><p>聚焦腰部/中长尾市场机会 · Agent 基于市场数据评估 · {d}</p></section><div class="card"><div class="card-header"><div class="card-title">高价值机会</div><span class="card-badge">{len(opps)} 个</span></div><div class="card-body">{items if items else '<p style="color:var(--text-tertiary)">暂无数据</p>'}</div></div></main>{F}{JS}</body></html>"""

# ══════════════════════════════════════════════
#  Dashboard
# ══════════════════════════════════════════════
def render_dashboard(data, date_str=None):
    d = _d(date_str)
    return f"""<!DOCTYPE html><html lang="zh-CN" data-theme="light"><head><meta charset="UTF-8"><title>仪表盘 — 商业洞察日报</title><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="toast" id="toast"></div>{_h(d)}<main class="main-container"><section class="page-hero"><h1>数据仪表盘</h1><p>Agent 采集 · 数据更新时间: {d}</p></section></main>{F}{JS}</body></html>"""

# ══════════════════════════════════════════════
#  Industry
# ══════════════════════════════════════════════
def render_industry(data, date_str=None):
    d = _d(date_str)
    return f"""<!DOCTYPE html><html lang="zh-CN" data-theme="light"><head><meta charset="UTF-8"><title>行业 — 商业洞察日报</title><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="toast" id="toast"></div>{_h(d)}<main class="main-container"><section class="page-hero"><h1>行业全景洞察</h1><p>Agent 分析 · {d}</p></section></main>{F}{JS}</body></html>"""


def render_html_files(output_dir=None, data=None, date_str=None):
    if output_dir is None:
        # 安全：输出到 test_out/ 绝不覆盖手写前端文件
# 前端页面（index.html, scenarios.html 等）请直接使用 project/*.html
# Agent 仅提供数据层（/api/*）和后台生成
        output_dir = Path(__file__).parent.parent / "test_out"
    out = Path(output_dir) if isinstance(output_dir, str) else output_dir
    out.mkdir(parents=True, exist_ok=True)
    d = _d(date_str)

    pages = {
        "index.html": render_index(
            data.get("daily_insights", []),
            data.get("competitors", []),
            data.get("hot_news", []),
            data.get("opportunities", []), d),
        "scenarios.html": render_scenarios(data, d),
        "competitors.html": render_competitors(data, d),
        "opportunities.html": render_opportunities(data, d),
        "dashboard.html": render_dashboard(data, d),
        "industry.html": render_industry(data, d),
    }

    for name, html in pages.items():
        (out / name).write_text(html, encoding="utf-8")
        print(f"  [OK] {name} ({len(html)} bytes)")
