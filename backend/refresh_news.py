#!/usr/bin/env python3
"""
手动刷新新闻数据
"""
import sys
sys.path.insert(0, '.')
from crawlers import crawl_all_news
from db import get_db
from datetime import datetime

def main():
    print("开始抓取所有新闻源...")
    results = crawl_all_news()

    print("\n抓取结果统计:")
    for source, items in results.items():
        print(f"  {source}: {len(items)} 条")
        if items:
            try:
                title = items[0]['title'][:60]
                print(f"    示例: {title}")
            except:
                pass

    today = datetime.now().strftime('%Y-%m-%d')
    now = datetime.now()

    # 入库 cloud_vendor_news
    cloud_items = results.get('cloud_vendors', [])
    if cloud_items:
        with get_db() as conn:
            c = conn.cursor()
            inserted = 0
            for item in cloud_items:
                try:
                    c.execute('''
                        INSERT INTO cloud_vendor_news (vendor, title, url, summary, crawl_date, created_at, category)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (vendor, title, url) DO NOTHING
                    ''', (
                        item['vendor'], item['title'], item['url'], item.get('summary', ''),
                        today, now, item.get('category', '产品动态')
                    ))
                    if c.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    print(f"cloud_vendor_news 入库失败 {item['title'][:30]}: {e}")
            conn.commit()
            print(f"\ncloud_vendor_news 入库 {inserted}/{len(cloud_items)} 条")

    # 入库 competitor_news（从 cloud_vendors 中提取）
    competitor_items = []
    for item in cloud_items:
        if item['vendor'] in ['阿里云', '腾讯云', 'AWS', '火山云']:
            competitor_items.append(item)

    if competitor_items:
        with get_db() as conn:
            c = conn.cursor()
            inserted = 0
            for item in competitor_items:
                try:
                    c.execute('''
                        INSERT INTO competitor_news (vendor, title, link, summary, scrape_date, created_at, category)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (vendor, title, link) DO NOTHING
                    ''', (
                        item['vendor'], item['title'], item['url'], item.get('summary', ''),
                        today, now, item.get('category', '产品动态')
                    ))
                    if c.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    print(f"competitor_news 入库失败 {item['title'][:30]}: {e}")
            conn.commit()
            print(f"competitor_news 入库 {inserted}/{len(competitor_items)} 条")

    # 入库 industry_news（从 policy, 36kr, cls, yicai, ai_news 合并）
    industry_items = []
    for source in ['policy', '36kr', 'cls', 'yicai', 'ai_news']:
        industry_items.extend(results.get(source, []))

    if industry_items:
        with get_db() as conn:
            c = conn.cursor()
            inserted = 0
            for item in industry_items:
                try:
                    c.execute('''
                        INSERT INTO industry_news (source, title, link, summary, scrape_date, created_at, category)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (source, title, link) DO NOTHING
                    ''', (
                        item.get('source', 'unknown'), item['title'], item['url'], item.get('summary', ''),
                        today, now, item.get('category', '行业动态')
                    ))
                    if c.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    print(f"industry_news 入库失败 {item['title'][:30]}: {e}")
            conn.commit()
            print(f"industry_news 入库 {inserted}/{len(industry_items)} 条")

    print("\n刷新完成")

if __name__ == '__main__':
    main()