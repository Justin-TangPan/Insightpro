"""
需求信号业务逻辑
封装需求信号的采集、查询、趋势分析功能。
"""
from datetime import datetime, timedelta
from db import get_db


def collect_demand_signals():
    """采集需求信号 — 使用 derive_demand_signals() 从已爬取数据推导"""
    today = datetime.now().strftime("%Y-%m-%d")
    from crawlers import derive_demand_signals
    signals = derive_demand_signals()
    if not signals:
        print(f"[{today}] 需求信号推导无结果")
        return 0

    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM demand_signals WHERE signal_date = %s", (today,))
        for s in signals:
            c.execute("""
                INSERT INTO demand_signals (signal_date, source_type, industry, title, summary, url, relevance_score, demand_tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (today, s["source_type"], s["industry"], s["title"], s["summary"],
                  s["url"], s["relevance_score"], s.get("demand_tags", "")))
    print(f"[{today}] 需求信号推导完成: {len(signals)} 条")
    return len(signals)


def get_demand_signals(industry: str = None, source_type: str = None, days: int = 7) -> list:
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = "SELECT * FROM demand_signals WHERE signal_date >= %s"
        params = [cutoff]
        if industry:
            query += " AND industry = %s"
            params.append(industry)
        if source_type:
            query += " AND source_type = %s"
            params.append(source_type)
        query += " ORDER BY relevance_score DESC, signal_date DESC"
        c.execute(query, params)
        rows = c.fetchall()
        return [dict(r) for r in rows]


def get_demand_trends() -> dict:
    """分析需求趋势"""
    signals = get_demand_signals(days=30)
    by_industry = {}
    for s in signals:
        ind = s["industry"]
        if ind not in by_industry:
            by_industry[ind] = {"count": 0, "tags": [], "signals": []}
        by_industry[ind]["count"] += 1
        tags = s.get("demand_tags") or ""
        by_industry[ind]["tags"].extend(tags.split(","))
        by_industry[ind]["signals"].append(s)

    by_type = {}
    for s in signals:
        t = s["source_type"]
        by_type[t] = by_type.get(t, 0) + 1

    all_tags = []
    for s in signals:
        tags = s.get("demand_tags") or ""
        all_tags.extend(tags.split(","))
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
