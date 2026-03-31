"""
ai_processor.py
"""
import json
import logging
import re
import time

from openai import OpenAI, OpenAIError
from config import PROVIDERS

logger = logging.getLogger(__name__)

_RETRY_PROVIDERS = {"5"}
_MAX_RETRIES = 3
_RETRY_DELAY = 8


def _clean_error(e):
    msg = str(e)
    if "<html" in msg.lower() or "<!doctype" in msg.lower():
        code_match = re.search(r"<h1>(\d+)</h1>", msg)
        text_match = re.search(r"<p>([^<]{1,80})</p>", msg)
        code = code_match.group(1) if code_match else "???"
        text = text_match.group(1).strip() if text_match else "Server error"
        return f"HTTP {code}: {text}"
    return msg


SYSTEM_PROMPT_BASIC = """Ты - аналитик клиентских диалогов.
Проанализируй транскрибацию и верни ТОЛЬКО валидный JSON:
{
  "client_name": "имя клиента или Неизвестно",
  "topic": "тема обращения",
  "main_request": "основной запрос клиента",
  "mood": "настроение клиента (позитивное/нейтральное/негативное/смешанное)",
  "next_steps": "рекомендуемые следующие шаги"
}"""

SYSTEM_PROMPT_PROJECT = """Ты - опытный бизнес-аналитик и менеджер проектов.
Проанализируй транскрибацию диалога между заказчиком и аналитиком-разработчиком.
Верни ТОЛЬКО валидный JSON без пояснений:
{
  "project_name": "название проекта",
  "client_company": "компания заказчика или Физическое лицо",
  "client_representative": "ФИО представителя заказчика",
  "client_position": "должность представителя",
  "analyst_name": "ФИО аналитика-разработчика",
  "topic": "краткая тема проекта",
  "main_request": "основной запрос",
  "key_requirements": ["требование 1", "требование 2"],
  "desired_deadline": "желаемые сроки заказчика",
  "estimated_duration": "оценка времени разработки",
  "budget": "бюджет проекта",
  "tech_stack": "технологический стек",
  "risks": ["риск 1", "риск 2"],
  "client_satisfaction": "удовлетворённость (позитивная/нейтральная/негативная/смешанная)",
  "mood": "настроение заказчика",
  "next_steps": "следующие шаги"
}"""

SYSTEM_PROMPT_DESIGN = """Ты - UX-аналитик и дизайн-консультант.
Проанализируй транскрибацию и извлеки требования к дизайну.
Верни ТОЛЬКО валидный JSON без пояснений:
{
  "project_name": "название проекта",
  "client_company": "компания заказчика",
  "client_representative": "ФИО представителя",
  "client_position": "должность",
  "topic": "тема дизайн-задачи",
  "design_style": "описание желаемого стиля",
  "color_scheme": "цветовая схема",
  "key_screens": ["экран 1", "экран 2"],
  "references": ["референс 1", "референс 2"],
  "target_audience": "целевая аудитория",
  "platform": "веб / мобильное / десктоп",
  "mood": "настроение заказчика",
  "image_prompt": "детальный промпт на английском для генерации концепт-изображения (не более 400 символов)",
  "next_steps": "следующие шаги"
}"""


def _call_ai(messages, provider_key, model_id, temperature, max_tokens):
    provider = PROVIDERS[provider_key]
    client = OpenAI(api_key=provider["api_key"], base_url=provider["base_url"])
    logger.info("AI запрос -> провайдер=%s модель=%s", provider["name"], model_id)

    max_attempts = _MAX_RETRIES if provider_key in _RETRY_PROVIDERS else 1
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=90,
            )
            content = response.choices[0].message.content or ""
            logger.info("AI ответ получен, длина=%d символов", len(content))
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            return content, usage

        except OpenAIError as e:
            clean = _clean_error(e)
            last_error = clean
            if attempt < max_attempts:
                logger.warning("Попытка %d/%d: %s. Повтор через %ds...", attempt, max_attempts, clean, _RETRY_DELAY)
                print(f"  Попытка {attempt}/{max_attempts}: {clean}. Повтор через {_RETRY_DELAY}с...")
                time.sleep(_RETRY_DELAY)
            else:
                logger.error("Ошибка API (все попытки исчерпаны): %s", clean)
                raise OpenAIError(clean) from e


def _extract_json(content):
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if not json_match:
        raise ValueError(f"Не удалось найти JSON в ответе модели:\n{content}")
    return json.loads(json_match.group())


def process_dialog_with_ai(text, provider_key, model_id, temperature, max_tokens, report_type="basic"):
    prompts = {
        "basic":   SYSTEM_PROMPT_BASIC,
        "project": SYSTEM_PROMPT_PROJECT,
        "design":  SYSTEM_PROMPT_DESIGN,
    }
    system_prompt = prompts.get(report_type, SYSTEM_PROMPT_BASIC)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Транскрибация диалога:\n\n{text}"},
    ]
    content, usage = _call_ai(messages, provider_key, model_id, temperature, max_tokens)
    data = _extract_json(content)
    logger.info("Данные извлечены: тип=%s проект=%s", report_type, data.get("project_name", data.get("topic", "-")))
    return data, usage