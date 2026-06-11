"""
Agent 配置管理模块
支持：
  - DeepSeek Flash（默认）
  - OpenAI 兼容格式的任意 URL + API Key
"""
import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "llm": {
        "provider": "deepseek",
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.7
    },
    "search": {
        "provider": "duckduckgo",
        "max_results": 10
    },
    "schedule": {
        "auto_refresh_interval_minutes": 3,
        "enabled": True
    },
    "server": {
        "port": 8099,
        "host": "0.0.0.0"
    }
}

class AgentConfig:
    """Agent 配置管理"""

    def __init__(self, config_path=None):
        self.path = Path(config_path) if config_path else (Path(__file__).parent.parent / "config.json")
        self._data = self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 合并默认值
            merged = DEFAULT_CONFIG.copy()
            self._deep_merge(merged, cfg)
            # 环境变量覆盖
            env_key = os.environ.get("LLM_API_KEY", "")
            if env_key:
                merged["llm"]["api_key"] = env_key
            env_url = os.environ.get("LLM_BASE_URL", "")
            if env_url:
                merged["llm"]["base_url"] = env_url
            return merged
        return DEFAULT_CONFIG.copy()

    def _deep_merge(self, base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def save(self):
        """保存配置"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def llm_config(self):
        return self._data["llm"]

    @property
    def api_key(self):
        return self.llm_config["api_key"]

    @property
    def base_url(self):
        return self.llm_config["base_url"]

    @property
    def model(self):
        return self.llm_config["model"]

    @property
    def max_tokens(self):
        return self.llm_config["max_tokens"]

    @property
    def temperature(self):
        return self.llm_config["temperature"]

    @property
    def search_provider(self):
        return self._data["search"]["provider"]

    @property
    def search_max_results(self):
        return self._data["search"]["max_results"]

    @property
    def server_port(self):
        return self._data["server"]["port"]

    @property
    def server_host(self):
        return self._data["server"]["host"]

    @property
    def is_valid(self):
        return bool(self.api_key) and len(self.api_key) > 8

    def to_openai_kwargs(self):
        """返回兼容 openai SDK 的参数"""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "default_headers": {"Content-Type": "application/json"}
        }


# 全局单例
_config = None

def get_config(config_path=None):
    global _config
    if _config is None:
        _config = AgentConfig(config_path)
    return _config
