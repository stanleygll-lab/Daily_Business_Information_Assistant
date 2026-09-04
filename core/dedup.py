# -*- coding: utf-8 -*-
"""
Sales & Business Intelligence Deduplication Engine
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from core.models import BusinessNewsItem


class DedupManager:
    """销售商机持久化去重管理器"""

    def __init__(self, log_file: Path or str, expiry_days: int = 7):
        self.log_file = Path(log_file)
        self.expiry_days = expiry_days
        self._log: Dict[str, str] = {}
        self.load()

    @staticmethod
    def get_hash(title: str, source: str) -> str:
        content = f"{title.strip()}|{source.strip()}".lower()
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def load(self) -> Dict[str, str]:
        if not self.log_file.exists():
            self._log = {}
            return self._log
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                self._log = json.load(f)
        except Exception as e:
            print(f"[DedupManager] 读取去重文件异常: {e}")
            self._log = {}
        return self._log

    def save(self) -> None:
        cutoff_time = datetime.now() - timedelta(days=self.expiry_days)
        cleaned_log = {}

        for news_hash, timestamp_str in self._log.items():
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp > cutoff_time:
                    cleaned_log[news_hash] = timestamp_str
            except Exception:
                continue

        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(cleaned_log, f, ensure_ascii=False, indent=2)
            self._log = cleaned_log
        except Exception as e:
            print(f"[DedupManager] 写入去重文件失败: {e}")

    def is_duplicate(self, title: str, source: str) -> bool:
        return self.get_hash(title, source) in self._log

    def add(self, title: str, source: str) -> None:
        self._log[self.get_hash(title, source)] = datetime.now().isoformat()

    def filter_items(self, items: List[BusinessNewsItem]) -> Tuple[List[BusinessNewsItem], int]:
        unique: List[BusinessNewsItem] = []
        dup_count = 0
        for item in items:
            if self.is_duplicate(item.title, item.source):
                dup_count += 1
            else:
                unique.append(item)
                self.add(item.title, item.source)

        self.save()
        return unique, dup_count
