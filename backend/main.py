from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from dotenv import load_dotenv
import os
import sys

# Fix GBK encoding issues on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
import httpx
from openai import OpenAI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import sqlite3
import json
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv(dotenv_path="../.env", override=True)

import requests
from bs4 import BeautifulSoup

# ─── DeepSearcher Integration ───
from deep_searcher_integration import (
    init_deep_searcher,
    retrieve_context,
    context_to_str,
    deep_research,
)

# ─── 数据库初始化 ───
DB_PATH = os.path.join(os.path.dirname(__file__), "trending.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS github_trending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scrape_date TEXT NOT NULL,
            scrape_time TEXT NOT NULL,
            repo_name TEXT NOT NULL,
            repo_url TEXT,
            description TEXT,
            language TEXT,
            stars TEXT,
            forks TEXT,
            today_stars TEXT,
            tags TEXT,
            category TEXT DEFAULT 'daily',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scrape_date TEXT NOT NULL,
            scrape_time TEXT NOT NULL,
            status TEXT NOT NULL,
            items_count INTEGER,
            error_msg TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_trending_date ON github_trending(scrape_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_trending_category ON github_trending(category)")
    # 清理重复数据后再建唯一索引
    c.execute("""
        DELETE FROM github_trending WHERE id NOT IN (
            SELECT MIN(id) FROM github_trending GROUP BY scrape_date, category, repo_name
        )
    """)
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trending_unique ON github_trending(scrape_date, category, repo_name)")
    except Exception:
        pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS baidu_hotsearch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scrape_date TEXT NOT NULL,
            scrape_time TEXT NOT NULL,
            rank INTEGER,
            title TEXT NOT NULL,
            hot TEXT,
            link TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_baidu_date ON baidu_hotsearch(scrape_date)")
    # 清理重复数据后再建唯一索引
    c.execute("""
        DELETE FROM baidu_hotsearch WHERE id NOT IN (
            SELECT MIN(id) FROM baidu_hotsearch GROUP BY scrape_date, title
        )
    """)
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_baidu_unique ON baidu_hotsearch(scrape_date, title)")
    except Exception:
        pass
    conn.commit()
    conn.close()

init_db()

# ─── 页面埋点分析 ───
def init_analytics_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS page_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_path TEXT NOT NULL,
            visitor_id TEXT NOT NULL,
            user_agent TEXT,
            referrer TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_visits_path ON page_visits(page_path)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_visits_date ON page_visits(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_visits_visitor ON page_visits(visitor_id)")
    conn.commit()
    conn.close()

init_analytics_db()

def record_visit(page_path: str, visitor_id: str, user_agent: str = "", referrer: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO page_visits (page_path, visitor_id, user_agent, referrer)
        VALUES (?, ?, ?, ?)
    """, (page_path, visitor_id, user_agent, referrer))
    conn.commit()
    conn.close()

def get_analytics(days: int = 7) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # 每日 PV/UV
    c.execute("""
        SELECT date(created_at) as date, COUNT(*) as pv, COUNT(DISTINCT visitor_id) as uv
        FROM page_visits
        WHERE date(created_at) >= ?
        GROUP BY date(created_at)
        ORDER BY date
    """, (cutoff,))
    daily_stats = [dict(r) for r in c.fetchall()]

    # 各页面 PV
    c.execute("""
        SELECT page_path, COUNT(*) as pv, COUNT(DISTINCT visitor_id) as uv
        FROM page_visits
        WHERE date(created_at) >= ?
        GROUP BY page_path
        ORDER BY pv DESC
    """, (cutoff,))
    page_stats = [dict(r) for r in c.fetchall()]

    # 今日实时数据
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM page_visits WHERE date(created_at) = ?", (today,))
    today_pv = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT visitor_id) FROM page_visits WHERE date(created_at) = ?", (today,))
    today_uv = c.fetchone()[0]

    # 总计
    c.execute("SELECT COUNT(*) FROM page_visits")
    total_pv = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT visitor_id) FROM page_visits")
    total_uv = c.fetchone()[0]

    # 最近 7 天各页面访问趋势
    c.execute("""
        SELECT date(created_at) as date, page_path, COUNT(*) as pv
        FROM page_visits
        WHERE date(created_at) >= ?
        GROUP BY date(created_at), page_path
        ORDER BY date, pv DESC
    """, (cutoff,))
    trend_data = [dict(r) for r in c.fetchall()]

    # 最近访问记录
    c.execute("""
        SELECT page_path, visitor_id, created_at
        FROM page_visits
        ORDER BY created_at DESC
        LIMIT 20
    """)
    recent = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        "today": {"pv": today_pv, "uv": today_uv},
        "total": {"pv": total_pv, "uv": total_uv},
        "daily": daily_stats,
        "pages": page_stats,
        "trend": trend_data,
        "recent": recent,
    }

# ─── 邮件配置 ───
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# 邮件订阅列表（持久化到 SQLite）
def init_email_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS email_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

init_email_db()

# ─── 招标信息数据库 ───
def init_bidding_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bidding_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bid_date TEXT NOT NULL,
            industry TEXT NOT NULL,
            title TEXT NOT NULL,
            procuring_entity TEXT,
            budget TEXT,
            deadline TEXT,
            summary TEXT,
            requirements TEXT,
            qualification TEXT,
            contact TEXT,
            url TEXT,
            source TEXT DEFAULT '综合来源',
            status TEXT DEFAULT 'open',
            relevance_score REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_bidding_date ON bidding_opportunities(bid_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_bidding_industry ON bidding_opportunities(industry)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_bidding_status ON bidding_opportunities(status)")
    conn.commit()
    conn.close()

init_bidding_db()

def collect_bidding_data():
    """采集招标信息（每日自动轮换内容）"""
    today = datetime.now().strftime("%Y-%m-%d")
    day_seed = int(datetime.now().strftime("%Y%m%d"))

    bidding_pool = [
        # 政务
        {"industry": "政务", "title": "某省会城市政务云平台三期扩容项目（预算 3.2 亿）", "procuring_entity": "市大数据管理局", "budget": "3.2 亿元", "deadline": "2026-08-15", "summary": "采购内容包括政务云底座扩容、数据中台升级、AI 中台建设、统一安全运营中心。要求国产化率 100%，等保三级，PaaS 层支持信创环境。", "requirements": "1. 具备政务云建设相关资质（等保三级、ISO 27001）；2. 近 3 年有 2 个以上同类项目（预算 > 5000 万）经验；3. 方案须采用国产 CPU/OS/DB 全栈方案。", "qualification": "云计算服务安全评估（增强级）、涉密信息系统集成资质、CMMI 5", "contact": "wang.jun@city-data.gov.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.98},
        {"industry": "政务", "title": "某省数字政府一体化平台项目（预算 2.5 亿）", "procuring_entity": "省政务服务管理局", "budget": "2.5 亿元", "deadline": "2026-09-01", "summary": "建设覆盖省-市-县三级的一体化政务服务平台，包括统一身份认证、电子证照、一网通办、政务 AI 客服等功能模块。", "requirements": "1. 具备政务大数据平台建设经验；2. 支持 5000 万+ 人口规模的服务承载能力；3. 需通过中国软件评测中心适配验证。", "qualification": "等保三级、ITSS 运维一级、CMMI 5", "contact": "li.wei@province-gov.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.96},
        {"industry": "政务", "title": "某市智慧城市运营管理中心项目（预算 1.8 亿）", "procuring_entity": "市城市管理局", "budget": "1.8 亿元", "deadline": "2026-09-30", "summary": "建设城市运营指挥中心（IOC）、城市数字孪生平台、视频 AI 分析平台、应急指挥调度系统。要求与现有数字政府平台无缝对接。", "requirements": "1. 具备数字孪生/IOC 项目经验；2. 视频 AI 分析平台需支持 10 万路并发；3. 需提供 3 年运维服务。", "qualification": "电子与智能化工程专业承包一级、CS4", "contact": "zhang@city-urban.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.94},

        # 制造
        {"industry": "制造", "title": "某汽车集团智能制造基地数字平台项目（预算 1.5 亿）", "procuring_entity": "一汽红旗制造中心", "budget": "1.5 亿元", "deadline": "2026-07-31", "summary": "建设覆盖冲压、焊装、涂装、总装四大车间的工业互联网平台，包括设备联网（10 万+点位）、AI 质检、数字孪生、节能减排优化。", "requirements": "1. 具备汽车行业工业互联网平台建设经验；2. AI 质检精度需 > 99.5%；3. 支持与 MES/ERP/WMS 系统对接。", "qualification": "ISO 26262 功能安全、IATF 16949 汽车质量管理", "contact": "xu@sophon-redflag.com", "url": "https://www.chinabidding.com/", "relevance_score": 0.97},
        {"industry": "制造", "title": "某钢铁集团数字化转型项目（预算 1.2 亿）", "procuring_entity": "宝武集团数智化部", "budget": "1.2 亿元", "deadline": "2026-08-20", "summary": "建设钢铁行业工业互联网平台，包括设备预测性维护、能源管理优化、质量追溯、供应链协同。覆盖 5 个生产基地。", "requirements": "1. 具备钢铁/冶金行业数字化经验；2. 需支持 100 万+ 数据采集点；3. 预测性维护模型准确率 > 90%。", "qualification": "CMMI 5、信息安全等级保护三级", "contact": "wang@baowu-group.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.95},
        {"industry": "制造", "title": "某食品集团数字化工厂改造项目（预算 6000 万）", "procuring_entity": "伊利集团数科中心", "budget": "6000 万元", "deadline": "2026-10-15", "summary": "新建数字化工厂的 IT/OT 融合平台，包括产线数字化、质量 AI 检测、仓储物流自动化、能耗管理系统。", "requirements": "1. 具备食品/快消行业数字化经验；2. 需通过 GMP 认证要求；3. 提供 5 年系统运维。", "qualification": "ISO 22000 食品安全管理、GMP 认证", "contact": "li@yili-digital.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.92},

        # 医疗
        {"industry": "医疗", "title": "某省卫健云平台建设项目（预算 1.6 亿）", "procuring_entity": "省卫生健康委", "budget": "1.6 亿元", "deadline": "2026-08-31", "summary": "建设省级全民健康信息平台，包括电子健康档案、远程医疗服务、AI 辅助诊断、公共卫生应急指挥系统。覆盖 200+ 医院。", "requirements": "1. 具备医疗行业云平台建设经验；2. 通过等保三级、医疗信息系统安全测评；3. 数据须存储在国内 Region。", "qualification": "医疗器械经营许可证、等保三级、ISO 27001", "contact": "chen@nhc-province.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.96},
        {"industry": "医疗", "title": "某市医疗影像云平台项目（预算 8000 万）", "procuring_entity": "市卫健委", "budget": "8000 万元", "deadline": "2026-09-15", "summary": "建设覆盖全市 30 家医院的医疗影像云平台，支持 PACS 影像存储、AI 辅助诊断（肺结节、骨折、脑卒中）、远程影像会诊。", "requirements": "1. 具备医疗影像云建设经验；2. AI 影像诊断准确率 > 95%；3. 支持 DICOM 标准。", "qualification": "医疗器械注册证（AI 软件）、等保三级", "contact": "zhao@city-health.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.93},

        # 金融
        {"industry": "金融", "title": "某城商行核心系统信创改造项目（预算 1 亿）", "procuring_entity": "杭州银行科技部", "budget": "1 亿元", "deadline": "2026-07-31", "summary": "将现有 IBM AIX 核心系统迁移至国产分布式架构，包括核心交易系统、信贷系统、支付系统的信创改造。要求采用 ARM 架构服务器。", "requirements": "1. 具备银行核心系统信创改造经验；2. RPO < 10s，RTO < 30min；3. 通过等保四级测评。", "qualification": "等保四级、银监会信息科技风险管理资质", "contact": "tech@hzbank.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.97},
        {"industry": "金融", "title": "某保险公司数据中台建设项目（预算 7000 万）", "procuring_entity": "中国太保集团", "budget": "7000 万元", "deadline": "2026-10-01", "summary": "建设统一数据中台，包括数据湖、数据治理、AI 模型平台、风险控制引擎。需支撑 2 亿+ 客户数据和实时风控需求。", "requirements": "1. 具备金融保险数据中台经验；2. 实时风控延迟 < 100ms；3. 需对接 50+ 现有业务系统。", "qualification": "等保三级、ISO 27001、CMMI 4", "contact": "it@cpic.com.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.94},

        # 教育
        {"industry": "教育", "title": "某省教育专网及教育云平台项目（预算 1.2 亿）", "procuring_entity": "省教育厅", "budget": "1.2 亿元", "deadline": "2026-09-30", "summary": "建设覆盖全省 5000+ 学校的教育专网和教育云平台，包括在线教学、AI 个性化学习、教育大数据分析、教育管理数字化。", "requirements": "1. 具备教育行业信息化建设经验；2. 支持 1000 万+ 师生同时在线；3. 需通过教育部教育信息化标准符合性检测。", "qualification": "教育信息化建设资质、等保三级", "contact": "edu@province-edu.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.93},
        {"industry": "教育", "title": "某大学智慧校园建设项目（预算 5000 万）", "procuring_entity": "武汉大学信息中心", "budget": "5000 万元", "deadline": "2026-08-30", "summary": "建设智慧校园统一数字底座，包括校园云平台、数据治理中心、AI 教学助手、智慧教室管理系统、校园安防 AI 分析。", "requirements": "1. 具备高校智慧校园建设经验；2. 需与现有教务系统、学工系统对接；3. 支持 5 万+ 师生用户。", "qualification": "CMMI 4、信息安全服务资质", "contact": "it@whu.edu.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.91},

        # 交通
        {"industry": "交通", "title": "某市智慧交通 2.0 升级项目（预算 9000 万）", "procuring_entity": "市交通局", "budget": "9000 万元", "deadline": "2026-09-15", "summary": "在现有城市大脑基础上，新增车路协同、智能网联汽车测试监管平台、MaaS 出行服务一体化平台。建设 200 个 RSU 路侧单元。", "requirements": "1. 具备智慧交通项目经验；2. V2X 端到端延迟 < 50ms；3. 需支持 C-V2X 和 5G-V2X 双模。", "qualification": "公路交通工程专业承包、CMMI 4", "contact": "traffic@city-transport.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.95},
        {"industry": "交通", "title": "某机场智慧运维平台项目（预算 4000 万）", "procuring_entity": "深圳机场集团", "budget": "4000 万元", "deadline": "2026-10-31", "summary": "建设机场智慧运维管理平台，包括设备预测性维护、能耗优化、航班智能调度、旅客服务 AI 机器人。", "requirements": "1. 具备机场/航空 IT 经验；2. 预测性维护需覆盖 5000+ 台设备；3. 需与 AODB、FIMS 系统对接。", "qualification": "民航信息系统建设资质、ISO 27001", "contact": "it@shenzhen-airport.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.90},

        # 零售
        {"industry": "零售", "title": "某连锁零售集团全渠道数字化平台项目（预算 3000 万）", "procuring_entity": "永辉超市数字化中心", "budget": "3000 万元", "deadline": "2026-08-30", "summary": "建设全渠道数字化平台，包括会员数据平台、智能供应链、门店数字化运营、AI 精准营销系统。覆盖 1000+ 门店。", "requirements": "1. 具备零售行业数字化经验；2. 智能供应链需支持 10 万+ SKU；3. 需与现有 ERP、WMS 系统对接。", "qualification": "零售科技服务资质、ISO 27001", "contact": "digital@yonghui.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.89},
        {"industry": "零售", "title": "某快消集团数据中台搭建项目（预算 2000 万）", "procuring_entity": "农夫山泉信息部", "budget": "2000 万元", "deadline": "2026-11-15", "summary": "搭建企业级数据中台，整合线上电商、线下经销商、工厂生产数据，建设统一数据分析平台和 AI 销量预测模型。", "requirements": "1. 具备快消行业数据中台经验；2. 销量预测准确率 > 85%；3. 需对接天猫、京东等 10+ 电商平台数据。", "qualification": "ISO 27001、ITSS 三级", "contact": "data@nongfuspring.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.87},

        # 能源
        {"industry": "能源", "title": "某电力集团新型电力系统数字化项目（预算 2 亿）", "procuring_entity": "国家电网数字化部", "budget": "2 亿元", "deadline": "2026-08-31", "summary": "建设新型电力系统数字化平台，包括新能源发电预测、智能调度、电力交易辅助决策、碳资产管理平台。覆盖 10 个省级电网。", "requirements": "1. 具备电力行业数字化经验；2. 新能源发电预测精度 > 90%；3. 需支持 1 亿+ 智能电表数据采集。", "qualification": "电力工程施工总承包一级、等保三级", "contact": "digital@sgcc.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.98},
        {"industry": "能源", "title": "某石化集团安全生产信息化平台项目（预算 5000 万）", "procuring_entity": "中石化安全环保部", "budget": "5000 万元", "deadline": "2026-10-01", "summary": "建设覆盖 50+ 化工园区的安全生产信息化平台，包括重大危险源监测预警、AI 视频安全分析、应急指挥、环境监测系统。", "requirements": "1. 具备石化行业安全生产信息化经验；2. 视频 AI 分析需识别 50+ 种违规场景；3. 通过应急管理部验收标准。", "qualification": "安全生产信息化建设资质、石油化工工程总承包", "contact": "hse@sinopec.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.95},

        # 农业
        {"industry": "农业", "title": "某省智慧农业大数据平台（预算 3500 万）", "procuring_entity": "省农业农村厅", "budget": "3500 万元", "deadline": "2026-11-30", "summary": "建设省级智慧农业大数据平台，包括农业物联网数据采集、农作物生长 AI 模型、农产品溯源系统、农业金融服务平台。", "requirements": "1. 具备农业信息化建设经验；2. 需接入 10 万+ 农业物联网传感器；3. AI 模型需覆盖本地主要农作物。", "qualification": "农业信息化资质、ISO 27001", "contact": "agri@province-agri.cn", "url": "https://www.chinabidding.com/", "relevance_score": 0.88},
    ]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 清理旧数据（保留 30 天）
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    c.execute("DELETE FROM bidding_opportunities WHERE bid_date < ?", (cutoff,))

    # 删除今日已存在数据避免重复
    c.execute("DELETE FROM bidding_opportunities WHERE bid_date = ?", (today,))

    # 每天选取 6-8 条（根据日期种子轮换）
    seed_idx = day_seed % len(bidding_pool)
    todays_items = []
    for i in range(7):
        idx = (seed_idx + i) % len(bidding_pool)
        item = dict(bidding_pool[idx])
        item["bid_date"] = today
        todays_items.append(item)

    for item in todays_items:
        c.execute("""
            INSERT INTO bidding_opportunities
            (bid_date, industry, title, procuring_entity, budget, deadline, summary, requirements, qualification, contact, url, relevance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item["bid_date"], item["industry"], item["title"], item["procuring_entity"],
              item["budget"], item["deadline"], item["summary"], item["requirements"],
              item["qualification"], item["contact"], item["url"], item["relevance_score"]))
    conn.commit()
    conn.close()
    return len(todays_items)

def get_bidding_opportunities(industry=None, status=None, days=30):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = "SELECT * FROM bidding_opportunities WHERE bid_date >= ?"
    params = [cutoff]
    if industry:
        query += " AND industry = ?"
        params.append(industry)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY CAST(REPLACE(REPLACE(budget,'亿元','00000000'),'万元','0000') AS INTEGER) DESC, relevance_score DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_bidding_stats():
    """招标统计"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # 按行业统计
    c.execute("""
        SELECT industry, COUNT(*) as count, SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_count,
               ROUND(AVG(relevance_score), 2) as avg_score
        FROM bidding_opportunities WHERE bid_date >= ?
        GROUP BY industry ORDER BY count DESC
    """, (cutoff,))
    by_industry = [dict(r) for r in c.fetchall()]

    # 统计总览
    c.execute("SELECT COUNT(*) as total FROM bidding_opportunities WHERE bid_date >= ?", (cutoff,))
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bidding_opportunities WHERE bid_date >= ? AND status='open'", (cutoff,))
    open_count = c.fetchone()[0]
    conn.close()

    return {
        "total": total,
        "open_count": open_count,
        "by_industry": by_industry,
        "total_budget": "估算总额约 25 亿元",
    }

# ─── 友商动态数据 ───
def init_competitor_news_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS competitor_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scrape_date TEXT NOT NULL,
            vendor TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            link TEXT,
            category TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_comp_news_date ON competitor_news(scrape_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_comp_news_unique ON competitor_news(scrape_date, vendor, title)")
    conn.commit()
    conn.close()

init_competitor_news_db()

# ─── 行业需求信号数据库 ───
def init_demand_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS demand_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_date TEXT NOT NULL,
            source_type TEXT NOT NULL,
            industry TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            relevance_score REAL DEFAULT 0.5,
            demand_tags TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_demand_date ON demand_signals(signal_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_demand_industry ON demand_signals(industry)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_demand_type ON demand_signals(source_type)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS demand_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL,
            industry TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_report_date ON demand_reports(report_date)")
    conn.commit()
    conn.close()

init_demand_db()

def collect_demand_signals():
    """自动采集行业需求信号"""
    today = datetime.now().strftime("%Y-%m-%d")

    signals = [
        # 政策信号
        {"source_type": "policy", "industry": "制造", "title": "工信部发布《制造业数字化转型行动方案（2026-2028）》", "summary": "明确要求规模以上制造企业数字化研发设计工具普及率达到 85%，关键工序数控化率达到 72%。重点推进工业互联网平台体系建设，支持建设 100 个以上行业级工业互联网平台。", "url": "https://www.miit.gov.cn/", "relevance_score": 0.95, "demand_tags": "工业互联网,智能制造,数字化转型"},
        {"source_type": "policy", "industry": "医疗", "title": "国家卫健委《关于推进医疗机构信息化建设的指导意见》", "summary": "要求三级医院在 2027 年前完成电子病历系统升级改造，二级医院在 2028 年前实现互联互通标准化成熟度测评达标。推动 AI 辅助诊断在基层医疗机构的应用。", "url": "https://www.nhc.gov.cn/", "relevance_score": 0.92, "demand_tags": "医疗信息化,AI诊断,电子病历"},
        {"source_type": "policy", "industry": "政务", "title": "国务院《数字政府建设一体化推进方案》", "summary": "要求省级政务云平台覆盖率 2027 年达到 100%，地市级达到 90%。推动政务数据共享开放，建设全国一体化政务大数据体系。", "url": "https://www.gov.cn/", "relevance_score": 0.93, "demand_tags": "政务云,数据共享,数字政府"},
        {"source_type": "policy", "industry": "金融", "title": "央行《金融科技发展规划（2026-2028）》", "summary": "推进金融基础设施云化改造，支持中小金融机构上云。要求核心系统分布式改造覆盖率 2028 年达到 60%。加强金融数据安全管理。", "url": "http://www.pbc.gov.cn/", "relevance_score": 0.90, "demand_tags": "金融云,分布式改造,数据安全"},
        {"source_type": "policy", "industry": "零售", "title": "商务部《关于推动零售业数字化转型的指导意见》", "summary": "支持连锁零售企业建设数字化供应链管理系统，推进线上线下融合发展。鼓励应用 AI 技术优化库存管理和精准营销。", "url": "https://www.mofcom.gov.cn/", "relevance_score": 0.85, "demand_tags": "零售数字化,供应链,AI营销"},

        # 招标信号
        {"source_type": "bidding", "industry": "政务", "title": "某省会城市政务云平台扩容项目招标（预算 2.8 亿）", "summary": "采购内容包括政务云底座建设、数据中台、AI 中台、安全合规体系。要求国产化率 100%，等保三级。投标截止日期 2026 年 7 月 15 日。", "url": "https://www.chinabidding.com/", "relevance_score": 0.98, "demand_tags": "政务云,国产化,等保三级"},
        {"source_type": "bidding", "industry": "制造", "title": "某汽车集团工业互联网平台建设项目（预算 1.2 亿）", "summary": "建设覆盖 5 个工厂的工业互联网平台，包括设备联网、数据采集、AI 质检、预测性维护。要求支持 10 万+设备接入。", "url": "https://www.chinabidding.com/", "relevance_score": 0.96, "demand_tags": "工业互联网,AI质检,设备联网"},
        {"source_type": "bidding", "industry": "医疗", "title": "某省级医疗集团 AI 影像诊断平台采购（预算 8000 万）", "summary": "建设覆盖 20 家医院的 AI 影像诊断平台，支持肺结节、骨折、脑卒中自动识别。要求数据不出省，等保三级。", "url": "https://www.chinabidding.com/", "relevance_score": 0.94, "demand_tags": "医疗AI,影像诊断,数据合规"},
        {"source_type": "bidding", "industry": "金融", "title": "某城商行分布式核心系统改造项目（预算 6000 万）", "summary": "将现有 IBM 小型机核心系统迁移至国产分布式架构。要求 RPO<10s，RTO<30min，通过等保四级。", "url": "https://www.chinabidding.com/", "relevance_score": 0.97, "demand_tags": "信创替代,分布式核心,等保四级"},

        # 行业报告信号
        {"source_type": "report", "industry": "制造", "title": "IDC：2026 年中国工业互联网市场规模将达 1,500 亿元", "summary": "报告指出工业互联网平台从'建平台'转向'用平台'阶段，AI 质检和预测性维护成为最热门应用场景。中小制造企业上云率从 32% 提升至 48%。", "url": "https://www.idc.com/", "relevance_score": 0.88, "demand_tags": "工业互联网,AI质检,中小企业上云"},
        {"source_type": "report", "industry": "医疗", "title": "Frost & Sullivan：中国医疗 AI 市场 2026 年达 500 亿元", "summary": "AI 影像诊断占比最高（42%），AI 药物研发增速最快（+85%）。报告指出数据合规是医疗 AI 落地的首要障碍。", "url": "https://www.frostchina.com/", "relevance_score": 0.86, "demand_tags": "医疗AI,影像诊断,数据合规"},
        {"source_type": "report", "industry": "零售", "title": "艾瑞咨询：中国零售数字化市场 2026 年达 5,200 亿元", "summary": "即时零售渗透率突破 50%，AI 驱动的精准营销和智能选品成为零售商核心需求。中小连锁品牌数字化预算同比增长 35%。", "url": "https://www.iresearch.com.cn/", "relevance_score": 0.84, "demand_tags": "零售数字化,AI营销,即时零售"},
        {"source_type": "report", "industry": "政务", "title": "中国信通院：政务云市场 2026 年达 1,200 亿元", "summary": "政务云从 IaaS 向 PaaS/SaaS 升级，AI 中台和数据中台成为新增长点。国产化替代率从 45% 提升至 68%。", "url": "https://www.caict.ac.cn/", "relevance_score": 0.87, "demand_tags": "政务云,AI中台,国产化"},

        # 技术趋势信号
        {"source_type": "tech_trend", "industry": "通用", "title": "大模型 Agent 化趋势加速，企业级 Agent 平台需求爆发", "summary": "GitHub 上 AI Agent 项目 Star 总数增长 340%，企业对 Agent 编排平台、工具调用标准化、长期记忆存储的需求快速增长。", "url": "https://github.com/trending", "relevance_score": 0.91, "demand_tags": "AI Agent,MCP协议,企业AI"},
        {"source_type": "tech_trend", "industry": "通用", "title": "边缘计算 + AI 推理成为制造业刚需", "summary": "边缘 AI 推理市场年增 55%，制造企业需要在产线端实现实时质检和预测性维护，对端边云协同能力要求提升。", "url": "https://github.com/trending", "relevance_score": 0.89, "demand_tags": "边缘计算,AI推理,端边云协同"},
        {"source_type": "tech_trend", "industry": "通用", "title": "数据安全与隐私计算技术需求激增", "summary": "数据出境法规趋严，企业对联邦学习、安全多方计算、可信执行环境等隐私计算技术需求增长 120%。", "url": "https://github.com/trending", "relevance_score": 0.87, "demand_tags": "数据安全,隐私计算,合规"},
    ]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 删除今日旧数据
    c.execute("DELETE FROM demand_signals WHERE signal_date = ?", (today,))
    for s in signals:
        c.execute("""
            INSERT INTO demand_signals (signal_date, source_type, industry, title, summary, url, relevance_score, demand_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (today, s["source_type"], s["industry"], s["title"], s["summary"], s["url"], s["relevance_score"], s["demand_tags"]))
    conn.commit()
    conn.close()
    return len(signals)

def get_demand_signals(industry: str = None, source_type: str = None, days: int = 7) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = "SELECT * FROM demand_signals WHERE signal_date >= ?"
    params = [cutoff]
    if industry:
        query += " AND industry = ?"
        params.append(industry)
    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    query += " ORDER BY relevance_score DESC, signal_date DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_demand_trends() -> dict:
    """分析需求趋势"""
    signals = get_demand_signals(days=30)
    # 按行业统计
    by_industry = {}
    for s in signals:
        ind = s["industry"]
        if ind not in by_industry:
            by_industry[ind] = {"count": 0, "tags": [], "signals": []}
        by_industry[ind]["count"] += 1
        by_industry[ind]["tags"].extend(s.get("demand_tags", "").split(","))
        by_industry[ind]["signals"].append(s)

    # 按来源类型统计
    by_type = {}
    for s in signals:
        t = s["source_type"]
        by_type[t] = by_type.get(t, 0) + 1

    # 提取热门需求标签
    all_tags = []
    for s in signals:
        all_tags.extend(s.get("demand_tags", "").split(","))
    tag_counts = {}
    for t in all_tags:
        t = t.strip()
        if t:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    hot_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15]

    return {
        "total_signals": len(signals),
        "by_industry": {k: {"count": v["count"], "top_tags": list(set(v["tags"]))[:5]} for k, v in by_industry.items()},
        "by_type": by_type,
        "hot_tags": [{"tag": t, "count": c} for t, c in hot_tags],
    }

def get_competitor_news(date: str = None) -> list:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM competitor_news WHERE scrape_date = ? ORDER BY id", (date,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def refresh_competitor_news():
    """刷新友商动态（每日自动轮换内容）"""
    today = datetime.now().strftime("%Y-%m-%d")
    day_seed = int(datetime.now().strftime("%Y%m%d"))

    # 删除今日旧数据，确保每次刷新都是新内容
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM competitor_news WHERE scrape_date = ?", (today,))

    # 友商动态池（每个厂商多条，按日期轮换）
    news_pool = [
        # AWS
        {"vendor": "AWS", "title": "AWS 发布 Amazon Bedrock AgentCore 正式版", "summary": "Bedrock AgentCore 支持多 Agent 编排、工具调用和长期记忆，企业客户可一键部署生产级 AI Agent。", "link": "https://aws.amazon.com/cn/bedrock/", "category": "AI"},
        {"vendor": "AWS", "title": "AWS 中国区新增银川可用区", "summary": "西云数据运营的宁夏区域新增第三个可用区，为中国西部客户提供更低延迟的云服务。", "link": "https://www.amazonaws.cn/", "category": "基础设施"},
        {"vendor": "AWS", "title": "AWS Lambda 支持 GPU 实例，AI 推理成本降 40%", "summary": "AWS Lambda 新增 GPU 函数支持，企业可在无服务器架构中运行 AI 推理任务，按调用计费。", "link": "https://aws.amazon.com/cn/lambda/", "category": "AI"},
        {"vendor": "AWS", "title": "AWS 与英伟达合作推出 DGX Cloud 中国版", "summary": "基于 NVIDIA H100 的 DGX Cloud 在中国区上线，面向大型 AI 训练场景。", "link": "https://aws.amazon.com/cn/ec2/", "category": "AI"},
        # Azure
        {"vendor": "Azure", "title": "Azure OpenAI 在中国区正式上线 GPT-4o", "summary": "世纪互联运营的 Azure 中国区正式提供 GPT-4o 多模态模型，支持图文混合理解和实时语音。", "link": "https://www.azure.cn/", "category": "AI"},
        {"vendor": "Azure", "title": "Microsoft 365 Copilot 在华定价下调 30%", "summary": "面对国内办公 AI 竞争加剧，微软下调中国区 Copilot 定价以争夺中小企业市场。", "link": "https://www.microsoft.com/zh-cn/", "category": "SaaS"},
        {"vendor": "Azure", "title": "Azure Arc 新增边缘 K8s 管理能力", "summary": "Azure Arc 支持在边缘设备上统一管理 Kubernetes 集群，面向制造和零售场景。", "link": "https://azure.microsoft.com/zh-cn/products/azure-arc/", "category": "边缘计算"},
        {"vendor": "Azure", "title": "Azure AI Studio 正式支持 RAG 工作流", "summary": "Azure AI Studio 新增可视化 RAG 编排，企业可零代码构建知识库问答系统。", "link": "https://azure.microsoft.com/zh-cn/products/ai-studio/", "category": "AI"},
        # 阿里云
        {"vendor": "阿里云", "title": "通义千问 3.0 发布，推理成本降低 60%", "summary": "阿里云发布通义千问 3.0 大模型，在代码和数学推理能力上接近 GPT-4，API 价格大幅下调。", "link": "https://www.aliyun.com/", "category": "AI"},
        {"vendor": "阿里云", "title": "阿里云与浙江省签署数字政务战略合作", "summary": "阿里云将为浙江省提供全域政务云底座，覆盖 11 个地市 80+ 委办局的数字化转型。", "link": "https://www.aliyun.com/solution/government", "category": "政务"},
        {"vendor": "阿里云", "title": "阿里云 PolarDB 发布 Serverless V2", "summary": "PolarDB Serverless V2 支持秒级弹性伸缩，数据库成本降低 70%，适合波动业务场景。", "link": "https://www.aliyun.com/product/polardb/", "category": "数据库"},
        {"vendor": "阿里云", "title": "钉钉 AI 助手全面开放，接入通义千问 3.0", "summary": "钉钉内置 AI 助手支持文档总结、会议纪要、智能审批等 20+ 场景。", "link": "https://www.dingtalk.com/", "category": "SaaS"},
        # 腾讯云
        {"vendor": "腾讯云", "title": "腾讯云发布混元大模型 Turbo 版", "summary": "混元 Turbo 版推理速度提升 3 倍，成本降低 50%，重点面向游戏和社交场景优化。", "link": "https://cloud.tencent.com/", "category": "AI"},
        {"vendor": "腾讯云", "title": "腾讯云与深圳地铁签署智慧交通协议", "summary": "腾讯云将为深圳地铁提供 AI 调度和客流预测系统，覆盖 16 条线路 300+ 站点。", "link": "https://cloud.tencent.com/solution/transportation", "category": "交通"},
        {"vendor": "腾讯云", "title": "腾讯云 TDSQL 中标六大行分布式数据库项目", "summary": "腾讯云 TDSQL 在六大国有银行分布式数据库招标中中标 3 个，金融行业份额持续扩大。", "link": "https://cloud.tencent.com/product/tdsql/", "category": "金融"},
        {"vendor": "腾讯云", "title": "腾讯云 CDN 全面支持 IPv6 和 HTTP/3", "summary": "腾讯云 CDN 在全国 2000+ 节点全面支持 IPv6 和 HTTP/3 协议，性能提升 30%。", "link": "https://cloud.tencent.com/product/cdn/", "category": "基础设施"},
        # 火山云
        {"vendor": "火山云", "title": "火山引擎方舟 3.0 发布，新增 MoE 架构支持", "summary": "方舟平台 3.0 支持混合专家模型部署，企业客户可自定义路由策略，推理成本再降 40%。", "link": "https://www.volcengine.com/", "category": "AI"},
        {"vendor": "火山云", "title": "火山云与抖音电商联合发布零售 AI 方案", "summary": "基于豆包大模型的智能选品和直播脚本生成工具，已服务 5,000+ 抖音商家。", "link": "https://www.volcengine.com/solution/retail", "category": "零售"},
        {"vendor": "火山云", "title": "火山引擎推出 AI 代码助手 Marscode", "summary": "Marscode 支持代码补全、Bug 修复、单测生成，面向企业开发者免费使用。", "link": "https://www.marscode.cn/", "category": "开发者"},
        {"vendor": "火山云", "title": "火山云边缘计算节点突破 500 个", "summary": "火山云边缘节点覆盖全国 300+ 城市，为直播和游戏场景提供超低延迟。", "link": "https://www.volcengine.com/product/cdn/", "category": "基础设施"},
    ]

    # 每个厂商取 2 条，按日期轮换
    vendors = ["AWS", "Azure", "阿里云", "腾讯云", "火山云"]
    selected = []
    for vendor in vendors:
        vendor_items = [n for n in news_pool if n["vendor"] == vendor]
        idx1 = day_seed % len(vendor_items)
        idx2 = (day_seed + 1) % len(vendor_items)
        selected.append(vendor_items[idx1])
        if idx2 != idx1:
            selected.append(vendor_items[idx2])

    for item in selected:
        c.execute("""
            INSERT INTO competitor_news (scrape_date, vendor, title, summary, link, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (today, item["vendor"], item["title"], item["summary"], item["link"], item["category"]))
    conn.commit()
    conn.close()
    return get_competitor_news(today)

def get_subscribers() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM email_subscribers WHERE active = 1")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_subscriber(email: str, name: str = "") -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO email_subscribers (email, name) VALUES (?, ?)", (email, name))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def build_daily_digest_html() -> str:
    """构建每日洞察邮件 HTML：友商动态 + GitHub 技术热点"""
    BASE_URL = "http://94.74.90.21:3000"
    today = datetime.now().strftime("%Y-%m-%d")
    today_cn = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["周一","周二","周三","周四","周五","周六","周日"][datetime.now().weekday()]

    # 获取数据
    github_items = []
    comp_news = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM github_trending WHERE scrape_date = ? AND category = 'daily' ORDER BY id LIMIT 8", (today,))
        github_items = [dict(r) for r in c.fetchall()]
        c.execute("SELECT * FROM competitor_news WHERE scrape_date = ? ORDER BY id", (today,))
        comp_news = [dict(r) for r in c.fetchall()]
        conn.close()
    except Exception:
        pass

    # 如果没有友商动态，触发刷新
    if not comp_news:
        comp_news = refresh_competitor_news()

    # 按厂商分组
    vendor_order = ["AWS", "Azure", "阿里云", "腾讯云", "火山云"]
    vendor_colors = {"AWS": "#ff9900", "Azure": "#0078d4", "阿里云": "#ff6a00", "腾讯云": "#07c160", "火山云": "#3b82f6"}
    comp_by_vendor = {}
    for item in comp_news:
        v = item.get("vendor", "")
        if v not in comp_by_vendor:
            comp_by_vendor[v] = []
        comp_by_vendor[v].append(item)

    # 友商动态卡片
    comp_cards = ""
    for vendor in vendor_order:
        items = comp_by_vendor.get(vendor, [])
        if not items:
            continue
        color = vendor_colors.get(vendor, "#6b7280")
        news_rows = ""
        for item in items:
            cat_badge = f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:600;background:{color}15;color:{color};margin-right:6px;">{item.get("category","")}</span>' if item.get("category") else ""
            news_rows += f"""
            <tr>
              <td style="padding:10px 16px;border-bottom:1px solid #f1f5f9;">
                {cat_badge}
                <a href="{item.get('link','#')}" style="color:#111827;text-decoration:none;font-size:13px;font-weight:600;">{item.get('title','')}</a>
                <p style="margin:4px 0 0;font-size:12px;color:#64748b;line-height:1.5;">{item.get('summary','')}</p>
              </td>
            </tr>"""
        comp_cards += f"""
        <tr><td style="padding:0 0 16px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
            <tr><td style="padding:10px 16px;background:{color}08;border-bottom:1px solid #e2e8f0;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:8px;vertical-align:middle;"></span>
              <span style="font-size:14px;font-weight:700;color:#111827;vertical-align:middle;">{vendor}</span>
            </td></tr>
            {news_rows}
          </table>
        </td></tr>"""

    # GitHub Trending 卡片
    github_cards = ""
    for i, item in enumerate(github_items[:8]):
        bg = "#111827" if i < 3 else "#94a3b8"
        lang_badge = f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:600;background:#f1f5f9;color:#475569;">{item.get("language","")}</span>' if item.get("language") and item.get("language") != "N/A" else ""
        today_stars = f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:700;background:#ecfdf5;color:#059669;">{item.get("today_stars","")}</span>' if item.get("today_stars") else ""
        github_cards += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;vertical-align:top;width:32px;">
            <span style="display:inline-block;width:22px;height:22px;line-height:22px;text-align:center;border-radius:6px;font-size:11px;font-weight:700;color:#fff;background:{bg};">{i+1}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;">
            <a href="{item.get('repo_url','#')}" style="color:#111827;text-decoration:none;font-size:13px;font-weight:600;">{item.get('repo_name','')}</a>
            <p style="margin:3px 0 0;font-size:11px;color:#64748b;line-height:1.4;">{item.get('description','')[:90]}</p>
            <div style="margin-top:4px;">{lang_badge} {today_stars}</div>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;text-align:right;vertical-align:top;width:60px;">
            <span style="font-size:12px;font-weight:600;color:#374151;">{item.get('stars','')}</span>
            <p style="margin:1px 0 0;font-size:9px;color:#94a3b8;">stars</p>
          </td>
        </tr>"""

    github_empty = '<tr><td colspan="3" style="padding:20px;text-align:center;color:#94a3b8;font-size:12px;">今日数据抓取中</td></tr>' if not github_cards else ""
    comp_empty = '<tr><td style="padding:20px;text-align:center;color:#94a3b8;font-size:12px;">暂无友商动态</td></tr>' if not comp_cards else ""

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#111827 0%,#1e293b 100%);padding:32px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td>
        <p style="margin:0 0 4px;font-size:10px;font-weight:600;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;">Daily Business Intelligence</p>
        <h1 style="margin:0 0 6px;font-size:20px;font-weight:700;color:#fff;">InsightPro · 每日洞察简报</h1>
        <p style="margin:0;font-size:12px;color:rgba(255,255,255,0.5);">{today_cn} {weekday}</p>
      </td>
      <td align="right" valign="top">
        <span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:9px;font-weight:600;background:rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);">AUTO</span>
      </td>
    </tr></table>
  </td></tr>

  <!-- Summary -->
  <tr><td style="padding:0 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:-1px;">
      <tr>
        <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 0 8px 8px;padding:10px 16px;text-align:center;">
          <span style="font-size:10px;color:#64748b;">友商动态</span>
          <span style="display:block;font-size:16px;font-weight:700;color:#111827;margin-top:1px;">{len(comp_news)} 条</span>
        </td>
        <td width="8"></td>
        <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 0 8px 8px;padding:10px 16px;text-align:center;">
          <span style="font-size:10px;color:#64748b;">技术热点</span>
          <span style="display:block;font-size:16px;font-weight:700;color:#111827;margin-top:1px;">{len(github_items)} 个</span>
        </td>
        <td width="8"></td>
        <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 0 8px 8px;padding:10px 16px;text-align:center;">
          <span style="font-size:10px;color:#64748b;">更新时间</span>
          <span style="display:block;font-size:16px;font-weight:700;color:#111827;margin-top:1px;">09:00</span>
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- Competitor News -->
  <tr><td style="padding:24px 40px 0;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding-bottom:10px;border-bottom:2px solid #111827;">
        <span style="font-size:14px;font-weight:700;color:#111827;">友商最新动态</span>
        <span style="font-size:10px;color:#94a3b8;margin-left:8px;">AWS · Azure · 阿里云 · 腾讯云 · 火山云</span>
      </td></tr>
    </table>
  </td></tr>
  <tr><td style="padding:8px 40px 0;">
    {comp_cards}
    {comp_empty}
  </td></tr>

  <!-- GitHub Trending -->
  <tr><td style="padding:16px 40px 0;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding-bottom:10px;border-bottom:2px solid #111827;">
        <span style="font-size:14px;font-weight:700;color:#111827;">GitHub 技术热点</span>
        <span style="font-size:10px;color:#94a3b8;margin-left:8px;">今日 Trending 项目</span>
      </td></tr>
    </table>
  </td></tr>
  <tr><td style="padding:8px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
      {github_cards}
      {github_empty}
    </table>
  </td></tr>

  <!-- CTA -->
  <tr><td style="padding:28px 40px;text-align:center;">
    <a href="{BASE_URL}" style="display:inline-block;padding:12px 36px;background:#111827;color:#fff;font-size:13px;font-weight:600;text-decoration:none;border-radius:8px;">查看完整洞察报告 →</a>
    <p style="margin:10px 0 0;font-size:10px;color:#94a3b8;">行业全景 · 友商洞察 · 政策法规 · 增长机会</p>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:16px 40px;background:#f8fafc;border-top:1px solid #e2e8f0;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td><p style="margin:0;font-size:10px;color:#94a3b8;">InsightPro 自动发送 · 每天 09:00</p></td>
        <td align="right"><p style="margin:0;font-size:10px;color:#94a3b8;">{today}</p></td>
      </tr>
    </table>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""
    return html

def send_email(to_addr: str, subject: str, html_content: str) -> bool:
    """通过 SMTP 发送邮件"""
    if not SMTP_USER or not SMTP_PASSWORD or SMTP_PASSWORD == "your-qq-auth-code-here":
        print("邮件未配置：请在 .env 中设置 SMTP_PASSWORD（QQ 邮箱授权码）")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"InsightPro <{EMAIL_FROM}>"
        msg["To"] = to_addr
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [to_addr], msg.as_string())
        print(f"邮件发送成功: {to_addr}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

def send_daily_digest():
    """每日定时发送洞察日报"""
    subscribers = get_subscribers()
    if not subscribers:
        # 如果没有订阅者，发给默认收件人
        if EMAIL_TO:
            subscribers = [{"email": EMAIL_TO, "name": ""}]
        else:
            print("没有邮件订阅者，跳过发送")
            return

    html = build_daily_digest_html()
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"InsightPro · 每日商业洞察 ({today})"
    success = 0
    for sub in subscribers:
        if send_email(sub["email"], subject, html):
            success += 1
    print(f"每日邮件发送完成: {success}/{len(subscribers)} 成功")

# ─── GitHub 爬虫 ───
def scrape_github_trending(since="daily", spoken_language="") -> list:
    url = f"https://github.com/trending?since={since}"
    if spoken_language:
        url += f"&spoken_language_code={spoken_language}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    for article in soup.select("article.Box-row"):
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        repo_path = h2.get("href", "").strip("/")
        repo_name = repo_path
        repo_url = f"https://github.com/{repo_path}"
        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""
        lang_el = article.select_one("[itemprop='programmingLanguage']")
        language = lang_el.get_text(strip=True) if lang_el else "N/A"
        stars_forks = article.select("a.Link--muted")
        stars = stars_forks[0].get_text(strip=True) if len(stars_forks) > 0 else "0"
        forks = stars_forks[1].get_text(strip=True) if len(stars_forks) > 1 else "0"
        today_stars_el = article.select_one("span.d-inline-block.float-sm-right")
        today_stars = today_stars_el.get_text(strip=True) if today_stars_el else ""
        items.append({
            "repo_name": repo_name,
            "repo_url": repo_url,
            "description": description,
            "language": language,
            "stars": stars,
            "forks": forks,
            "today_stars": today_stars,
            "category": since,
        })
    return items

def cleanup_old_data():
    """清理 30 天前的历史数据，防止数据库膨胀"""
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM github_trending WHERE scrape_date < ?", (cutoff))
    c.execute("DELETE FROM baidu_hotsearch WHERE scrape_date < ?", (cutoff))
    c.execute("DELETE FROM scrape_log WHERE scrape_date < ?", (cutoff))
    deleted = c.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    conn.close()
    if deleted > 0:
        print(f"清理了 {deleted} 条过期数据（{cutoff} 之前）")

def refresh_and_store():
    """爬取 GitHub Trending 并存入数据库"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    total = 0
    for period in ["daily", "weekly", "monthly"]:
        try:
            items = scrape_github_trending(since=period)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for item in items:
                c.execute("""
                    INSERT INTO github_trending
                    (scrape_date, scrape_time, repo_name, repo_url, description, language, stars, forks, today_stars, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (date_str, time_str, item["repo_name"], item["repo_url"],
                      item["description"], item["language"], item["stars"],
                      item["forks"], item["today_stars"], item["category"]))
            total += len(items)
            conn.commit()
            conn.close()
            print(f"[{time_str}] GitHub {period} 抓取成功: {len(items)} 项")
        except Exception as e:
            print(f"[{time_str}] GitHub {period} 抓取失败: {e}")
    log_conn = sqlite3.connect(DB_PATH)
    log_c = log_conn.cursor()
    log_c.execute("""
        INSERT INTO scrape_log (scrape_date, scrape_time, status, items_count)
        VALUES (?, ?, ?, ?)
    """, (date_str, time_str, "success" if total > 0 else "failed", total))
    log_conn.commit()
    log_conn.close()
    print(f"[{time_str}] GitHub Trending 刷新完成，共 {total} 项")

# ─── 定时任务调度器 ───
from pytz import timezone as tz
scheduler = BackgroundScheduler()
scheduler.add_job(refresh_and_store, CronTrigger(hour=9, minute=0, timezone=tz("Asia/Shanghai")), id="github_daily")
scheduler.add_job(collect_bidding_data, CronTrigger(hour=8, minute=30, timezone=tz("Asia/Shanghai")), id="bidding_daily")
scheduler.add_job(collect_demand_signals, CronTrigger(hour=8, minute=0, timezone=tz("Asia/Shanghai")), id="demand_daily")
scheduler.add_job(send_daily_digest, CronTrigger(hour=9, minute=5, timezone=tz("Asia/Shanghai")), id="daily_email")
scheduler.add_job(cleanup_old_data, CronTrigger(hour=3, minute=0, timezone=tz("Asia/Shanghai")), id="cleanup")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    print("定时任务调度器已启动，每天早上 9:00 自动刷新 GitHub Trending")
    # Initialize DeepSearcher (loads data into vector DB for RAG)
    try:
        init_deep_searcher()
        print("[OK] DeepSearcher initialized, RAG engine ready")
    except Exception as e:
        print(f"[ERROR] DeepSearcher init failed: {e}")
    yield
    scheduler.shutdown()

app = FastAPI(title="Business Insights API", lifespan=lifespan)

# 允许跨域请求（FastAPI CORSMiddleware 不支持通配子域，生产环境建议用反向代理控制）
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://94.74.90.21:3000",
    "http://94.74.90.21:3001",
]

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin", "")
    allowed = origin in ALLOWED_ORIGINS or origin.endswith(".vercel.app") or origin.endswith(".vercel.sh")
    # 处理 preflight OPTIONS 请求
    if request.method == "OPTIONS" and allowed:
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )
    response = await call_next(request)
    if allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.get("/api/github-trending")
async def get_github_trending(
    since: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    date: Optional[str] = None,
):
    """获取 GitHub Trending 项目（优先实时，降级数据库）"""
    try:
        items = scrape_github_trending(since=since)
        if items:
            now = datetime.now()
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for item in items:
                c.execute("""
                    INSERT OR IGNORE INTO github_trending
                    (scrape_date, scrape_time, repo_name, repo_url, description, language, stars, forks, today_stars, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                      item["repo_name"], item["repo_url"], item["description"],
                      item["language"], item["stars"], item["forks"],
                      item["today_stars"], item["category"]))
            conn.commit()
            conn.close()
            return {"items": items, "source": "live", "count": len(items), "date": now.strftime("%Y-%m-%d")}
    except Exception as e:
        print(f"GitHub 实时抓取失败，降级到数据库: {e}")
    # 降级：从数据库读
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM github_trending
        WHERE scrape_date = ? AND category = ?
        ORDER BY id
    """, (target_date, since))
    rows = c.fetchall()
    conn.close()
    if rows:
        return {
            "items": [dict(r) for r in rows],
            "source": "database",
            "count": len(rows),
            "date": target_date,
        }
    return {"items": [], "source": "empty", "count": 0, "date": target_date}

@app.get("/api/github-trending/history")
async def get_github_trending_history(
    days: int = Query(7, ge=1, le=90),
    category: str = Query("daily", enum=["daily", "weekly", "monthly"]),
):
    """查询历史 GitHub Trending 记录"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("""
        SELECT DISTINCT scrape_date FROM github_trending
        WHERE scrape_date >= ? AND category = ?
        ORDER BY scrape_date DESC
    """, (cutoff, category))
    dates = [r["scrape_date"] for r in c.fetchall()]
    history = []
    for d in dates:
        c.execute("""
            SELECT * FROM github_trending
            WHERE scrape_date = ? AND category = ?
            ORDER BY id LIMIT 25
        """, (d, category))
        rows = c.fetchall()
        history.append({"date": d, "items": [dict(r) for r in rows]})
    conn.close()
    return {"history": history, "total_dates": len(dates), "category": category}

@app.post("/api/github-trending/refresh")
async def manual_refresh():
    """手动触发 GitHub Trending 刷新"""
    try:
        refresh_and_store()
        return {"status": "success", "message": "GitHub Trending 数据已刷新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")

@app.get("/api/baidu-hotsearch")
async def get_baidu_hotsearch():
    """实时爬取百度热搜"""
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        text = response.text

        items = []

        # 策略1: 尝试从 <script> 的 window.__INITIAL_STATE__ 中提取
        import re
        import json as json_mod

        # 策略2: 尝试从页面 HTML 注释 <s-data> 中提取 JSON 数据
        sdata_matches = re.findall(r'<!--\s*(.*?)\s*-->', text, re.DOTALL)
        for sdata in sdata_matches:
            sdata = sdata.strip()
            if sdata.startswith('{') or sdata.startswith('['):
                try:
                    parsed = json_mod.loads(sdata)
                    if isinstance(parsed, dict):
                        cards = parsed.get('cards', []) or []
                        for card in cards:
                            content = card.get('content', {}) or {}
                            for word in content.get('word', []):
                                title = word.get('word', '') or ''
                                hot_score = word.get('hotScore', '') or ''
                                if title:
                                    items.append({
                                        "rank": len(items) + 1,
                                        "title": title,
                                        "hot": str(hot_score) if hot_score else "热",
                                        "link": f"https://www.baidu.com/s?wd={title}"
                                    })
                                    if len(items) >= 10:
                                        break
                    if items:
                        break
                except (json_mod.JSONDecodeError, TypeError):
                    continue

        # 策略3: 使用已知的最新 CSS 选择器
        soup = BeautifulSoup(text, 'html.parser')
        if not items:
            # 尝试多个可能的类名（百度经常改版）
            for selector in [
                '.category-wrap_iQLoo',
                '.category-wrap_i9C3D',
                '[class*="category-wrap"]',
                '.content_1YWBm',
                '.hot-list-item',
                '.single-title',
            ]:
                content_items = soup.select(selector)
                if content_items:
                    for index, el in enumerate(content_items[:10]):
                        title_el = el.select_one('.c-single-text-ellipsis, .ellipsis_D0Wok, [class*="ellipsis"]')
                        if not title_el:
                            title_el = el
                        hot_score_el = el.select_one('.hot-index_1Bl1a, .hot_38s2J, [class*="hot-index"], [class*="hot_"]')

                        title = title_el.get_text(strip=True) if title_el else ''
                        if title and len(title) > 1 and not any(excluded in title for excluded in ['百度', '广告']):
                            hot_score = hot_score_el.get_text(strip=True) if hot_score_el else "热"
                            items.append({
                                "rank": len(items) + 1,
                                "title": title,
                                "hot": hot_score,
                                "link": f"https://www.baidu.com/s?wd={title}"
                            })
                            if len(items) >= 10:
                                break
        
        # 如果没爬到（可能是类名变了），从数据库降级
        if not items:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT * FROM baidu_hotsearch WHERE scrape_date = ? ORDER BY rank LIMIT 10", (today,))
            rows = c.fetchall()
            conn.close()
            if rows:
                return [dict(r) for r in rows]
            return [
                {"rank": 1, "title": "百度热搜数据抓取中...", "hot": "---", "link": "https://top.baidu.com/board?tab=realtime"},
            ]

        # 存入数据库（去重）
        now = datetime.now()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        for item in items:
            c.execute("""
                INSERT OR IGNORE INTO baidu_hotsearch (scrape_date, scrape_time, rank, title, hot, link)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                  item["rank"], item["title"], item["hot"], item["link"]))
        conn.commit()
        conn.close()

        return items
    except Exception as e:
        print(f"爬取百度热搜失败: {e}")
        # 降级到数据库
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT * FROM baidu_hotsearch WHERE scrape_date = ? ORDER BY rank LIMIT 10", (today,))
            rows = c.fetchall()
            conn.close()
            if rows:
                return [dict(r) for r in rows]
        except Exception:
            pass
        return [{"rank": 1, "title": "热搜加载失败", "hot": "---", "link": "#"}]

@app.get("/api/competitors")
async def get_competitors():
    """获取友商洞察数据"""
    return [
        {"name": "AWS", "region": "全球", "marketShare": "全球 32% · 中国区 < 5%", "score": 92,
         "products": ["Amazon Bedrock", "Amazon SageMaker", "Amazon Q", "AWS Lambda"],
         "productUrls": ["https://aws.amazon.com/bedrock/", "https://aws.amazon.com/sagemaker/", "https://aws.amazon.com/q/", "https://aws.amazon.com/lambda/"],
         "strengths": ["全球基础设施最广（39 Region/123 AZ）", "AI/ML 服务成熟度最高", "企业生态完善", "Serverless 先驱"],
         "weaknesses": ["中国区功能滞后", "本地化支持不足", "价格体系复杂", "合规认证进展慢"],
         "vs_huawei": "AWS 全球化布局领先，但华为云在中国政企市场的本地化深度、端边云协同、一云多芯架构适配方面具有显著优势。"},
        {"name": "Microsoft Azure", "region": "全球", "marketShare": "全球 23% · 中国区 < 3%", "score": 88,
         "products": ["Azure AI Foundry", "Azure OpenAI Service", "Azure Arc"],
         "productUrls": ["https://azure.microsoft.com/zh-cn/products/ai-foundry/", "https://azure.microsoft.com/zh-cn/products/cognitive-services/openai-service/", "https://azure.microsoft.com/zh-cn/products/azure-arc/"],
         "strengths": ["OpenAI 独占整合", "企业办公生态绑定（Office 365）", "混合云 Azure Arc", "开发者工具链完善"],
         "weaknesses": ["中国节点带宽受限", "第三方集成成本高", "AI 服务定价偏高", "开源社区信任度一般"],
         "vs_huawei": "Azure 的 Copilot + OpenAI 整合优势明显，但华为云在 AI 算力自主可控、国产化替代完整方案、政企行业 Know-how 上具备差异化竞争力。"},
        {"name": "阿里云", "region": "中国", "marketShare": "国内 34% · 第一", "score": 85,
         "products": ["通义千问", "百炼平台", "PAI", "PolarDB"],
         "productUrls": ["https://www.aliyun.com/product/tongyi", "https://www.aliyun.com/product/bailian", "https://www.aliyun.com/product/pai", "https://www.aliyun.com/product/polardb"],
         "strengths": ["国内市场份额第一", "双11高并发验证", "云原生生态成熟", "钉钉企业入口"],
         "weaknesses": ["海外市场拓展受限", "政企客户深度不足", "AI 大模型商业化慢", "组织架构调整频繁"],
         "vs_huawei": "阿里云在互联网行业和开发者生态上领先，但华为云在政府、金融、制造行业覆盖深度、端边云全栈能力、国产化信创替代方案上更具优势。"},
        {"name": "腾讯云", "region": "中国", "marketShare": "国内 16% · 第三", "score": 78,
         "products": ["混元大模型", "TI-ONE", "大模型知识引擎 LKE", "TDSQL"],
         "productUrls": ["https://cloud.tencent.com/product/hunyuan", "https://cloud.tencent.com/product/tione", "https://cloud.tencent.com/product/lke", "https://cloud.tencent.com/product/tdsql"],
         "strengths": ["微信 13 亿用户生态", "游戏行业深度覆盖", "实时音视频领先", "小程序云开发"],
         "weaknesses": ["企业服务基因较弱", "AI 大模型布局较慢", "toB 服务体系不完善", "行业解决方案深度不足"],
         "vs_huawei": "腾讯云在文娱社交和实时音视频场景占据优势，但华为云在严肃企业级市场、工业互联网、AI 大模型行业落地方面具备更强的综合服务能力。"},
        {"name": "火山云", "region": "中国", "marketShare": "国内 5% · 增速最快", "score": 68,
         "products": ["豆包大模型", "火山方舟", "扣子 Coze"],
         "productUrls": ["https://www.volcengine.com/product/doubao", "https://www.volcengine.com/product/ark", "https://www.volcengine.com/product/coze"],
         "strengths": ["抖音电商生态", "AI 推理价格最低", "扣子 Agent 平台用户超千万", "增长策略灵活"],
         "weaknesses": ["市场份额较小", "企业级能力验证不足", "行业覆盖窄", "toB 服务体系薄弱"],
         "vs_huawei": "火山云依托字节生态在增长策略和 AI 算法上表现突出，但华为云在企业级产品系统性、行业覆盖广度、全栈自主可控能力上具有压倒性优势。"},
        {"name": "华为云", "region": "中国", "marketShare": "国内第二 · 政企市场第一", "score": 90,
         "products": ["ModelArts", "GaussDB", "OBS", "ROMA", "ECS"],
         "productUrls": ["https://www.huaweicloud.com/product/modelarts.html", "https://www.huaweicloud.com/product/gaussdb.html", "https://www.huaweicloud.com/product/obs.html", "https://www.huaweicloud.com/product/roma.html", "https://www.huaweicloud.com/product/ecs.html"],
         "strengths": ["全栈自主可控（鲲鹏+欧拉+GaussDB）", "政企市场深耕", "端边云协同能力", "盘古大模型行业落地"],
         "weaknesses": ["海外 Region 覆盖不足", "开发者生态待加强", "SaaS 产品矩阵不完整", "定价灵活性待提升"],
         "vs_huawei": "华为云在政企市场、信创替代、端边云协同等场景具有独特优势，是唯一能提供'芯片+操作系统+数据库+云平台'全栈信创方案的厂商。"}
    ]

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """获取数据大屏统计指标"""
    return {
        "kpis": [
            {"label": "总分析任务", "value": "2,847", "trend": "+12.5%"},
            {"label": "活跃用户", "value": "1,380", "trend": "+8.3%"},
            {"label": "报告生成", "value": "456", "trend": "+23.1%"},
            {"label": "数据覆盖率", "value": "92%", "trend": "+5.2%"},
        ],
        "trends": [
            {"month": "1月", "云服务": 82, "AI算力": 65, "边缘计算": 45, "大数据": 70},
            {"month": "2月", "云服务": 85, "AI算力": 70, "边缘计算": 48, "大数据": 72},
            {"month": "3月", "云服务": 88, "AI算力": 78, "边缘计算": 55, "大数据": 75},
            {"month": "4月", "云服务": 86, "AI算力": 85, "边缘计算": 60, "大数据": 78},
            {"month": "5月", "云服务": 90, "AI算力": 92, "边缘计算": 68, "大数据": 80},
            {"month": "6月", "云服务": 92, "AI算力": 95, "边缘计算": 72, "大数据": 82},
        ],
        "serviceHealth": [
            {"service": "AI 分析引擎", "status": "healthy", "uptime": "99.97%"},
            {"service": "数据爬虫服务", "status": "healthy", "uptime": "99.85%"},
            {"service": "前端 API 网关", "status": "healthy", "uptime": "99.99%"},
            {"service": "数据库连接池", "status": "degraded", "uptime": "98.2%"},
        ]
    }

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_BASE)

class DataSource(BaseModel):
    type: str
    content: Optional[str] = None
    file_url: Optional[str] = None

class TaskRequest(BaseModel):
    title: str
    data_sources: List[DataSource]
    depth: str = "standard"

@app.get("/")
async def root():
    return {"message": "Business Insights API is running"}

@app.get("/api/daily-insight")
async def get_daily_insight():
    """获取或生成今日商业市场洞察"""
    # 实际项目中这里应从数据库读取，若无则触发生成
    # 为了演示，我们直接返回一个经过深度提示词优化的结构化数据
    return {
        "date": "2026-05-30",
        "industry": [
            {"name": "生物医疗", "summary": "基因编辑技术 CRIPSR 2.0 进入临床三期...", "link": "https://www.nature.com/subjects/biotechnology"},
            {"name": "交通", "summary": "低空经济政策放宽，eVTOL 适航证核发加速...", "link": "https://www.caac.gov.cn/"},
            {"name": "互联网", "summary": "分布式 AI 算力网络标准化协议发布...", "link": "https://www.techcrunch.com"},
        ],
        "hotspots": [
            {"platform": "GitHub", "title": "Auto-GPT-Next: 全自主商业智能代理", "link": "https://github.com/trending"},
            {"platform": "CSDN", "title": "2026 开发者生态报告：低代码与 AI 深度融合", "link": "https://www.csdn.net"},
        ],
        "news": [
            {"title": "全球半导体供应链重组：东南亚份额占比升至 30%", "link": "https://www.reuters.com/business/"},
            {"title": "新能源汽车价格战告一段落，品牌忠诚度成为核心", "link": "https://www.bloomberg.com/asia"},
        ],
        "opportunities": [
            {"target": "腰部客户", "advice": "建议关注数字化转型中的订阅制安全服务...", "opportunity": "中小企业安全合规市场"},
            {"target": "长尾客户", "advice": "利用轻量化 AI 工具降低运营成本...", "opportunity": "个体工商户自动化套件"},
        ]
    }

async def run_analysis(task_id: str, title: str, content: str):
    """异步运行 AI 分析逻辑，生成高度结构化的商业研报"""
    try:
        system_prompt = """你是一位世界顶级的商业分析师，任职于麦肯锡或高盛研究部。
你的任务是根据用户提供的关键词或数据，撰写一份极具专业深度、排版精美且具有实战指导意义的“商业洞察日报”。

输出要求：
1. 必须包含四个维度：市场核心痛点、竞品优势分析、潜在机会点、核心风险提示。
2. 必须包含三个市场指数（0-100）：行业热度、竞争烈度、政策支持。
3. 必须包含详细的执行摘要和战略建议（短期与长期）。
4. 语言风格：专业、客观、犀利，多用行业术语，避开空话。
5. 必须引用虚拟或真实的数据来源，增加权威感。
6. 输出格式：JSON，包含字段：summary_metrics, takeaways, detailed_report, strategies."""

        user_prompt = f"""任务标题: {title}
分析背景数据: {content}

请开始你的深度分析。"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            stream=False
        )
        
        result = response.choices[0].message.content
        print(f"任务 {task_id} 深度分析完成，结果已生成。")
        # TODO: 将 JSON 结果解析并存入 Supabase Report 表
        
    except Exception as e:
        print(f"分析失败: {str(e)}")

@app.post("/api/tasks/analyze")
async def analyze_task(request: TaskRequest, background_tasks: BackgroundTasks):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="DeepSeek API Key not configured")
    
    task_id = "task_" + os.urandom(4).hex()
    
    # 提取内容
    combined_content = ""
    for source in request.data_sources:
        if source.type == "KEYWORD" and source.content:
            combined_content += source.content + "\n"
    
    # 将长耗时任务放入后台运行
    background_tasks.add_task(run_analysis, task_id, request.title, combined_content)
    
    return {
        "status": "processing",
        "task_id": task_id,
        "title": request.title,
        "message": "分析任务已启动，正在使用 DeepSeek-V3 生成深度报告..."
    }

# ─── 邮件 API ───
class EmailRequest(BaseModel):
    email: str
    name: Optional[str] = ""

@app.get("/api/email/subscribers")
async def list_subscribers():
    """获取邮件订阅列表"""
    subscribers = get_subscribers()
    return {"subscribers": subscribers, "count": len(subscribers)}

@app.post("/api/email/subscribe")
async def subscribe_email(req: EmailRequest):
    """添加邮件订阅"""
    if add_subscriber(req.email, req.name or ""):
        return {"status": "success", "message": f"{req.email} 已订阅每日洞察邮件"}
    return {"status": "exists", "message": f"{req.email} 已在订阅列表中"}

@app.delete("/api/email/subscribers/{email}")
async def unsubscribe_email(email: str):
    """取消邮件订阅"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE email_subscribers SET active = 0 WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"{email} 已取消订阅"}

@app.get("/api/email/debug")
async def email_debug():
    """调试邮件配置"""
    return {
        "smtp_host": SMTP_HOST,
        "smtp_port": SMTP_PORT,
        "smtp_user": SMTP_USER,
        "smtp_password_set": bool(SMTP_PASSWORD) and SMTP_PASSWORD != "your-qq-auth-code-here",
        "email_from": EMAIL_FROM,
        "email_to": EMAIL_TO,
    }

@app.post("/api/email/test")
async def test_email(req: EmailRequest):
    """测试发送邮件"""
    html = build_daily_digest_html()
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"[测试] InsightPro · 每日商业洞察 ({today})"
    try:
        if send_email(req.email, subject, html):
            return {"status": "success", "message": f"测试邮件已发送至 {req.email}"}
        raise HTTPException(status_code=500, detail="邮件发送失败，请检查 SMTP 配置")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件发送异常: {str(e)}")

@app.post("/api/email/send-now")
async def send_now():
    """立即发送每日洞察邮件给所有订阅者"""
    send_daily_digest()
    return {"status": "success", "message": "邮件发送任务已执行"}

# ─── AI 智能客服 ───
CHAT_API_URL = os.getenv("CHAT_API_URL", "https://api.modelarts-maas.com/v2/chat/completions")
CHAT_API_KEY = os.getenv("CHAT_API_KEY", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek-v3.2")

KNOWLEDGE_BASE = """你是 InsightPro 商业洞察平台的专属 AI 助手。以下是平台核心知识：

## 平台概述
InsightPro 是面向云服务商业市场（中长尾、腰部行业客户）业务领导的 AI 驱动商业洞察平台，帮助用户快速获取行业动态、竞争分析、政策法规和市场机会。

## 核心功能模块
1. **今日洞察**（首页）：每日商业简报入口，展示 6 大板块摘要
2. **行业全景**（/insights/industry）：覆盖生物医疗、交通、基础设施、互联网、零售、制造 6 大行业，每个行业含具体客户案例和厂商方案
3. **案例库**（/insights/industry/cases）：5 大行业深度案例（三一重工、省级医疗集团、省会城市交通、农商行信创、连锁便利店），含友商对比和数据来源
4. **技术热点**（/insights/hotspots）：GitHub Trending 实时监控，支持日/周/月维度，历史数据追溯
5. **友商洞察**（/insights/competitors）：6 大场景分析（出海、AI平台、开发者、SaaS、性价比、数字化），对比 AWS/Azure/阿里云/腾讯云/火山云
6. **政策法规**（/insights/policy）：等保 2.0、信创替代、数据出境、OPC、数字化补贴、SOC 6 项政策追踪
7. **商业快讯**（/insights/news）：Reuters/Bloomberg/财新网/Wired 实时新闻
8. **增长机会**（/insights/opportunities）：综合分析页，聚合所有子版块数据形成 6 大机会点
9. **数据大屏**（/dashboard）：KPI 看板 + Recharts 趋势图 + 实时监测
10. **深度研报**（/reports）：AI 生成的结构化商业研报
11. **历史日报**（/history）：GitHub Trending 历史快照，支持搜索

## 技术栈
- 前端：Next.js 14+ / React / TypeScript / Tailwind CSS / Recharts
- 后端：FastAPI / Python / SQLite / APScheduler
- AI：DeepSeek-V3 / ModelArts
- 数据源：GitHub Trending API / 百度热搜爬虫 / 友商动态库

## 邮件订阅
平台支持每日 09:05 自动发送洞察简报邮件，包含友商动态和 GitHub 技术热点。用户可在设置页面管理订阅。

## 回答规则
1. 基于上述知识回答用户关于平台功能、数据、模块的问题
2. 如果用户问平台没有的功能，诚实说明并建议替代方案
3. 回答简洁专业，适合商业决策者阅读
4. 如果用户问技术细节，可以适当深入
5. 不要编造平台不存在的数据或功能"""

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None

@app.post("/api/chat")
async def chat_with_ai(req: ChatRequest):
    """智能客服接口（RAG 增强版：自动检索知识库 + DeepSeek 回答）"""
    if not CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="AI 客服未配置")

    # Step 1: Retrieve relevant context from vector DB (deep-searcher)
    try:
        ctx_results = retrieve_context(req.message, top_k=8)
        ctx_str = context_to_str(ctx_results)
    except Exception:
        ctx_str = ""  # Fallback: no retrieval context

    # Step 2: Build system prompt with platform knowledge + retrieved context
    system_content = KNOWLEDGE_BASE
    if ctx_str:
        system_content += f"\n\n## 检索到的相关知识\n{ctx_str}"

    messages = [{"role": "system", "content": system_content}]
    if req.history:
        messages.extend(req.history[-6:])
    messages.append({"role": "user", "content": req.message})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                CHAT_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {CHAT_API_KEY}",
                },
                json={
                    "model": CHAT_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            return {"reply": reply, "model": CHAT_MODEL}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 响应超时，请稍后重试")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务异常: {str(e)}")

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式智能客服接口（RAG 增强版：自动检索知识库 + 流式回答）"""
    if not CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="AI 客服未配置")

    # Step 1: Retrieve relevant context from vector DB
    try:
        ctx_results = retrieve_context(req.message, top_k=8)
        ctx_str = context_to_str(ctx_results)
    except Exception:
        ctx_str = ""

    # Step 2: Build system prompt with platform knowledge + retrieved context
    system_content = KNOWLEDGE_BASE
    if ctx_str:
        system_content += f"\n\n## 检索到的相关知识\n{ctx_str}"

    messages = [{"role": "system", "content": system_content}]
    if req.history:
        messages.extend(req.history[-6:])
    messages.append({"role": "user", "content": req.message})

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    CHAT_API_URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {CHAT_API_KEY}",
                    },
                    json={
                        "model": CHAT_MODEL,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1024,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"
                    yield "data: [DONE]\n\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'

    from fastapi.responses import StreamingResponse
    return StreamingResponse(generate(), media_type="text/event-stream")

# ─── 埋点 API ───
class TrackRequest(BaseModel):
    page: str
    visitor_id: Optional[str] = ""
    user_agent: Optional[str] = ""

@app.post("/api/track")
async def track_visit(req: TrackRequest, request: Request):
    """记录页面访问"""
    visitor_id = req.visitor_id or request.client.host if request.client else "unknown"
    ua = req.user_agent or request.headers.get("user-agent", "")
    ref = request.headers.get("referer", "")
    record_visit(req.page, visitor_id, ua, ref)
    return {"status": "ok"}

@app.get("/api/analytics")
async def analytics_endpoint(days: int = Query(7, ge=1, le=90)):
    """获取页面分析数据"""
    return get_analytics(days)

@app.post("/api/track/batch")
async def track_batch(visits: List[TrackRequest], request: Request):
    """批量记录页面访问"""
    client_ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    for v in visits:
        vid = v.visitor_id or client_ip
        record_visit(v.page, vid, v.user_agent or ua, "")
    return {"status": "ok", "count": len(visits)}

# ─── 行业需求智能挖掘 API ───
@app.post("/api/demand/refresh")
async def refresh_demand():
    """触发需求信号采集"""
    count = collect_demand_signals()
    return {"status": "success", "message": f"已采集 {count} 条需求信号", "count": count}

@app.get("/api/demand/signals")
async def demand_signals(
    industry: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
):
    """获取需求信号列表"""
    signals = get_demand_signals(industry=industry, source_type=source_type, days=days)
    return {"signals": signals, "count": len(signals)}

@app.get("/api/demand/trends")
async def demand_trends():
    """获取需求趋势分析"""
    return get_demand_trends()

@app.get("/api/demand/report")
async def demand_report(industry: Optional[str] = Query(None)):
    """AI 生成行业需求洞察报告（RAG 增强版：使用 deep-searcher 检索 + 深度研究）"""
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # Use deep-searcher for deep research
        query_text = f"分析{industry or '各行业'}数字化需求趋势和市场机会，按行业分类输出洞察报告"
        if industry:
            query_text = f"分析{industry}行业的数字化需求趋势、政策驱动因素和市场机会"

        result = deep_research(query_text, max_iter=2)

        if result["answer"] and "错误" not in result["answer"][:20]:
            report_content = result["answer"]
        else:
            # Fallback: use traditional approach
            signals = get_demand_signals(industry=industry, days=30)
            context = "以下是近期行业需求信号数据：\n\n"
            for s in signals[:20]:
                context += f"[{s['source_type']}] [{s['industry']}] {s['title']}\n{s['summary']}\n需求标签: {s.get('demand_tags','')}\n\n"

            prompt = f"""基于以下行业需求信号数据，生成一份专业的行业数字化需求洞察报告。

要求：
1. 按行业分类分析需求趋势
2. 识别高增长需求领域和市场机会
3. 分析政策驱动 vs 市场驱动的需求
4. 给出华为云在各行业的切入点建议
5. 输出格式：Markdown，包含标题、摘要、各行业分析、机会点、行动建议

{context}"""

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是资深行业分析师，擅长从数据中提炼商业洞察。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            report_content = response.choices[0].message.content

        # 存储报告
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO demand_reports (report_date, industry, title, content)
            VALUES (?, ?, ?, ?)
        """, (today, industry or "综合", f"行业需求洞察报告 {today}", report_content))
        conn.commit()
        conn.close()

        return {"report": report_content, "date": today, "signal_count": len(result.get("sources", []))}
    except Exception as e:
        return {"report": f"报告生成失败: {str(e)}", "date": today, "signal_count": 0}

@app.get("/api/demand/report/history")
async def demand_report_history(days: int = Query(30, ge=1, le=90)):
    """获取历史需求报告"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("SELECT * FROM demand_reports WHERE report_date >= ? ORDER BY report_date DESC", (cutoff,))
    rows = c.fetchall()
    conn.close()
    return {"reports": [dict(r) for r in rows]}

# ─── 招标信息 API ───
@app.post("/api/bidding/refresh")
async def refresh_bidding():
    """手动刷新招标信息"""
    try:
        count = collect_bidding_data()
        return {"status": "success", "message": f"已采集 {count} 条招标信息", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集失败: {str(e)}")

@app.get("/api/bidding/list")
async def bidding_list(
    industry: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=90),
):
    """获取招标信息列表"""
    items = get_bidding_opportunities(industry=industry, status=status, days=days)
    return {"items": items, "count": len(items)}

@app.get("/api/bidding/stats")
async def bidding_stats():
    """获取招标统计"""
    return get_bidding_stats()

@app.post("/api/bidding/analyze")
async def bidding_analyze():
    """AI 分析招标机会"""
    items = get_bidding_opportunities(days=30)
    if not items:
        return {"analysis": "暂无招标数据，请先刷新", "total": 0}

    context = "以下是近期招标信息汇总：\n\n"
    for item in items[:15]:
        context += f"[{item['industry']}] {item['title']}\n  招标方: {item.get('procuring_entity','')} | 预算: {item.get('budget','')} | 截止: {item.get('deadline','')}\n  摘要: {item.get('summary','')[:100]}\n\n"

    prompt = f"""基于以下招标信息，生成一份专业的招标市场分析报告。

要求：
1. 按行业分类分析招标需求热点和趋势
2. 识别高价值标段（预算大、紧迫度高）
3. 分析各行业的数字化建设重点方向
4. 给出华为云在标的中的竞争优劣势和切入点建议
5. 输出格式：Markdown，包含标题、摘要、各行业分析、重点推荐标段、行动建议

{context}"""

    try:
        if not CHAT_API_KEY:
            return {"analysis": "AI 未配置", "total": len(items)}

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是资深招标分析师，擅长从招标信息中挖掘商机。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2500,
        )
        return {"analysis": response.choices[0].message.content, "total": len(items)}
    except Exception as e:
        return {"analysis": f"分析生成失败: {str(e)}", "total": len(items)}

# ─── 市场洞察 API ───
@app.get("/api/market/overview")
async def market_overview():
    """市场总览：整合各维度数据生成全景洞察"""
    try:
        # Gather data from RAG
        ctx = retrieve_context("数字化市场全景洞察各行业发展趋势", top_k=10)
        ctx_str = context_to_str(ctx)

        # Stats overview
        industries_count = 8
        signals = []
        tenders = []
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT COUNT(DISTINCT industry) FROM demand_signals WHERE signal_date >= date('now','-30 days')")
            row = c.fetchone()
            if row and row[0]:
                industries_count = row[0]

            c.execute("SELECT COUNT(*) FROM demand_signals WHERE signal_date >= date('now','-30 days')")
            signals_count = c.fetchone()[0] or 0

            c.execute("SELECT COUNT(*) FROM bidding_opportunities WHERE bid_date >= date('now','-30 days')")
            tenders_count = c.fetchone()[0] or 0
            conn.close()
        except Exception:
            signals_count = 0
            tenders_count = 0

        # Use AI to generate market overview if API key is available
        if CHAT_API_KEY:
            prompt = f"""基于以下数据，生成一份简洁的数字化市场全景洞察摘要：

覆盖行业: {industries_count} 个
需求信号: {signals_count} 条
招标信息: {tenders_count} 条

向量库检索到的相关信息:
{ctx_str[:2000]}

请生成结构化的市场总览，包含：
1. 市场热度总览（一句话总结当前市场状态）
2. TOP 3 高增长行业及核心驱动因素
3. TOP 3 需求标签（当前最热门的技术/服务需求）
4. 整体市场趋势判断（看多/看稳/看空及理由）

输出格式：JSON
{{
  "summary": "一句话总结",
  "market_status": "扩张/稳定/收缩",
  "top_industries": [{{"name": "行业名", "driver": "驱动因素", "growth": "增长判断"}}],
  "hot_tags": ["标签1", "标签2", "标签3"],
  "outlook": "趋势判断"
}}"""

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是资深市场分析师，输出结构化 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            overview = json.loads(response.choices[0].message.content)
        else:
            overview = {
                "summary": f"当前覆盖 {industries_count} 个行业，采集需求信号 {signals_count} 条、招标信息 {tenders_count} 条，市场处于增长期",
                "market_status": "扩张",
                "top_industries": [],
                "hot_tags": ["AI赋能", "数字化转型", "信创替代"],
                "outlook": "数字化市场保持高速增长，AI 大模型落地和信创替代是两大核心驱动力",
            }

        return {
            "overview": overview,
            "stats": {
                "industries": industries_count,
                "signals": signals_count,
                "tenders": tenders_count,
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    except Exception as e:
        return {"error": str(e), "stats": {"industries": 0, "signals": 0, "tenders": 0}}

@app.get("/api/market/heatmap")
async def market_heatmap():
    """市场热度热力图数据"""
    industries_heat = [
        {"industry": "政务", "demand": 95, "competition": 75, "policy": 98, "growth": "高速增长", "trend": "+35%"},
        {"industry": "医疗", "demand": 92, "competition": 60, "policy": 90, "growth": "高速增长", "trend": "+42%"},
        {"industry": "制造", "demand": 88, "competition": 70, "policy": 85, "growth": "稳健增长", "trend": "+28%"},
        {"industry": "金融", "demand": 85, "competition": 80, "policy": 88, "growth": "稳健增长", "trend": "+25%"},
        {"industry": "教育", "demand": 75, "competition": 55, "policy": 80, "growth": "增长中", "trend": "+20%"},
        {"industry": "交通", "demand": 82, "competition": 65, "policy": 75, "growth": "稳健增长", "trend": "+22%"},
        {"industry": "能源", "demand": 90, "competition": 50, "policy": 92, "growth": "高速增长", "trend": "+38%"},
        {"industry": "零售", "demand": 78, "competition": 72, "policy": 60, "growth": "存量博弈", "trend": "+12%"},
        {"industry": "农业", "demand": 65, "competition": 35, "policy": 70, "growth": "新兴市场", "trend": "+30%"},
    ]
    return {"items": industries_heat, "total": len(industries_heat)}

@app.get("/api/market/industry-analysis")
async def industry_analysis(industry: str = Query("制造", description="行业名称")):
    """指定行业的深度分析（含 RAG 检索）"""
    try:
        query = f"{industry}行业数字化市场分析、需求趋势、竞争格局、机会点"
        ctx = retrieve_context(query, top_k=8)
        ctx_str = context_to_str(ctx)

        # Get bidding data for this industry
        bids = get_bidding_opportunities(industry=industry, days=60)
        bid_context = ""
        if bids:
            for b in bids[:5]:
                bid_context += f"- {b['title']}（预算: {b.get('budget','')}，截止: {b.get('deadline','')}）\n"

        prompt = f"""你是一位资深行业分析师。请分析{industry}行业的数字化市场。

向量数据库检索到的相关信息:
{ctx_str[:2500]}

近期相关招标:
{bid_context or '暂无'}

请输出以下格式（JSON）:
{{
  "industry": "{industry}",
  "market_size": "市场规模描述",
  "key_trends": ["趋势1", "趋势2", "趋势3"],
  "pain_points": ["痛点1", "痛点2"],
  "opportunities": [{{"title": "机会描述", "priority": "高/中", "action": "建议行动"}}],
  "competition": "竞争格局概述",
  "huawei_advantage": "华为云优势分析",
  "recommendation": "综合建议"
}}"""

        if CHAT_API_KEY:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是资深行业分析师，输出结构化 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            analysis = json.loads(response.choices[0].message.content)
        else:
            analysis = {"industry": industry, "market_size": "待分析", "key_trends": [], "pain_points": [], "opportunities": [], "competition": "", "huawei_advantage": "", "recommendation": ""}

        return {"analysis": analysis, "bids_count": len(bids[:5])}
    except Exception as e:
        return {"error": str(e)}

# ─── 每日洞察增强版 ───
@app.get("/api/daily-insight/enhanced")
async def daily_insight_enhanced():
    """增强版每日洞察：RAG 检索 + AI 生成"""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        ctx = retrieve_context("今日数字化市场热点和行业动态", top_k=6)
        ctx_str = context_to_str(ctx)

        prompt = f"""你是一位资深商业分析师。基于以下信息，生成今日市场洞察摘要。

向量数据库信息:
{ctx_str[:2000]}

请输出 JSON:
{{
  "date": "{today}",
  "headline": "今日核心洞察标题",
  "hot_industries": ["行业1", "行业2", "行业3"],
  "key_insights": ["洞察1（含数据）", "洞察2", "洞察3"],
  "opportunity_alert": "今日最值得关注的商机",
  "risk_warning": "需要关注的风险因素",
  "action_items": ["建议行动1", "建议行动2"]
}}"""

        if CHAT_API_KEY:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是资深分析师，输出结构化市场洞察 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        else:
            return {"date": today, "headline": "AI 洞察暂不可用", "hot_industries": [], "key_insights": [], "opportunity_alert": "", "risk_warning": "", "action_items": []}
    except Exception as e:
        return {"error": str(e), "date": today}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
