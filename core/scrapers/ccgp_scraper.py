# -*- coding: utf-8 -*-
"""
China Government Procurement Network (CCGP) Scraper
中国政府采购网 (search.ccgp.gov.cn) 招投标与采购意向专项定向抓取器
"""

import asyncio
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote
from playwright.async_api import BrowserContext
from core.models import BusinessNewsItem
from core.scrapers.base import BaseScraper


def parse_ccgp_date(span_text: str) -> Optional[datetime]:
    """解析 CCGP 的时间格式，例如 2026.07.23 10:08:50 或 2026-07-23"""
    if not span_text:
        return None
    m = re.search(r'(20\d{2})[./-](0?[1-9]|1[0-2])[./-](0?[1-9]|[12]\d|3[01])\s+(0?\d|1\d|2[0-3]):(0?\d|[1-5]\d)', span_text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))
    m2 = re.search(r'(20\d{2})[./-](0?[1-9]|1[0-2])[./-](0?[1-9]|[12]\d|3[01])', span_text)
    if m2:
        return datetime(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)), 12, 0)
    return None


class CcgpScraper(BaseScraper):
    """中国政府采购网专项采集器"""

    def __init__(self, context: BrowserContext, keywords: List[str] = None, time_type: int = 1):
        super().__init__(name="CCGP Procurement")
        self.context = context
        self.keywords = keywords or [
            "数字化", "系统集成", "信息化", "云计算", "大数据", "AI大模型", "信创", "软件开发"
        ]
        # timeType=1 表示近3日招采公告，timeType=2 为近1周
        self.time_type = time_type

    async def fetch(self) -> List[BusinessNewsItem]:
        print(f"  🏛️ 启动中国政府采购网 (CCGP) 定向商机挖掘 (共 {len(self.keywords)} 组核心词)...")
        all_items: List[BusinessNewsItem] = []
        page = await self.context.new_page()
        seen_links = set()

        try:
            for kw in self.keywords:
                kw_encoded = quote(kw)
                url = (
                    f"http://search.ccgp.gov.cn/bxsearch?searchtype=1&page_index=1&bidSort=0"
                    f"&buyerName=&projectId=&pinMu=0&bidType=0&dbselect=b_bid&kw={kw_encoded}"
                    f"&start_time=&end_time=&timeType={self.time_type}"
                )
                try:
                    await page.goto(url, timeout=25000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2500)

                    lis = await page.query_selector_all("ul.vT-srch-result-list-bid > li")
                    for li in lis:
                        try:
                            a_el = await li.query_selector("a")
                            span_el = await li.query_selector("span")
                            if not a_el:
                                continue

                            title = (await a_el.inner_text()).strip()
                            if len(title) < 5:
                                continue

                            link = await a_el.get_attribute("href")
                            if not link:
                                continue
                            if link in seen_links:
                                continue
                            seen_links.add(link)

                            span_text = (await span_el.inner_text()).strip() if span_el else ""
                            item_date = parse_ccgp_date(span_text)
                            if not item_date:
                                m_date = re.search(r't(\d{4})(\d{2})(\d{2})_\d+', link)
                                if m_date:
                                    item_date = datetime(int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3)), 12, 0)

                            if not item_date:
                                item_date = datetime.now()

                            buyer = ""
                            m_buyer = re.search(r'采购人：([^\s|]+)', span_text)
                            if m_buyer:
                                buyer = m_buyer.group(1).strip()

                            source_name = f"中国政府采购网({buyer})" if buyer else "中国政府采购网"

                            all_items.append(BusinessNewsItem(
                                title=title,
                                link=link,
                                source=source_name,
                                date=item_date,
                                is_bidding=True
                            ))
                        except Exception:
                            continue
                except Exception as e:
                    print(f"    ⚠️ CCGP 检索关键词 '{kw}' 异常: {e}")
                    continue
        finally:
            await page.close()

        print(f"  ✅ CCGP 政府采购网直接抓取完毕，获取标讯 {len(all_items)} 条")
        return all_items
