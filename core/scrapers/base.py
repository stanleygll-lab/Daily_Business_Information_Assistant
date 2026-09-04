# -*- coding: utf-8 -*-
"""
Scraper Base Class
"""

from abc import ABC, abstractmethod
from typing import List
from core.models import BusinessNewsItem


class BaseScraper(ABC):
    """商业情报抓取器基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def fetch(self) -> List[BusinessNewsItem]:
        pass
