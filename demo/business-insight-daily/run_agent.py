#!/usr/bin/env python3
"""
Business Insight Daily — Agent 系统主入口
===========================================
自动工作流：
1. 读取配置 (config.json) — 支持 DeepSeek / OpenAI 兼容
2. 联网搜索最新市场信息
3. LLM 生成深度洞察内容
4. HTML 渲染发布
5. 启动 Web 服务

配置方式：
  - config.json 文件（支持任意 OpenAI 兼容 API）
  - 环境变量 LLM_API_KEY / LLM_BASE_URL 覆盖

快速使用：
  python run_agent.py              # 使用 config.json
  python run_agent.py --fetch      # 强制联网再生成
  python run_agent.py --serve      # 只启动 Web 服务
  python run_agent.py --all        # 完整流程：搜索→生成→渲染→服务

设置你的 API Key：
  # 方法1：编辑 config.json
  # 方法2：环境变量
  set LLM_API_KEY=sk-your-key
  set LLM_BASE_URL=https://api.deepseek.com
  python run_agent.py
"""
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# 确保 agent 包可导入
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "agent"))

def print_banner():
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"""
╔══════════════════════════════════════╗
║  Business Insight Daily Agent       ║
║  {today}           ║
║  DeepSeek Flash · Auto-Refresh      ║
╚══════════════════════════════════════╝
    """)

def main():
    parser = argparse.ArgumentParser(description="Business Insight Daily Agent")
    parser.add_argument("--fetch", action="store_true", help="强制联网获取最新数据")
    parser.add_argument("--generate", action="store_true", help="用 LLM 生成内容")
    parser.add_argument("--render", action="store_true", help="渲染 HTML 页面")
    parser.add_argument("--serve", action="store_true", help="启动 Web 服务")
    parser.add_argument("--all", action="store_true", help="完整流程")
    parser.add_argument("--port", type=int, default=0, help="服务端口 (默认: config.json)")
    parser.add_argument("--config", default="", help="配置文件路径")

    args = parser.parse_args()

    # 默认行为：如果没指定任何 flag，执行完整流程
    if not any([args.fetch, args.generate, args.render, args.serve, args.all]):
        args.all = True

    # 加载配置
    from config import get_config
    cfg_path = args.config or str(BASE_DIR / "config.json")
    cfg = get_config(cfg_path)

    print_banner()

    # 验证配置
    if not cfg.is_valid:
        print(f"\n! 未配置 API Key")
        print(f"  请设置环境变量 LLM_API_KEY 或编辑 {cfg_path}")
        print(f"  或使用 OpenAI 兼容 API:")
        print(f"    set LLM_BASE_URL=https://your-api-endpoint")
        print(f"    set LLM_API_KEY=your-key")
        print(f"  默认使用: {cfg.base_url}")
        print()
        if args.serve:
            print("! 无 API Key 时只能启动服务，无法生成新内容")
        else:
            return

    data = {}
    date_str = datetime.now().strftime("%Y-%m-%d")

    # ========== Phase 1: Fetch ==========
    if args.all or args.fetch:
        print(f"\n[1/3] 联网获取最新数据...")
        from fetcher import DataFetcher
        fetcher = DataFetcher(cfg)
        keywords = fetcher.get_today_keywords()
        print(f"  搜索 {len(keywords)} 个主题...")
        search_data = fetcher.fetch_multi_topic(keywords)
        data["search_raw"] = search_data
        data["market_data"] = fetcher.get_market_data()
        data["competitors"] = fetcher._mock_search("云厂商动态")
        print(f"  Done. 获取到 {sum(len(v) for v in search_data.values())} 条结果")

    # ========== Phase 2: Generate ==========
    if args.all or args.generate:
        print(f"\n[2/3] LLM 生成洞察内容...")
        print(f"  模型: {cfg.model}")
        print(f"  端点: {cfg.base_url}")

        from generator import ContentGenerator
        gen = ContentGenerator(cfg)

        # 生成今日洞察
        print(f"  生成今日洞察...")
        search_data_for_llm = data.get("search_raw", {})
        data["daily_insights"] = gen.generate_daily_insight(search_data_for_llm, date_str)
        print(f"    -> {len(data['daily_insights'])} 条洞察")

        # 生成行业洞察
        print(f"  生成行业洞察...")
        data["industry_insights"] = gen.generate_industry_insights(search_data_for_llm, date_str)

        # 生成友商动态（用预设数据）
        print(f"  生成友商动态...")
        data["competitors"] = gen.generate_competitor_news(date_str)
        print(f"    -> {len(data['competitors'])} 条友商动态")

        # 生成商业机会
        print(f"  生成商业机会...")
        data["opportunities"] = gen.generate_opportunities(date_str)
        print(f"    -> {len(data['opportunities'])} 个商业机会")

        # 生成热搜
        data["baidu_hot"] = gen.generate_baidu_hot()

        print(f"  内容生成完成.")

    # ========== Phase 3: Render ==========
    if args.all or args.render:
        print(f"\n[3/3] 渲染 HTML 页面...")
        from renderer import render_html_files

        # 填充缺失数据
        if "daily_insights" not in data or not data["daily_insights"]:
            from generator import ContentGenerator
            gen = ContentGenerator(cfg)
            data["daily_insights"] = gen.generate_daily_insight({}, date_str)
        if "competitors" not in data or not data["competitors"]:
            from generator import ContentGenerator
            gen = ContentGenerator(cfg)
            data["competitors"] = gen.generate_competitor_news(date_str)
        if "opportunities" not in data or not data["opportunities"]:
            from generator import ContentGenerator
            gen = ContentGenerator(cfg)
            data["opportunities"] = gen.generate_opportunities(date_str)
        if "baidu_hot" not in data:
            from generator import ContentGenerator
            gen = ContentGenerator(cfg)
            data["baidu_hot"] = gen.generate_baidu_hot()

        # 默认热搜作为 news 备用
        if "hot_news" not in data:
            data["hot_news"] = data.get("baidu_hot", [])

        render_html_files(BASE_DIR, data, date_str)

    # ========== Phase 4: Serve ==========
    if args.all or args.serve:
        port = args.port or cfg.server_port
        print(f"\n 启动 Web 服务: http://localhost:{port}")
        print(f"  按 Ctrl+C 停止\n")

        # 确保 server.py 存在且能在项目根目录运行
        server_py = BASE_DIR / "server.py"
        if not server_py.exists():
            print(f"  注意: server.py 不存在，使用简易内置服务")
            from http.server import HTTPServer, SimpleHTTPRequestHandler
            import os
            os.chdir(BASE_DIR)
            server = HTTPServer((cfg.server_host, port), SimpleHTTPRequestHandler)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\n  服务已停止")
        else:
            import subprocess
            import os
            os.chdir(BASE_DIR)
            cmd = [sys.executable, "server.py"]
            if args.port:
                cmd.extend(["--port", str(port)])
            subprocess.run(cmd)

    print("\n  Done.")


if __name__ == "__main__":
    main()
