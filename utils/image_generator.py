"""
image_generator.py — генерация UI-прототипов и изображений через AI-провайдеров.

Поддерживаемые бэкенды:
  - Together.ai  : FLUX.1 [schnell] — бесплатно (8000+ изображений/день без карты)
                   FLUX.1 [dev]     — платно, высокое качество
  - ProxyAPI     : DALL-E 3 / DALL-E 2 — платно через OpenAI-совместимый прокси
"""
import base64
import logging
import os
from pathlib import Path

import requests
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv

load_dotenv()

from config import PROVIDERS

logger = logging.getLogger(__name__)

IMAGES_DIR = Path(__file__).parent.parent / "reports" / "images"

# ─── Конфигурация бэкендов генерации изображений ─────────────────────────────

IMAGE_BACKENDS = {
    "1": {
        "name": "Pollinations.ai — FLUX (БЕСПЛАТНО, без ключа)",
        "backend": "pollinations",
        "model": "flux",
        "free": True,
        "max_count": 4,
        "aspect_ratios": ["1:1", "16:9", "4:3", "3:2"],
        "default_ratio": "16:9",
        "note": "Полностью бесплатно, без регистрации и API-ключа",
    },
    "2": {
        "name": "Together.ai — FLUX.1 [schnell] (платно, $0.003/изображение)",
        "backend": "together",
        "model": "black-forest-labs/FLUX.1-schnell",
        "free": False,
        "max_count": 4,
        "aspect_ratios": ["1:1", "16:9", "4:3", "3:2"],
        "default_ratio": "16:9",
        "steps_range": (1, 4),
        "default_steps": 4,
        "note": "Требует TOGETHER_API_KEY и баланс на api.together.ai",
    },
    "3": {
        "name": "Together.ai — FLUX.1 [dev] (платно, $0.025/изображение)",
        "backend": "together",
        "model": "black-forest-labs/FLUX.1-dev",
        "free": False,
        "max_count": 4,
        "aspect_ratios": ["1:1", "16:9", "4:3", "3:2"],
        "default_ratio": "16:9",
        "steps_range": (10, 50),
        "default_steps": 28,
        "note": "Фотореалистичное качество, требует TOGETHER_API_KEY",
    },
    "4": {
        "name": "ProxyAPI — DALL-E 3 (платно)",
        "backend": "dalle",
        "provider_key": "2",
        "model": "dall-e-3",
        "free": False,
        "max_count": 4,
        "sizes": ["1024x1024", "1792x1024", "1024x1792"],
        "default_size": "1792x1024",
        "qualities": ["standard", "hd"],
        "note": "Требует PROXY_API_KEY и баланс",
    },
}

# UI-специфичный суффикс промпта для лучших результатов
UI_PROMPT_SUFFIX = (
    ", clean UI design, modern web interface mockup, high fidelity wireframe, "
    "professional layout, crisp typography, flat design, light background, "
    "desktop browser screenshot, 4K quality"
)


# ─── Pollinations.ai backend (бесплатно, без ключа) ──────────────────────────

def _generate_pollinations(
    prompt: str,
    count: int,
    aspect_ratio: str,
    report_prefix: str,
) -> list[str]:
    """Генерация через Pollinations.ai — полностью бесплатно, без API-ключа."""
    ratio_map = {
        "1:1":  (1024, 1024),
        "16:9": (1344, 768),
        "4:3":  (1152, 896),
        "3:2":  (1216, 832),
    }
    width, height = ratio_map.get(aspect_ratio, (1344, 768))
    enhanced_prompt = prompt + UI_PROMPT_SUFFIX
    saved_paths: list[str] = []

    import urllib.parse
    encoded = urllib.parse.quote(enhanced_prompt)

    for i in range(count):
        url = f"https://image.pollinations.ai/prompt/{encoded}"
        params = {
            "width": width,
            "height": height,
            "model": "flux",
            "nologo": "true",
            "seed": i * 42,  # разные seed для вариаций
        }
        logger.info("Pollinations.ai запрос %d/%d: %dx%d", i + 1, count, width, height)

        resp = requests.get(url, params=params, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"Pollinations.ai HTTP {resp.status_code}: {resp.text[:200]}")

        ext = "jpg" if resp.headers.get("content-type", "").startswith("image/jpeg") else "png"
        filename = f"{report_prefix}_img_{i + 1}.{ext}"
        filepath = IMAGES_DIR / filename

        with open(filepath, "wb") as f:
            f.write(resp.content)

        saved_paths.append(str(filepath))
        logger.info("Изображение сохранено: %s", filepath)

    return saved_paths


# ─── Together.ai backend ──────────────────────────────────────────────────────

def _generate_together(
    prompt: str,
    model: str,
    count: int,
    aspect_ratio: str,
    steps: int,
    report_prefix: str,
) -> list[str]:
    """Генерация через Together.ai REST API."""
    api_key = os.environ.get("TOGETHER_API_KEY", "")
    if not api_key:
        raise ValueError(
            "TOGETHER_API_KEY не найден в .env. "
            "Получите бесплатный ключ на https://api.together.ai/settings/api-keys"
        )

    # Конвертируем aspect_ratio в width/height (FLUX.1 schnell/dev используют width+height)
    ratio_map = {
        "1:1":  (1024, 1024),
        "16:9": (1344, 768),
        "4:3":  (1152, 896),
        "3:2":  (1216, 832),
    }
    width, height = ratio_map.get(aspect_ratio, (1344, 768))

    enhanced_prompt = prompt + UI_PROMPT_SUFFIX
    saved_paths: list[str] = []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for i in range(count):
        payload = {
            "model": model,
            "prompt": enhanced_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "n": 1,
            "response_format": "b64_json",
        }

        logger.info("Together.ai запрос %d/%d: модель=%s %dx%d steps=%d",
                    i + 1, count, model, width, height, steps)

        resp = requests.post(
            "https://api.together.ai/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=120,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Together.ai HTTP {resp.status_code}: {resp.text[:300]}")

        result = resp.json()
        img_data = result["data"][0]

        filename = f"{report_prefix}_img_{i + 1}.png"
        filepath = IMAGES_DIR / filename

        if img_data.get("b64_json"):
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(img_data["b64_json"]))
        elif img_data.get("url"):
            r = requests.get(img_data["url"], timeout=60)
            r.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(r.content)
        else:
            logger.warning("Together.ai: изображение %d без данных", i + 1)
            continue

        saved_paths.append(str(filepath))
        logger.info("Изображение сохранено: %s", filepath)

    return saved_paths


# ─── DALL-E backend ───────────────────────────────────────────────────────────

def _generate_dalle(
    prompt: str,
    provider_key: str,
    model: str,
    count: int,
    size: str,
    quality: str,
    report_prefix: str,
) -> list[str]:
    """Генерация через DALL-E (OpenAI-совместимый API)."""
    provider = PROVIDERS[provider_key]
    client = OpenAI(api_key=provider["api_key"], base_url=provider["base_url"])

    saved_paths: list[str] = []

    for i in range(count):
        kwargs = dict(model=model, prompt=prompt, n=1, size=size, response_format="b64_json")
        if model == "dall-e-3":
            kwargs["quality"] = quality

        try:
            response = client.images.generate(**kwargs)
        except OpenAIError as e:
            logger.error("DALL-E ошибка %d: %s", i + 1, e)
            raise

        img_data = response.data[0]
        filename = f"{report_prefix}_img_{i + 1}.png"
        filepath = IMAGES_DIR / filename

        if img_data.b64_json:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(img_data.b64_json))
        elif img_data.url:
            r = requests.get(img_data.url, timeout=60)
            r.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(r.content)
        else:
            logger.warning("DALL-E: изображение %d без данных", i + 1)
            continue

        saved_paths.append(str(filepath))
        logger.info("Изображение сохранено: %s", filepath)

    return saved_paths


# ─── Публичный интерфейс ──────────────────────────────────────────────────────

def generate_images(
    prompt: str,
    backend_key: str = "1",
    count: int = 1,
    report_prefix: str = "design",
    # Together.ai параметры
    aspect_ratio: str = "16:9",
    steps: int = 4,
    # DALL-E параметры
    size: str = "1792x1024",
    quality: str = "standard",
) -> list[str]:
    """
    Единая точка входа для генерации изображений.
    backend_key: ключ из IMAGE_BACKENDS.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    backend = IMAGE_BACKENDS[backend_key]

    logger.info("Генерация %d изображений: бэкенд=%s", count, backend["name"])

    if backend["backend"] == "pollinations":
        return _generate_pollinations(
            prompt=prompt,
            count=count,
            aspect_ratio=aspect_ratio,
            report_prefix=report_prefix,
        )
    elif backend["backend"] == "together":
        return _generate_together(
            prompt=prompt,
            model=backend["model"],
            count=count,
            aspect_ratio=aspect_ratio,
            steps=steps,
            report_prefix=report_prefix,
        )
    else:
        return _generate_dalle(
            prompt=prompt,
            provider_key=backend["provider_key"],
            model=backend["model"],
            count=count,
            size=size,
            quality=quality,
            report_prefix=report_prefix,
        )


def pick_image_settings() -> dict:
    """Интерактивный выбор параметров генерации изображений."""
    from utils.settings import ask, sep

    sep()
    print("  НАСТРОЙКИ ГЕНЕРАЦИИ UI-ПРОТОТИПА")
    sep()
    print("  Выберите провайдер генерации изображений:\n")
    for key, b in IMAGE_BACKENDS.items():
        free_tag = "  [БЕСПЛАТНО]" if b["free"] else ""
        print(f"  {key}. {b['name']}{free_tag}")
        print(f"     {b['note']}")
    print()

    b_choice = ask("  Провайдер [1]: ", "1")
    if b_choice not in IMAGE_BACKENDS:
        b_choice = "1"
    backend = IMAGE_BACKENDS[b_choice]

    print(f"\n  Количество изображений (1–{backend['max_count']}):")
    try:
        count = max(1, min(backend["max_count"], int(ask(f"  Количество [1]: ", "1"))))
    except ValueError:
        count = 1

    settings = {"backend_key": b_choice, "count": count}

    if backend["backend"] in ("together", "pollinations"):
        ratios = backend["aspect_ratios"]
        default_r = backend["default_ratio"]
        default_idx = str(ratios.index(default_r) + 1)
        print("\n  Соотношение сторон:")
        for i, r in enumerate(ratios, 1):
            note = " (рекомендуется для веб)" if r == "16:9" else ""
            print(f"  {i}. {r}{note}")
        r_choice = ask(f"  Соотношение [{default_idx}]: ", default_idx)
        try:
            aspect_ratio = ratios[int(r_choice) - 1]
        except (ValueError, IndexError):
            aspect_ratio = default_r

        steps = backend.get("default_steps", 4)
        if backend["backend"] == "together":
            lo, hi = backend["steps_range"]
            steps = int(get_int_input(
                f"  Шаги генерации ({lo}–{hi}, больше = лучше качество): ",
                backend["default_steps"], lo, hi
            ))
        settings.update({"aspect_ratio": aspect_ratio, "steps": steps})

    else:  # DALL-E
        sizes = backend["sizes"]
        default_size = backend["default_size"]
        default_idx = str(sizes.index(default_size) + 1)
        print("\n  Размер изображения:")
        for i, s in enumerate(sizes, 1):
            print(f"  {i}. {s}")
        s_choice = ask(f"  Размер [{default_idx}]: ", default_idx)
        try:
            size = sizes[int(s_choice) - 1]
        except (ValueError, IndexError):
            size = default_size

        quality = "standard"
        if backend["model"] == "dall-e-3":
            print("\n  Качество:")
            print("  1. standard")
            print("  2. hd")
            quality = "hd" if ask("  Качество [1]: ", "1") == "2" else "standard"

        settings.update({"size": size, "quality": quality})

    return settings


def get_int_input(prompt: str, default: int, lo: int, hi: int) -> int:
    from utils.settings import ask
    try:
        return max(lo, min(hi, int(ask(prompt, str(default)))))
    except ValueError:
        return default


def generate_image_prompt(
    dialog_text: str,
    provider_key: str,
    model_id: str,
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict]:
    """Использует LLM для генерации UI-промпта из транскрибации диалога."""
    provider = PROVIDERS[provider_key]
    client = OpenAI(api_key=provider["api_key"], base_url=provider["base_url"])

    system = (
        "Ты — дизайнер UI/UX. На основе описания проекта из диалога создай "
        "детальный промпт на английском языке для генерации изображения-концепта "
        "дизайна веб-страницы или интерфейса. Промпт должен описывать визуальный стиль, "
        "цветовую схему, ключевые элементы интерфейса, настроение. "
        "Верни ТОЛЬКО текст промпта, без пояснений, не более 400 символов."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Диалог:\n\n{dialog_text}"},
    ]

    logger.info("Генерация промпта изображения через %s / %s", provider["name"], model_id)

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        max_tokens=min(max_tokens, 512),
    )

    prompt = (response.choices[0].message.content or "").strip()
    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    logger.info("Промпт изображения: %s", prompt[:80])
    return prompt, usage
