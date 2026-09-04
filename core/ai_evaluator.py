# -*- coding: utf-8 -*-
"""
AI Intelligence & Sales Value Evaluator
大模型商机智能研判与商业事实提炼器
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from core.models import BusinessNewsItem

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


async def fetch_article_text(url: str, max_chars: int = 2500) -> str:
    """并发异步提取新闻正文纯文本"""
    if not url or not url.startswith("http"):
        return ""
    try:
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, verify=False, timeout=12.0) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for s in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    s.decompose()
                paragraphs = soup.find_all("p")
                text = "\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 10])
                return text[:max_chars]
    except Exception:
        pass
    return ""


class AiSalesEvaluator:
    """面向销售的大模型商机研判与事实提取器"""

    def __init__(self, ai_config: Dict[str, Any]):
        self.enabled = ai_config.get("enabled", True)
        self.provider = ai_config.get("provider", "gemini").lower()
        self.model = ai_config.get("model", "gemini-2.5-flash-lite")
        self.api_key = ai_config.get("api_key", "")
        self.base_url = ai_config.get("base_url", "")
        self.temperature = ai_config.get("temperature", 0.2)
        self.batch_size = ai_config.get("batch_size", 5)
        self.prompt_template = ai_config.get(
            "prompt",
            "你是一位资深的ToB销售商机分析师。请为以下新闻分别提供一句话商业价值事实摘要（30字以内，重点突出采购主体、项目金额、中标方或核心采购诉求）。请直接输出结果，每行一条，严格遵循格式：序号. 摘要内容"
        )

    def is_available(self) -> bool:
        return bool(self.enabled and self.api_key)

    async def evaluate_items(self, items: List[BusinessNewsItem]) -> List[BusinessNewsItem]:
        """对经过初步筛选的新闻进行 AI 深度正文抽取与商机摘要提炼"""
        if not self.is_available():
            print("  ℹ️ AI 商机评估未启用或未配置 API Key，使用本地规则摘要")
            for item in items:
                if not item.summary:
                    bid_tag = "【重点标讯】" if item.is_bidding else ""
                    item.summary = f"{bid_tag}点击扫码查看该行业商业动态及招标文件"
            return items

        print(f"\n💼 启动大模型商机事实分析 ({self.model}, 共 {len(items)} 条商机)...")

        # 1. 并发抓取文章正文
        fetch_tasks = [fetch_article_text(it.link) for it in items]
        contents = await asyncio.gather(*fetch_tasks)

        # 2. 分批送入大模型
        for i in range(0, len(items), self.batch_size):
            batch_items = items[i:i + self.batch_size]
            batch_contents = contents[i:i + self.batch_size]

            prompt = f"{self.prompt_template}\n\n"
            for idx, (it, ctx) in enumerate(zip(batch_items, batch_contents)):
                text_ctx = ctx if ctx else "（无正文，根据标题提炼）"
                prompt += f"商机 {idx+1}：\n行业分类：{it.industry}\n标题：{it.title}\n内容：{text_ctx[:1500]}\n---\n"

            try:
                summaries = await self._call_llm(prompt, len(batch_items))
                for idx, it in enumerate(batch_items):
                    if idx in summaries:
                        it.summary = summaries[idx]
                    elif not it.summary:
                        it.summary = "（点击右侧二维码直接阅读招采原文）"
            except Exception as e:
                print(f"  ❌ 批次 {i // self.batch_size + 1} 评估异常: {e}")
                for it in batch_items:
                    if not it.summary:
                        it.summary = "（商机事实获取超时，扫码查阅原文）"

            await asyncio.sleep(2)

        return items

    async def _call_llm(self, prompt: str, expected_count: int) -> Dict[int, str]:
        if self.provider == "gemini":
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key)
            async with client.aio as aclient:
                for retry in range(2):
                    try:
                        resp = await aclient.models.generate_content(
                            model=self.model,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                temperature=self.temperature,
                                top_p=0.95,
                                max_output_tokens=1024
                            )
                        )
                        if resp and resp.text:
                            return self._parse_numbered(resp.text, expected_count)
                    except Exception as e:
                        if "429" in str(e):
                            await asyncio.sleep(15)
                        if retry == 1:
                            raise e
            return {}
        else:
            from openai import AsyncOpenAI
            provider_urls = {
                "deepseek": "https://api.deepseek.com/v1",
                "openai": "https://api.openai.com/v1",
                "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "kimi": "https://api.moonshot.cn/v1",
                "ollama": "http://localhost:11434/v1"
            }
            resolved_base_url = self.base_url or provider_urls.get(self.provider)
            client = AsyncOpenAI(api_key=self.api_key, base_url=resolved_base_url)
            resp = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的ToB销售商业情报分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=1024
            )
            content = resp.choices[0].message.content or ""
            return self._parse_numbered(content, expected_count)

    @staticmethod
    def _parse_numbered(text: str, expected_count: int) -> Dict[int, str]:
        result = {}
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.search(r'(?:商机|新闻\s*)?(\d+)[\.、\s:-]+(.*)', line)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < expected_count:
                    result[idx] = m.group(2).strip()
        return result
