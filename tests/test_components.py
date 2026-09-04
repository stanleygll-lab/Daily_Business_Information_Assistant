# -*- coding: utf-8 -*-
"""
Automated Test Suite for Daily Business Information Assistant
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from config.settings import ConfigManager
from core.models import BusinessNewsItem
from core.filter_engine import MatrixFilterEngine
from core.dedup import DedupManager
from core.renderer import SalesBriefingRenderer


def test_config_manager():
    print("Testing ConfigManager...")
    cfg = ConfigManager()
    assert "industries" in cfg.config
    assert "business_domains" in cfg.config
    assert "bidding_keywords" in cfg.config
    assert "MEDICAL" in cfg.industries
    assert "SECURITY" in cfg.business_domains
    print("  ✅ ConfigManager passed!")


def test_matrix_filter():
    print("Testing MatrixFilterEngine (Two-Dimensional Matrix)...")
    cfg = ConfigManager()
    filter_engine = MatrixFilterEngine(
        cfg.industries,
        cfg.business_domains,
        cfg.bidding_keywords
    )

    # 1. 医疗 + 数据安全 + 中标 (符合两维 + 标讯)
    ok1, ind1, biz1, is_bid1 = filter_engine.evaluate_news(
        "某省人民医院数据安全分级分类与防护系统建设项目中标结果公告"
    )
    assert ok1 is True, "Should match both industry and business"
    assert ind1 == "MEDICAL", f"Expected MEDICAL, got {ind1}"
    assert is_bid1 is True, "Should flag as bidding"

    # 2. 高校 + AI/靶场实训 + 招标 (符合两维)
    ok2, ind2, biz2, is_bid2 = filter_engine.evaluate_news(
        "某大学人工智能网络攻防实训靶场平台采购意向公示"
    )
    assert ok2 is True
    assert ind2 == "EDUCATION"
    assert is_bid2 is True

    # 3. 仅有行业，无安全/AI/数据业务 -> 必须排除
    ok3, _, _, _ = filter_engine.evaluate_news(
        "某市第一人民医院新院区建设项目主体工程封顶"
    )
    assert ok3 is False, "Should reject news without business domain"

    # 4. 仅有安全，无目标行业 -> 必须排除
    ok4, _, _, _ = filter_engine.evaluate_news(
        "Chrome浏览器紧急修复高危远程代码执行漏洞"
    )
    assert ok4 is False, "Should reject news without target industry"

    print("  ✅ MatrixFilterEngine passed all 4 cases!")


def test_dedup_manager():
    print("Testing DedupManager...")
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test_dedup_sales.json"
        dedup = DedupManager(log_file)

        items = [
            BusinessNewsItem(title="项目A中标公告", link="https://1", source="招标网", date=datetime.now()),
            BusinessNewsItem(title="项目A中标公告", link="https://1", source="招标网", date=datetime.now()), # 重复
            BusinessNewsItem(title="项目B中标公告", link="https://2", source="采购网", date=datetime.now()),
        ]

        unique, dup_count = dedup.filter_items(items)
        assert len(unique) == 2
        assert dup_count == 1
    print("  ✅ DedupManager passed!")


def test_renderer():
    print("Testing SalesBriefingRenderer...")
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "output"
        app_cfg = {"title": "📰 行业销售动态测试", "creator": "测试助手", "image_width": 1000}
        cfg = ConfigManager()
        renderer = SalesBriefingRenderer(app_cfg, cfg.industries, out_dir)

        test_items = [
            BusinessNewsItem(
                title="某三甲医院数据要素流通与数据安全保护体系重大采购项目中标结果公告",
                link="https://example.com/med1",
                source="政府采购网",
                date=datetime.now(),
                industry="MEDICAL",
                business="SECURITY",
                is_bidding=True,
                summary="某三甲医院投资1200万元建设数据安全平台，知名厂商全包入围。"
            ),
            BusinessNewsItem(
                title="某高校国家级网络安全靶场与教学实训系统建设项目",
                link="https://example.com/edu1",
                source="高校招标网",
                date=datetime.now(),
                industry="EDUCATION",
                business="CYBER_RANGE",
                is_bidding=True,
                summary="某高校采购多模态教学实训系统，赋能网络空间学科建设。"
            )
        ]

        res = renderer.render_all(test_items)
        assert Path(res["json"]).exists()
        assert Path(res["markdown"]).exists()
        assert Path(res["image"]).exists()
        assert Path(res["image"]).stat().st_size > 5000
    print("  ✅ SalesBriefingRenderer passed!")


if __name__ == "__main__":
    test_config_manager()
    test_matrix_filter()
    test_dedup_manager()
    test_renderer()
    print("\n🎉 ALL SALES ASSISTANT TESTS PASSED!")
