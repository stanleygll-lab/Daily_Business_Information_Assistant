# -*- coding: utf-8 -*-
"""
Business Intelligence Data Models
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class BusinessNewsItem:
    """商业与销售情报数据模型"""
    title: str
    link: str
    source: str
    date: datetime
    industry: str = "OTHER"       # 归属行业 (如 MEDICAL, EDUCATION, TRAFFIC, MILITARY, TELECOM)
    business: str = "OTHER"       # 归属业务 (如 SECURITY, DATA_ASSET, AI_INTELLIGENCE, CYBER_RANGE)
    summary: Optional[str] = None # 商业价值与事实摘要
    is_bidding: bool = False      # 是否为明确招标/中标大单
    is_relevant: bool = True      # 是否属于高价值商机
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(self.date, datetime) else str(self.date),
            "industry": self.industry,
            "business": self.business,
            "summary": self.summary or "",
            "is_bidding": self.is_bidding,
            "is_relevant": self.is_relevant,
            "extra": self.extra
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BusinessNewsItem":
        d = data.get("date")
        if isinstance(d, str):
            try:
                date_val = datetime.fromisoformat(d)
            except Exception:
                date_val = datetime.now()
        elif isinstance(d, datetime):
            date_val = d
        else:
            date_val = datetime.now()

        return cls(
            title=data.get("title", ""),
            link=data.get("link", ""),
            source=data.get("source", ""),
            date=date_val,
            industry=data.get("industry", "OTHER"),
            business=data.get("business", "OTHER"),
            summary=data.get("summary"),
            is_bidding=data.get("is_bidding", False),
            is_relevant=data.get("is_relevant", True),
            extra=data.get("extra", {})
        )


@dataclass
class TaskStatus:
    """商业情报采集任务执行状态模型"""
    is_running: bool = False
    task_id: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_found: int = 0
    total_filtered: int = 0
    total_deduped: int = 0
    latest_image: Optional[str] = None
    latest_json: Optional[str] = None
    error_message: Optional[str] = None
    logs: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_found": self.total_found,
            "total_filtered": self.total_filtered,
            "total_deduped": self.total_deduped,
            "latest_image": self.latest_image,
            "latest_json": self.latest_json,
            "error_message": self.error_message,
            "log_count": len(self.logs)
        }
