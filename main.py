#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Business Information Assistant - CLI Main Entry Point
每日行业商业与销售情报助手 - 命令行总入口
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# 路径与控制台 UTF-8 支持
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from config.settings import ConfigManager
from core.engine import BusinessBriefingEngine
from core.scheduler import DailyScheduler


def parse_args():
    parser = argparse.ArgumentParser(
        description="Daily Business Information Assistant - 行业销售动态与商机挖掘助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                     # 执行一次全量商业招采动态抓取
  python main.py --no-ai             # 不调用大模型，快速生成销售长图
  python main.py --schedule          # 启动每日后台自动定时推送
  python main.py --web -p 8001       # 启动 Web 可视化工作台 (默认端口8001)
        """
    )
    parser.add_argument("-c", "--config", help="自定义配置文件路径 (默认: config/config.yaml)", default=None)
    parser.add_argument("--no-ai", action="store_true", help="禁用 AI 商机研判，仅做矩阵规则过滤")
    parser.add_argument("--schedule", action="store_true", help="启动每日定时常驻调度")
    parser.add_argument("--web", action="store_true", help="启动 Web 可视化控制台")
    parser.add_argument("-p", "--port", type=int, default=8001, help="Web 端口 (默认: 8001)")
    return parser.parse_args()


async def run_cli(args):
    cfg_mgr = ConfigManager(args.config)
    if args.no_ai:
        cfg_mgr.config.setdefault("ai", {})["enabled"] = False

    engine = BusinessBriefingEngine(cfg_mgr)

    if args.schedule:
        daily_time = cfg_mgr.scheduler.get("daily_time", "08:30")
        print(f"⏰ 已启动销售商机每日自动定时模式 (每天 {daily_time} 触发)...")
        print("按 Ctrl+C 可退出。\n")

        async def scheduled_job():
            await engine.run()

        sched = DailyScheduler(daily_time, scheduled_job)
        sched.start()

        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n👋 停止定时调度...")
            sched.stop()
    else:
        await engine.run()


def main():
    args = parse_args()
    if args.web:
        import uvicorn
        from app import app
        print(f"💼 启动商业销售情报 Web 工作台: http://localhost:{args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        try:
            asyncio.run(run_cli(args))
        except KeyboardInterrupt:
            print("\n👋 用户手动终止执行")


if __name__ == "__main__":
    main()
