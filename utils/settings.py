"""
settings.py — сохранение и загрузка пользовательских настроек.
"""
import json
import logging
import os
import sys

from config import PROVIDERS

logger = logging.getLogger(__name__)
SETTINGS_FILE = "pdf_generator_settings.json"


def sep(char: str = "─", width: int = 60) -> None:
    print(char * width)


def ask(prompt: str, default: str = "") -> str:
    try:
        val = input(prompt).strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print("\n  Прервано пользователем.")
        import sys; sys.exit(0)


def get_float(prompt: str, default: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(ask(prompt, str(default)))))
    except ValueError:
        return default


def pick_settings() -> dict:
    """Интерактивный выбор провайдера, модели, температуры и токенов."""
    sep("═")
    print("  НАСТРОЙКИ AI Client PDF Generator")
    sep("═")
    print("  ВЫБОР ПРОВАЙДЕРА:")
    for key, p in PROVIDERS.items():
        print(f"    {key}. {p['name']}")

    p_key = ask("\n  Провайдер [1]: ", "1")
    if p_key not in PROVIDERS:
        p_key = "1"
    provider = PROVIDERS[p_key]

    if not provider["api_key"]:
        print(f"\n  Ошибка: {provider['api_key_env']} не найден в .env")
        sys.exit(1)

    sep()
    print(f"  МОДЕЛИ — {provider['name']}:")
    print(f"  {'#':<4} {'Модель':<25} {'Бесплатно':<12} Макс. токенов")
    sep()
    for key, m in provider["models"].items():
        print(f"  {key:<4} {m['label']:<25} {'да' if m['free'] else 'нет':<12} {m['max_tokens']}")

    m_key = ask("\n  Модель [1]: ", "1")
    if m_key not in provider["models"]:
        m_key = "1"
    model = provider["models"][m_key]

    lo, hi = model["temp_range"]
    temperature = get_float(f"\n  Температура ({lo}–{hi}, по умолчанию 0.7): ", 0.7, lo, hi)

    max_tokens = int(get_float(
        f"  Макс. токенов (1–{model['max_tokens']}, по умолчанию 1024): ",
        1024, 1, model["max_tokens"]
    ))

    settings = {
        "provider_key": p_key,
        "model_key": m_key,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    save_settings(settings)
    return settings


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    logger.info("Настройки сохранены в %s", SETTINGS_FILE)


def load_settings() -> dict | None:
    if not os.path.exists(SETTINGS_FILE):
        return None
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Не удалось загрузить настройки: %s", e)
        return None


def get_active_config(settings: dict) -> tuple[str, dict, str, float, int]:
    """Возвращает (provider_key, provider, model_id, temperature, max_tokens)."""
    p_key = settings["provider_key"]
    m_key = settings["model_key"]
    provider = PROVIDERS[p_key]
    # Если сохранённый ключ модели больше не существует — берём первую доступную
    if m_key not in provider["models"]:
        m_key = next(iter(provider["models"]))
        logger.warning("Модель '%s' не найдена у провайдера %s, используется '%s'",
                       settings["model_key"], provider["name"], m_key)
    model = provider["models"][m_key]
    return p_key, provider, model["id"], settings["temperature"], settings["max_tokens"]
