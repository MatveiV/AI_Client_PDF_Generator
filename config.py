"""
config.py — конфигурация провайдеров и моделей для AI Client PDF Generator.
"""
import os
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {
    "1": {
        "name": "Z.AI",
        "api_key": os.environ.get("ZAI_API_KEY", ""),
        "api_key_env": "ZAI_API_KEY",
        "base_url": "https://api.z.ai/api/paas/v4/",
        "models": {
            "1": {"id": "glm-4.7-flash", "label": "GLM-4.7-Flash", "free": True,  "temp_range": (0.0, 1.0), "max_tokens": 4096},
            "2": {"id": "glm-4.5-flash", "label": "GLM-4.5-Flash", "free": True,  "temp_range": (0.0, 1.0), "max_tokens": 4096},
            "3": {"id": "glm-4.7",       "label": "GLM-4.7",       "free": False, "temp_range": (0.0, 1.0), "max_tokens": 8192},
            "4": {"id": "glm-4.5",       "label": "GLM-4.5",       "free": False, "temp_range": (0.0, 1.0), "max_tokens": 8192},
            "5": {"id": "glm-5",         "label": "GLM-5",         "free": False, "temp_range": (0.0, 1.0), "max_tokens": 8192},
        },
    },
    "2": {
        "name": "ProxyAPI (OpenAI)",
        "api_key": os.environ.get("PROXY_API_KEY", ""),
        "api_key_env": "PROXY_API_KEY",
        "base_url": "https://api.proxyapi.ru/openai/v1",
        "models": {
            "1": {"id": "gpt-4.1-nano",  "label": "GPT-4.1 Nano",  "free": False, "temp_range": (0.0, 2.0), "max_tokens": 32768},
            "2": {"id": "gpt-4.1-mini",  "label": "GPT-4.1 Mini",  "free": False, "temp_range": (0.0, 2.0), "max_tokens": 32768},
            "3": {"id": "gpt-4.1",       "label": "GPT-4.1",       "free": False, "temp_range": (0.0, 2.0), "max_tokens": 32768},
            "4": {"id": "gpt-4o-mini",   "label": "GPT-4o Mini",   "free": False, "temp_range": (0.0, 2.0), "max_tokens": 16384},
            "5": {"id": "gpt-4o",        "label": "GPT-4o",        "free": False, "temp_range": (0.0, 2.0), "max_tokens": 16384},
        },
    },
    "3": {
        "name": "GenAPI",
        "api_key": os.environ.get("GEN_API_KEY", ""),
        "api_key_env": "GEN_API_KEY",
        "base_url": "https://proxy.gen-api.ru/v1",
        "models": {
            "1": {"id": "gpt-4-1-mini",      "label": "GPT-4.1 Mini",      "free": False, "temp_range": (0.0, 2.0), "max_tokens": 32768},
            "2": {"id": "gpt-4-1",           "label": "GPT-4.1",           "free": False, "temp_range": (0.0, 2.0), "max_tokens": 32768},
            "3": {"id": "gpt-4o",            "label": "GPT-4o",            "free": False, "temp_range": (0.0, 2.0), "max_tokens": 16384},
            "4": {"id": "claude-sonnet-4-5", "label": "Claude Sonnet 4.5", "free": False, "temp_range": (0.0, 1.0), "max_tokens": 8192},
            "5": {"id": "gemini-2-5-flash",  "label": "Gemini 2.5 Flash",  "free": False, "temp_range": (0.0, 2.0), "max_tokens": 8192},
            "6": {"id": "deepseek-chat",     "label": "DeepSeek Chat",     "free": False, "temp_range": (0.0, 2.0), "max_tokens": 8192},
            "7": {"id": "deepseek-r1",       "label": "DeepSeek R1",       "free": False, "temp_range": (0.0, 2.0), "max_tokens": 16000},
        },
    },
    "4": {
        "name": "Cerebras",
        "api_key": os.environ.get("CEREBRAS_API_KEY", ""),
        "api_key_env": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "models": {
            "1": {"id": "llama3.1-8b",                        "label": "Llama 3.1 8B",      "free": True, "temp_range": (0.0, 1.5), "max_tokens": 8192},
            "2": {"id": "qwen-3-235b-a22b-instruct-2507",     "label": "Qwen 3 235B MoE",   "free": True, "temp_range": (0.0, 1.5), "max_tokens": 8192},
        },
    },
    "5": {
        "name": "HuggingFace",
        "api_key": os.environ.get("HF_TOKEN", ""),
        "api_key_env": "HF_TOKEN",
        "base_url": "https://router.huggingface.co/v1",
        "models": {
            "1": {"id": "meta-llama/Llama-3.3-70B-Instruct",        "label": "Llama 3.3 70B",       "free": True, "temp_range": (0.0, 2.0), "max_tokens": 8192},
            "2": {"id": "Qwen/Qwen2.5-72B-Instruct",                "label": "Qwen 2.5 72B",        "free": True, "temp_range": (0.0, 2.0), "max_tokens": 8192},
            "3": {"id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", "label": "DeepSeek R1 32B",     "free": True, "temp_range": (0.0, 2.0), "max_tokens": 8192},
        },
    },
}
