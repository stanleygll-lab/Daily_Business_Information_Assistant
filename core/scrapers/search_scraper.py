# -*- coding: utf-8 -*-
"""
Toutiao Bidding & Commercial Opportunity Scraper
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urlparse, parse_qs, unquote
from playwright.async_api import BrowserContext
from core.models import BusinessNewsItem
from core.scrapers.base import BaseScraper


def resolve_sslocal(href: str) -> str:
    try:
        if "url=" in href:
            p = urlparse(href)
            params = parse_qs(p.query)
            if "url" in params:
                return unquote(params["url"][0])
    except Exception:
        pass
    return href


class ToutiaoBiddingScraper(BaseScraper):
    """头条商业招采专项定向抓取器"""

    def __init__(self, context: BrowserContext, queries: List[str]):
        super().__init__(name="Toutiao Bidding")
        self.context = context
        self.queries = queries

    async def fetch(self) -> List[BusinessNewsItem]:
        print(f"  🔍 启动头条招采商机挖掘 (共 {len(self.queries)} 组关键词)...")
        all_items: List[BusinessNewsItem] = []
        page = await self.context.new_page()

        try:
            for q in self.queries:
                url = f"https://so.toutiao.com/search?keyword={q}"
                try:
                    await page.goto(url, timeout=20000)
                    await page.wait_for_selector(".result-content", timeout=8000)
                    await asyncio.sleep(2)

                    results = await page.query_selector_all(".result-content")
                    count = 0
                    for res in results:
                        if count >= 3:
                            break
                        title_el = await res.query_selector("a")
                        if not title_el:
                            continue
                        title = (await title_el.inner_text()).strip()
                        href = await title_el.get_attribute("href") or ""
                        if href.startswith("sslocal://"):
                            href = resolve_sslocal(href)
                        if not href.startswith("http"):
                            href = "https://so.toutiao.com" + href

                        all_items.append(BusinessNewsItem(
                            title=title,
                            link=href,
                            source="头条商机快报",
                            date=datetime.now(),
                            is_bidding=True
                        ))
                        count += 1
                except Exception:
                    pass
        finally:
            await page.close()

        return all_items
