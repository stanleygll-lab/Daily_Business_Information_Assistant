# -*- coding: utf-8 -*-
"""
Asynchronous Daily Scheduler for Business Briefings
"""

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional


class DailyScheduler:
    """轻量异步每日定时调度器"""

    def __init__(self, target_time_str: str = "08:30", job_coro: Optional[Callable] = None):
        self.target_time_str = target_time_str
        self.job_coro = job_coro
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    def update_time(self, new_time_str: str):
        self.target_time_str = new_time_str
        if self.is_running:
            self.stop()
            self.start()

    def get_seconds_until_next_run(self) -> float:
        now = datetime.now()
        try:
            target_hour, target_minute = map(int, self.target_time_str.split(":"))
        except Exception:
            target_hour, target_minute = 8, 30

        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target_time <= now:
            target_time += timedelta(days=1)

        return (target_time - now).total_seconds()

    async def _loop(self):
        while self.is_running:
            wait_seconds = self.get_seconds_until_next_run()
            next_run_dt = datetime.now() + timedelta(seconds=wait_seconds)
            print(f"[Scheduler] ⏰ 下一次自动商机采集: {next_run_dt.strftime('%Y-%m-%d %H:%M:%S')} (等待 {int(wait_seconds)} 秒)")

            try:
                await asyncio.sleep(wait_seconds)
                if not self.is_running:
                    break
                print(f"[Scheduler] 🚀 自动商机采集时间到达 ({self.target_time_str})，正在执行...")
                if self.job_coro:
                    await self.job_coro()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Scheduler] ❌ 定时任务执行异常: {e}")
                await asyncio.sleep(60)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
