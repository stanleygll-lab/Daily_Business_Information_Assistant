# -*- coding: utf-8 -*-
"""
Business Briefing Orchestrator Engine
商业情报采集与长图推送主调度引擎
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Callable, Dict, Any
from playwright.async_api import async_playwright
from config.settings import ConfigManager
from core.models import BusinessNewsItem, TaskStatus
from core.filter_engine import MatrixFilterEngine
from core.dedup import DedupManager
from core.ai_evaluator import AiSalesEvaluator
from core.renderer import SalesBriefingRenderer
from core.scrapers.baidu_scraper import BaiduScraper
from core.scrapers.search_scraper import ToutiaoBiddingScraper
from core.scrapers.rss_scraper import BusinessRssScraper
from core.scrapers.ccgp_scraper import CcgpScraper


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class BusinessBriefingEngine:
    """行业商业与销售情报主引擎"""

    def __init__(self, config_manager: ConfigManager):
        self.cfg_mgr = config_manager
        self.status = TaskStatus()
        self._log_listeners: List[Callable[[str], None]] = []

    def add_log_listener(self, listener: Callable[[str], None]):
        self._log_listeners.append(listener)

    def log(self, message: str):
        formatted = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.status.logs.append(formatted)
        if len(self.status.logs) > 500:
            self.status.logs = self.status.logs[-500:]
        print(formatted)
        for listener in self._log_listeners:
            try:
                listener(formatted)
            except Exception:
                pass

    async def run(self) -> Dict[str, Any]:
        if self.status.is_running:
            self.log("⚠️ 当前已有商机采集任务正在执行中...")
            return self.status.to_dict()

        self.status.is_running = True
        self.status.task_id = str(uuid.uuid4())[:8]
        self.status.start_time = datetime.now()
        self.status.error_message = None
        self.log(f"💼 启动商业销售动态情报采集流水线 (任务ID: {self.status.task_id})...")

        cfg = self.cfg_mgr.config
        app_cfg = cfg.get("app", {})
        ind_cfg = cfg.get("industries", {})
        biz_cfg = cfg.get("business_domains", {})
        bid_kws = cfg.get("bidding_keywords", [])
        src_cfg = cfg.get("sources", {})
        ai_cfg = cfg.get("ai", {}).copy()
        ai_cfg["api_key"] = self.cfg_mgr.get_api_key()

        # 1. 实例化核心组件
        matrix_filter = MatrixFilterEngine(ind_cfg, biz_cfg, bid_kws)
        dedup_mgr = DedupManager(self.cfg_mgr.get_dedup_file())
        evaluator = AiSalesEvaluator(ai_cfg)
        renderer = SalesBriefingRenderer(app_cfg, ind_cfg, self.cfg_mgr.get_output_dir())

        raw_items: List[BusinessNewsItem] = []

        try:
            # 2. RSS 抓取
            rss_feeds = src_cfg.get("rss_feeds", [])
            if rss_feeds:
                self.log(f"📡 抓取 {len(rss_feeds)} 个商业与招采 RSS 源...")
                rss_items = await BusinessRssScraper(rss_feeds).fetch()
                self.log(f"✅ RSS 获取到 {len(rss_items)} 条候选数据")
                raw_items.extend(rss_items)

            # 3. 浏览器抓取 (中国政府采购网 + 百度新闻 + 头条招标)
            ccgp_cfg = src_cfg.get("ccgp", {})
            baidu_cfg = src_cfg.get("baidu_news", {})
            toutiao_cfg = src_cfg.get("toutiao_bidding", {})

            if ccgp_cfg.get("enabled", True) or baidu_cfg.get("enabled", True) or toutiao_cfg.get("enabled", True):
                self.log("🌐 启动无头浏览器，进行中国政府采购网、百度新闻与头条商机定向挖掘...")
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(user_agent=USER_AGENT)

                    tasks = []
                    if ccgp_cfg.get("enabled", True):
                        c_kws = ccgp_cfg.get("keywords", [])
                        c_time_type = ccgp_cfg.get("time_type", 1)
                        tasks.append(CcgpScraper(context, keywords=c_kws, time_type=c_time_type).fetch())
                    if baidu_cfg.get("enabled", True):
                        b_queries = baidu_cfg.get("queries", [])
                        tasks.append(BaiduScraper(context, b_queries).fetch())
                    if toutiao_cfg.get("enabled", True):
                        t_queries = toutiao_cfg.get("queries", [])
                        tasks.append(ToutiaoBiddingScraper(context, t_queries).fetch())

                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for res in results:
                        if isinstance(res, list):
                            raw_items.extend(res)

                    await browser.close()
                self.log(f"✅ 政府采购与全网商机挖掘完成，当前全网候选数据 {len(raw_items)} 条")

            self.status.total_found = len(raw_items)

            # 4. 双维矩阵规则筛选 (行业 ∩ 业务)
            self.log("🎯 正在执行【目标行业 × 业务产品】双维矩阵交叉研判...")
            matrix_passed, filtered_count = matrix_filter.filter_items(raw_items)
            self.status.total_filtered = len(matrix_passed)
            self.log(f"✅ 矩阵研判完成：淘汰无关噪音 {filtered_count} 条，入选关键行业商机 {len(matrix_passed)} 条")

            # 5. 去重处理
            self.log("🧹 正在执行销售专版商机去重处理...")
            unique_items, dup_count = dedup_mgr.filter_items(matrix_passed)
            self.status.total_deduped = len(unique_items)
            self.log(f"✅ 去重完成：拦截历史重复 {dup_count} 条，最终入围高价值商机 {len(unique_items)} 条")

            # 6. 大模型商机事实分析
            if evaluator.is_available() and unique_items:
                self.log(f"🤖 正在调用大模型 ({evaluator.model}) 提炼商业招采关键事实...")
                unique_items = await evaluator.evaluate_items(unique_items)
                self.log("✅ AI 商业事实提炼完成")
            else:
                self.log("ℹ️ 跳过 AI 商机提炼 (未启用或无 API Key)")

            # 7. 渲染销售专属长图文
            self.log("🎨 正在渲染销售专版多配色信息流长图文与报告...")
            out_files = renderer.render_all(unique_items)
            self.status.latest_image = out_files.get("image")
            self.status.latest_json = out_files.get("json")
            self.log(f"🎉 销售商机推送生成完毕！长图文件: {out_files.get('image')}")

        except Exception as e:
            err_msg = f"任务执行遇到异常: {e}"
            self.status.error_message = err_msg
            self.log(f"❌ {err_msg}")
        finally:
            self.status.is_running = False
            self.status.end_time = datetime.now()

        return self.status.to_dict()
