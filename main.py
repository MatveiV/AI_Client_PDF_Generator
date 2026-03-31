"""
main.py — AI Client PDF Generator
Автоматически формирует PDF-отчёты по диалогам с клиентами через ИИ.

Запуск:
  python main.py                          — интерактивный режим
  python main.py examples/dialog.txt      — сразу загрузить файл транскрибации
"""
import logging
import os
import sys
from pathlib import Path

# Подавляем системный шум от GTK/GLib на Windows (WeasyPrint)
os.environ.setdefault("G_MESSAGES_DEBUG", "none")
os.environ.setdefault("GLIB_SILENCE_DEPRECATION_WARNINGS", "1")

from dotenv import load_dotenv

load_dotenv()

# ─── Логирование ──────────────────────────────────────────────────────────────

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ─── Импорты модулей проекта ──────────────────────────────────────────────────

from utils.settings import pick_settings, load_settings, get_active_config, sep, ask
from utils.ai_processor import process_dialog_with_ai
from utils.pdf_generator import generate_pdf
from utils.cbr_rate import get_usd_rub_rate
from utils.cost_calculator import calculate_cost, format_cost_line


# ─── Выбор типа отчёта ────────────────────────────────────────────────────────

REPORT_TYPES = {
    "1": ("basic",   "Базовый отчёт по диалогу"),
    "2": ("project", "Расширенный отчёт по проекту (сроки, бюджет, риски, требования)"),
    "3": ("design",  "Дизайн-отчёт с генерацией концепт-изображения"),
}


def pick_report_type() -> str:
    sep()
    print("  ТИП ОТЧЁТА")
    sep()
    for key, (_, label) in REPORT_TYPES.items():
        print(f"  {key}. {label}")
    choice = ask("\n  Выбор [2]: ", "2")
    return REPORT_TYPES.get(choice, REPORT_TYPES["2"])[0]


# ─── Ввод транскрибации ───────────────────────────────────────────────────────

def get_transcript(file_arg: str | None = None) -> str:
    """Возвращает текст транскрибации из файла (аргумент CLI или выбор) или ручного ввода."""
    if file_arg:
        if not os.path.exists(file_arg):
            print(f"  Файл не найден: {file_arg}")
            sys.exit(1)
        with open(file_arg, encoding="utf-8") as f:
            text = f.read().strip()
        logger.info("Транскрибация загружена из аргумента CLI: %s (%d символов)", file_arg, len(text))
        return text

    sep()
    print("  ИСТОЧНИК ТРАНСКРИБАЦИИ")
    sep()
    print("  1. Ввести текст вручную")
    print("  2. Загрузить из файла")
    print("  3. Использовать пример (examples/)")
    choice = ask("\n  Выбор [2]: ", "2")

    if choice == "3":
        examples = list(Path("examples").glob("*.txt")) if Path("examples").exists() else []
        if not examples:
            print("  Примеры не найдены в папке examples/")
            sys.exit(1)
        print("\n  Доступные примеры:")
        for i, p in enumerate(examples, 1):
            print(f"  {i}. {p.name}")
        idx = ask(f"\n  Выбор [1]: ", "1")
        try:
            path = examples[int(idx) - 1]
        except (ValueError, IndexError):
            path = examples[0]
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        logger.info("Пример загружен: %s (%d символов)", path, len(text))
        return text

    if choice == "2":
        path_str = ask("  Путь к файлу: ").strip()
        if not os.path.exists(path_str):
            print(f"  Файл не найден: {path_str}")
            sys.exit(1)
        with open(path_str, encoding="utf-8") as f:
            text = f.read().strip()
        logger.info("Транскрибация загружена из файла: %s (%d символов)", path_str, len(text))
        return text

    # Ручной ввод
    print("  Введите текст диалога (завершите двумя пустыми строками подряд):")
    lines: list[str] = []
    empty_count = 0
    while True:
        line = input()
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
        else:
            empty_count = 0
        lines.append(line)
    text = "\n".join(lines).strip()
    logger.info("Транскрибация введена вручную (%d символов)", len(text))
    return text


# ─── Генерация изображений для дизайн-отчёта ─────────────────────────────────

def run_image_generation(
    data: dict,
    transcript: str,
    p_key: str,
    model_id: str,
    temperature: float,
    max_tokens: int,
    usd_rub: float,
) -> tuple[list[str], float]:
    """
    Генерирует изображения для дизайн-отчёта.
    Возвращает (список путей к изображениям, суммарная стоимость в рублях).
    """
    from utils.image_generator import generate_images, pick_image_settings

    total_cost_rub = 0.0

    image_prompt = data.get("image_prompt", "").strip()
    if not image_prompt:
        print("  AI не сформировал промпт изображения, используем тему проекта.")
        image_prompt = (
            f"Modern UI/UX design concept for {data.get('project_name', 'web application')}, "
            f"{data.get('design_style', 'clean minimal')}, "
            f"{data.get('platform', 'web')}, professional, high quality mockup"
        )

    sep()
    print(f"  Промпт для генерации изображения:\n  {image_prompt[:120]}...")

    img_settings = pick_image_settings()

    sep()
    print(f"  Генерация {img_settings['count']} изображений...")

    from datetime import datetime
    prefix = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        image_paths = generate_images(
            prompt=image_prompt,
            backend_key=img_settings["backend_key"],
            count=img_settings["count"],
            report_prefix=prefix,
            aspect_ratio=img_settings.get("aspect_ratio", "16:9"),
            steps=img_settings.get("steps", 4),
            size=img_settings.get("size", "1792x1024"),
            quality=img_settings.get("quality", "standard"),
        )
        print(f"  Сгенерировано изображений: {len(image_paths)}")
        for p in image_paths:
            print(f"    → {p}")
    except Exception as e:
        logger.error("Ошибка генерации изображений: %s", e)
        print(f"  Предупреждение: не удалось сгенерировать изображения — {e}")
        image_paths = []

    return image_paths, total_cost_rub


# ─── Главная функция ──────────────────────────────────────────────────────────

def main() -> None:
    # Аргумент командной строки — путь к файлу транскрибации
    file_arg = sys.argv[1] if len(sys.argv) > 1 else None

    print("\n" + "═" * 60)
    print("  AI CLIENT PDF GENERATOR")
    print("═" * 60)
    logger.info("Запуск AI Client PDF Generator")

    # ── Настройки LLM ─────────────────────────────────────────────────────────
    settings = load_settings()
    if settings:
        p_key, provider, model_id, temperature, max_tokens = get_active_config(settings)
        sep()
        print(f"  Настройки: {provider['name']} / {model_id} / temp={temperature} / max_tokens={max_tokens}")
        if ask("  Изменить? (y/n) [n]: ", "n").lower() == "y":
            settings = pick_settings()
            p_key, provider, model_id, temperature, max_tokens = get_active_config(settings)
    else:
        print("\n  Первый запуск — выберите настройки.")
        settings = pick_settings()
        p_key, provider, model_id, temperature, max_tokens = get_active_config(settings)

    logger.info("LLM: %s / %s / temp=%.2f / max_tokens=%d",
                provider["name"], model_id, temperature, max_tokens)

    # ── Тип отчёта ────────────────────────────────────────────────────────────
    report_type = pick_report_type()
    logger.info("Тип отчёта: %s", report_type)

    # ── Транскрибация ─────────────────────────────────────────────────────────
    transcript = get_transcript(file_arg)
    if not transcript:
        print("  Ошибка: транскрибация пустая.")
        sys.exit(1)

    # ── Курс ЦБ РФ ────────────────────────────────────────────────────────────
    print("\n  Получение курса USD/RUB от ЦБ РФ...")
    usd_rub = get_usd_rub_rate()

    # ── AI-обработка ──────────────────────────────────────────────────────────
    sep()
    print(f"  Анализ диалога через {provider['name']} ({model_id})...")

    try:
        data, usage = process_dialog_with_ai(
            text=transcript,
            provider_key=p_key,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            report_type=report_type,
        )
    except Exception as e:
        logger.error("Ошибка AI: %s", e)
        print(f"\n  Ошибка AI: {e}")
        sys.exit(1)

    # Стоимость LLM-запроса
    total_cost_rub = 0.0
    cost_data = None
    if usage:
        cost_data = calculate_cost(model_id, usage["prompt_tokens"], usage["completion_tokens"], usd_rub)
        total_cost_rub += cost_data["cost_total_rub"]
        print("\n" + format_cost_line(cost_data))
        logger.info("Стоимость LLM: $%.6f / %.4f ₽", cost_data["cost_total_usd"], cost_data["cost_total_rub"])

    # ── Генерация изображений (только для дизайн-отчёта) ─────────────────────
    image_paths: list[str] = []
    if report_type == "design":
        image_paths, img_cost = run_image_generation(
            data, transcript, p_key, model_id, temperature, max_tokens, usd_rub
        )
        total_cost_rub += img_cost

    # Передаём пути изображений и данные о затратах в шаблон
    data["images"] = image_paths
    data["cost"] = cost_data

    # ── Генерация PDF ─────────────────────────────────────────────────────────
    sep()
    print("  Генерация PDF...")
    try:
        pdf_path = generate_pdf(data, report_type=report_type)
    except Exception as e:
        logger.error("Ошибка генерации PDF: %s", e)
        print(f"\n  Ошибка PDF: {e}")
        sys.exit(1)

    sep("═")
    print(f"  Отчёт успешно создан: {pdf_path}")
    if total_cost_rub > 0:
        print(f"  Итоговая стоимость сессии: ≈ {total_cost_rub:.4f} ₽")
    sep("═")
    logger.info("Готово: %s", pdf_path)

    # ── Повтор ────────────────────────────────────────────────────────────────
    if ask("\n  Обработать ещё один диалог? (y/n) [n]: ", "n").lower() == "y":
        main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Прервано пользователем.")
        sys.exit(0)
