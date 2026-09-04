# -*- coding: utf-8 -*-
"""
RSS Scraper for Business Feeds
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import httpx
import feedparser
from core.models import BusinessNewsItem
from core.scrapers.base import BaseScraper

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class BusinessRssScraper(BaseScraper):
    """商业资讯 RSS 订阅抓取器"""

    def __init__(self, feeds: List[Dict[str, Any]]):
        super().__init__(name="Business RSS")
        self.feeds = [f for f in feeds if f.get("enabled", True)]

    async def fetch(self) -> List[BusinessNewsItem]:
        items: List[BusinessNewsItem] = []
        if not self.feeds:
            return items

        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(headers=headers, verify=False, timeout=20.0) as client:
            tasks = [self._fetch_single(client, f) for f in self.feeds]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    items.extend(r)
        return items

    async def _fetch_single(self, client: httpx.AsyncClient, feed_conf: Dict[str, Any]) -> List[BusinessNewsItem]:
        name = feed_conf.get("name", "RSS")
        url = feed_conf.get("url", "")
        max_items = feed_conf.get("max_items", 8)
        items: List[BusinessNewsItem] = []

        try:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                cutoff = datetime.now() - timedelta(hours=72)

                for e in feed.entries[:max_items]:
                    title = getattr(e, "title", "").strip()
                    link = getattr(e, "link", "").strip()
                    if not title or not link:
                        continue

                    d = datetime.now()
                    if hasattr(e, "published_parsed") and e.published_parsed:
                        try:
                            d = datetime(*e.published_parsed[:6]) + timedelta(hours=8)
                        except Exception:
                            pass

                    if d < cutoff:
                        continue

                    items.append(BusinessNewsItem(
                        title=title,
                        link=link,
                        source=name,
                        date=d
                    ))
        except Exception as e:
            print(f"  ❌ RSS [{name}] 请求失败: {e}")

        return items
