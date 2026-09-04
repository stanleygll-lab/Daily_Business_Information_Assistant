# -*- coding: utf-8 -*-
"""
Daily Business Information Assistant - Settings Manager
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config" / "config.example.yaml"


class ConfigManager:
    """商业与销售情报配置中心管理器"""

    def __init__(self, config_path: Optional[str or Path] = None):
        if config_path:
            self.config_file = Path(config_path)
        elif DEFAULT_CONFIG_PATH.exists():
            self.config_file = DEFAULT_CONFIG_PATH
        elif EXAMPLE_CONFIG_PATH.exists():
            self.config_file = EXAMPLE_CONFIG_PATH
        else:
            self.config_file = DEFAULT_CONFIG_PATH

        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """从 YAML 加载并注入环境变量"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[ConfigManager] 读取配置文件异常: {e}")
                self._config = {}
        else:
            self._config = {}

        ai_cfg = self._config.setdefault("ai", {})
        env_gemini_key = os.environ.get("GEMINI_API_KEY")
        if env_gemini_key and not ai_cfg.get("api_key"):
            ai_cfg["api_key"] = env_gemini_key

        env_openai_key = os.environ.get("OPENAI_API_KEY")
        if env_openai_key:
            ai_cfg["openai_api_key"] = env_openai_key

        env_openai_base = os.environ.get("OPENAI_BASE_URL")
        if env_openai_base:
            ai_cfg["base_url"] = env_openai_base

        return self._config

    def save(self, new_config: Optional[Dict[str, Any]] = None) -> bool:
        """持久化保存新配置到 config.yaml"""
        if new_config is not None:
            self._config = new_config

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, allow_unicode=True, sort_keys=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] 保存配置文件失败: {e}")
            return False

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def app(self) -> Dict[str, Any]:
        return self._config.get("app", {})

    @property
    def industries(self) -> Dict[str, Any]:
        return self._config.get("industries", {})

    @property
    def business_domains(self) -> Dict[str, Any]:
        return self._config.get("business_domains", {})

    @property
    def bidding_keywords(self) -> list:
        return self._config.get("bidding_keywords", [])

    @property
    def sources(self) -> Dict[str, Any]:
        return self._config.get("sources", {})

    @property
    def ai(self) -> Dict[str, Any]:
        return self._config.get("ai", {})

    @property
    def scheduler(self) -> Dict[str, Any]:
        return self._config.get("scheduler", {})

    @property
    def dedup(self) -> Dict[str, Any]:
        return self._config.get("dedup", {})

    def get_api_key(self) -> str:
        ai_cfg = self.ai
        provider = ai_cfg.get("provider", "gemini")
        if provider == "gemini":
            return os.environ.get("GEMINI_API_KEY") or ai_cfg.get("api_key", "")
        else:
            return os.environ.get("OPENAI_API_KEY") or ai_cfg.get("api_key", "")

    def get_output_dir(self) -> Path:
        raw_dir = self.app.get("output_dir", "./output")
        p = Path(raw_dir)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_dedup_file(self) -> Path:
        raw_file = self.dedup.get("log_file", "./data/news_dedup_log_sales.json")
        p = Path(raw_file)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


settings = ConfigManager()
