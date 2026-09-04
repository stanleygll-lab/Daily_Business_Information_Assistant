# -*- coding: utf-8 -*-
"""
Baidu News Search Scraper for Commercial & Bidding News
百度新闻商机定向抓取器 (含落地页真实 URL 重定向解析)
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote
from playwright.async_api import BrowserContext
import requests
from core.models import BusinessNewsItem
from core.scrapers.base import BaseScraper

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def resolve_final_url(url: str) -> str:
    """解析百度新闻跳转链接为目标真实 URL"""
    if not url or "baidu.com" not in url:
        return url
    try:
        resp = requests.get(url, headers={'User-Agent': USER_AGENT}, allow_redirects=True, timeout=8, stream=True)
        final_url = resp.url
        resp.close()
        return final_url
    except Exception:
        return url


def parse_baidu_time_source(meta_text: str):
    """从百度新闻 meta 文本提取来源与日期"""
    if not meta_text:
        return "百度新闻", datetime.now()
    meta_text = meta_text.replace("\n", " ").strip()
    parts = [p.strip() for p in meta_text.split(" ") if p.strip()]

    source = parts[0] if parts else "百度新闻"
    now = datetime.now()
    item_date = now

    for part in parts[1:]:
        if '分钟' in part:
            m = re.search(r'(\d+)', part)
            if m:
                item_date = now - timedelta(minutes=int(m.group(1)))
                break
        elif '小时' in part:
            m = re.search(r'(\d+)', part)
            if m:
                item_date = now - timedelta(hours=int(m.group(1)))
                break
        elif '昨天' in part:
            item_date = now - timedelta(days=1)
            break
        elif '天前' in part:
            m = re.search(r'(\d+)', part)
            if m:
                item_date = now - timedelta(days=int(m.group(1)))
                break
        elif re.match(r'\d{4}年\d{1,2}月\d{1,2}日', part):
            try:
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', part)
                item_date = datetime(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)), 12, 0)
                break
            except Exception:
                pass

    return source, item_date


class BaiduScraper(BaseScraper):
    """百度新闻专项商机爬虫"""

    def __init__(self, context: BrowserContext, queries: List[str]):
        super().__init__(name="Baidu News")
        self.context = context
        self.queries = queries

    async def fetch(self) -> List[BusinessNewsItem]:
        print(f"  🔍 启动百度新闻行业商机抓取 (共 {len(self.queries)} 组关键词)...")
        all_items: List[BusinessNewsItem] = []
        page = await self.context.new_page()

        try:
            for query in self.queries:
                url = f"https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&word={quote(query)}"
                try:
                    await page.goto(url, timeout=25000)
                    await asyncio.sleep(3)

                    cards = await page.query_selector_all(".result-op, .c-container")
                    count = 0
                    for card in cards:
                        if count >= 4:
                            break
                        try:
                            title_el = await card.query_selector("h3 a, .news-title_10014 a")
                            if not title_el:
                                continue
                            title = (await title_el.inner_text()).strip()
                            if len(title) < 6:
                                continue

                            href = await title_el.get_attribute("href") or ""
                            if not href:
                                continue

                            meta_el = await card.query_selector(".c-color-gray2, .news-source, .c-summary")
                            meta_text = (await meta_el.inner_text()) if meta_el else ""
                            source, item_date = parse_baidu_time_source(meta_text)

                            # 限制时效至72小时
                            if item_date < (datetime.now() - timedelta(hours=72)):
                                continue

                            real_url = resolve_final_url(href)
                            all_items.append(BusinessNewsItem(
                                title=title,
                                link=real_url,
                                source=f"百度·{source}",
                                date=item_date
                            ))
                            count += 1
                        except Exception:
                            continue
                except Exception as e:
                    print(f"  ⚠️ 百度检索 [{query}] 跳过: {e}")
        finally:
            await page.close()

        return all_items
