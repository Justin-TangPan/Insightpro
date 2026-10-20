from datetime import date
from unittest.mock import patch

from crawlers import VENDOR_SOURCES, _crawl_vendor_news, _domestic_focus, _parse_volcengine_updates, _update_category


class Response:
    text = '<a href="/news/one">正式发布全新的云服务能力更新</a><a href="/news/one">正式发布全新的云服务能力更新</a>'
    encoding = ""


def test_vendor_sources_resolve_relative_urls_and_deduplicate():
    with patch("crawlers._safe_get", return_value=Response()):
        items = _crawl_vendor_news("测试云", "官方", ["https://example.com/news"], 8)
    assert len(items) == 1
    assert items[0]["url"] == "https://example.com/news/one"


def test_chinese_vendors_use_domestic_sources():
    sources = {vendor: urls for vendor, _, urls, _ in VENDOR_SOURCES}
    assert all("alibabacloud.com" not in url for url in sources["Alibaba Cloud"])
    assert all(url.startswith("https://cloud.tencent.com/") for url in sources["Tencent Cloud"])


def test_updates_are_classified_and_overseas_regions_do_not_displace_domestic_news():
    assert _update_category("新产品", "云开发正式发布") == "Product Launch"
    assert _update_category("新功能/规格", "行业解决方案上线") == "Solution New"
    assert not _domestic_focus("云防火墙在巴西圣保罗开服")
    assert _domestic_focus("AI 引擎版正式发布")


def test_volcengine_release_rows_keep_official_dates_and_skip_old_or_future_items():
    markdown = """|SSL 证书到期提醒与自动更新 |支持自动识别到期证书并更新。 |2026\\-10\\-16 |全部 |
|10.13 |* 模型新增：支持新的 Coding Agent 模型。 |文档 |
|旧功能 |旧功能说明 |2026\\-07\\-01 |全部 |
|未来功能 |尚未发布 |2026\\-10\\-30 |全部 |"""
    items = _parse_volcengine_updates(markdown, "火山引擎产品", "https://docs.volcengine.com/docs/ark/example", date(2026, 10, 19))
    assert [item["published_date"] for item in items] == ["2026-10-16", "2026-10-13"]
    assert items[0]["title"] == "火山引擎产品 · SSL 证书到期提醒与自动更新"
    assert "Coding Agent" in items[1]["summary"]
