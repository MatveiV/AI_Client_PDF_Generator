"""
cost_calculator.py — расчёт стоимости запроса в рублях.
Цены в USD за 1M токенов (приблизительные, актуальны на 2025 г.).
"""
import logging

logger = logging.getLogger(__name__)

# Цены USD за 1M токенов: {model_id: (input_price, output_price)}
MODEL_PRICES: dict[str, tuple[float, float]] = {
    # Z.AI GLM
    "glm-4.7-flash":     (0.0,   0.0),    # бесплатно
    "glm-4.5-flash":     (0.0,   0.0),    # бесплатно
    "glm-4.7":           (0.14,  0.14),
    "glm-4.5":           (0.14,  0.14),
    "glm-5":             (1.0,   1.0),
    # ProxyAPI / OpenAI
    "gpt-4.1-nano":      (0.1,   0.4),
    "gpt-4.1-mini":      (0.4,   1.6),
    "gpt-4.1":           (2.0,   8.0),
    "gpt-4o-mini":       (0.15,  0.6),
    "gpt-4o":            (2.5,   10.0),
    # GenAPI
    "gpt-4-1-mini":      (0.4,   1.6),
    "gpt-4-1":           (2.0,   8.0),
    "claude-sonnet-4-5": (3.0,   15.0),
    "gemini-2-5-flash":  (0.15,  0.6),
    "deepseek-chat":     (0.27,  1.1),
    "deepseek-r1":       (0.55,  2.19),
}


def calculate_cost(model_id: str, prompt_tokens: int, completion_tokens: int, usd_rub: float) -> dict:
    """
    Возвращает словарь с деталями стоимости запроса.
    """
    input_price, output_price = MODEL_PRICES.get(model_id, (0.0, 0.0))

    cost_input_usd  = (prompt_tokens     / 1_000_000) * input_price
    cost_output_usd = (completion_tokens / 1_000_000) * output_price
    cost_total_usd  = cost_input_usd + cost_output_usd
    cost_total_rub  = cost_total_usd * usd_rub

    return {
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens":      prompt_tokens + completion_tokens,
        "cost_input_usd":    cost_input_usd,
        "cost_output_usd":   cost_output_usd,
        "cost_total_usd":    cost_total_usd,
        "cost_total_rub":    cost_total_rub,
        "usd_rub_rate":      usd_rub,
    }


def format_cost_line(cost: dict) -> str:
    return (
        f"  Токены: вход {cost['prompt_tokens']} | выход {cost['completion_tokens']} | "
        f"всего {cost['total_tokens']}\n"
        f"  Стоимость: ${cost['cost_total_usd']:.6f} "
        f"≈ {cost['cost_total_rub']:.4f} ₽  (курс ЦБ: {cost['usd_rub_rate']:.2f} ₽/$)"
    )
