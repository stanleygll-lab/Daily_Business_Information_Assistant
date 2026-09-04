# -*- coding: utf-8 -*-
"""
Two-Dimensional Matrix Filter & Rules Engine
行业 × 业务 双维矩阵交叉过滤引擎
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from core.models import BusinessNewsItem


class MatrixFilterEngine:
    """双维矩阵过滤器：本地极速研判 (行业词 ∩ 业务词 ∩ 招采商机词)"""

    def __init__(self, industries_cfg: Dict[str, Any], business_cfg: Dict[str, Any], bidding_keywords: List[str]):
        self.industries = industries_cfg
        self.business_domains = business_cfg
        self.bidding_keywords = [k.lower() for k in bidding_keywords]

        # 编译各行业正则
        self.industry_patterns: Dict[str, re.Pattern] = {}
        for ind_key, ind_val in self.industries.items():
            kws = ind_val.get("keywords", [])
            if kws:
                pattern_str = "|".join(re.escape(k) for k in kws)
                self.industry_patterns[ind_key] = re.compile(pattern_str, re.IGNORECASE)

        # 编译各业务领域正则
        self.business_patterns: Dict[str, re.Pattern] = {}
        for biz_key, biz_val in self.business_domains.items():
            kws = biz_val.get("keywords", [])
            if kws:
                pattern_str = "|".join(re.escape(k) for k in kws)
                self.business_patterns[biz_key] = re.compile(pattern_str, re.IGNORECASE)

        # 编译招采特征正则
        b_pattern_str = "|".join(re.escape(k) for k in self.bidding_keywords)
        self.bidding_pattern = re.compile(b_pattern_str, re.IGNORECASE)

    def evaluate_news(self, title: str, content: str = "") -> Tuple[bool, Optional[str], Optional[str], bool]:
        """
        评估新闻是否吻合双维商机矩阵
        :return: (is_relevant, matched_industry, matched_business, is_bidding)
        """
        full_text = f"{title} {content}".lower()

        # 1. 匹配目标行业
        matched_ind = None
        max_ind_score = 0
        for ind_key, pattern in self.industry_patterns.items():
            matches = pattern.findall(full_text)
            if len(matches) > max_ind_score:
                max_ind_score = len(matches)
                matched_ind = ind_key

        if not matched_ind:
            return False, None, None, False

        # 2. 匹配业务产品能力
        matched_biz = None
        max_biz_score = 0
        for biz_key, pattern in self.business_patterns.items():
            matches = pattern.findall(full_text)
            if len(matches) > max_biz_score:
                max_biz_score = len(matches)
                matched_biz = biz_key

        if not matched_biz:
            return False, None, None, False

        # 3. 检测是否包含招采大单动作词
        is_bidding = bool(self.bidding_pattern.search(full_text))

        # 只要同时击中行业与业务，即判定为强相关销售商机
        return True, matched_ind, matched_biz, is_bidding

    def filter_items(self, items: List[BusinessNewsItem]) -> Tuple[List[BusinessNewsItem], int]:
        """批量执行双维矩阵过滤"""
        relevant_items: List[BusinessNewsItem] = []
        filtered_count = 0

        for item in items:
            is_rel, ind, biz, is_bid = self.evaluate_news(item.title, item.content or "")
            if is_rel:
                item.industry = ind or item.industry
                item.business = biz or item.business
                item.is_bidding = is_bid
                item.is_relevant = True
                relevant_items.append(item)
            else:
                filtered_count += 1

        return relevant_items, filtered_count
