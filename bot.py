"""
bot.py — Telegram-бот для AI Client PDF Generator.

Запуск: python bot.py

Команды:
  /start   — приветствие и инструкция
  /new     — начать новый отчёт
  /settings — изменить настройки AI
  /help    — справка
"""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler,
        ConversationHandler, ContextTypes, filters,
    )
    from telegram.request import HTTPXRequest
except ImportError:
    print("Установите python-telegram-bot: pip install python-telegram-bot")
    sys.exit(1)

from config import PROVIDERS
from utils.ai_processor import process_dialog_with_ai
from utils.pdf_generator import generate_pdf
from utils.cbr_rate import get_usd_rub_rate
from utils.cost_calculator import calculate_cost, format_cost_line
from utils.image_generator import generate_images, IMAGE_BACKENDS

# ─── Состояния диалога ────────────────────────────────────────────────────────

(
    STATE_MAIN_MENU,
    STATE_CHOOSE_REPORT,
    STATE_CHOOSE_PROVIDER,
    STATE_CHOOSE_MODEL,
    STATE_CHOOSE_TEMP,
    STATE_CHOOSE_TOKENS,
    STATE_TRANSCRIPT_SOURCE,
    STATE_TRANSCRIPT_TEXT,
    STATE_TRANSCRIPT_FILE,
    STATE_IMAGE_BACKEND,
    STATE_IMAGE_COUNT,
    STATE_IMAGE_RATIO,
    STATE_GENERATING,
) = range(13)

# ─── Клавиатуры ───────────────────────────────────────────────────────────────

REPORT_TYPES = {
    "basic":   "Базовый отчёт",
    "project": "Проектный отчёт",
    "design":  "Дизайн-отчёт + изображение",
}

def kb_report_types():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Базовый отчёт", callback_data="rt_basic")],
        [InlineKeyboardButton("Проектный отчёт", callback_data="rt_project")],
        [InlineKeyboardButton("Дизайн-отчёт + изображение", callback_data="rt_design")],
    ])

def kb_providers():
    rows = []
    for key, p in PROVIDERS.items():
        rows.append([InlineKeyboardButton(p["name"], callback_data=f"prov_{key}")])
    return InlineKeyboardMarkup(rows)

def kb_models(provider_key: str):
    models = PROVIDERS[provider_key]["models"]
    rows = []
    for key, m in models.items():
        free = " (free)" if m.get("free") else ""
        rows.append([InlineKeyboardButton(f"{m['label']}{free}", callback_data=f"model_{key}")])
    return InlineKeyboardMarkup(rows)

def kb_transcript_source():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Ввести текст", callback_data="src_text")],
        [InlineKeyboardButton("Загрузить файл (.txt)", callback_data="src_file")],
        [InlineKeyboardButton("Использовать пример", callback_data="src_example")],
    ])

def kb_image_backends():
    rows = []
    for key, b in IMAGE_BACKENDS.items():
        free = " [FREE]" if b["free"] else ""
        rows.append([InlineKeyboardButton(f"{key}. {b['name']}{free}", callback_data=f"img_{key}")])
    rows.append([InlineKeyboardButton("Пропустить генерацию", callback_data="img_skip")])
    return InlineKeyboardMarkup(rows)

def kb_image_count():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data="cnt_1"),
         InlineKeyboardButton("2", callback_data="cnt_2"),
         InlineKeyboardButton("3", callback_data="cnt_3"),
         InlineKeyboardButton("4", callback_data="cnt_4")],
    ])

def kb_aspect_ratios():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("16:9 (веб)", callback_data="ratio_16:9"),
         InlineKeyboardButton("1:1", callback_data="ratio_1:1")],
        [InlineKeyboardButton("4:3", callback_data="ratio_4:3"),
         InlineKeyboardButton("3:2", callback_data="ratio_3:2")],
    ])

def kb_main_menu():
    return ReplyKeyboardMarkup(
        [["Новый отчёт", "Настройки"], ["Помощь"]],
        resize_keyboard=True,
    )

# ─── Вспомогательные функции ──────────────────────────────────────────────────

async def safe_answer(query, text: str = "") -> None:
    """Отвечает на callback_query, игнорируя таймауты."""
    try:
        await query.answer(text)
    except Exception:
        pass  # таймаут на answer() не критичен


async def safe_edit(query, update: Update, text: str, **kwargs) -> None:
    """
    Редактирует сообщение через query, при ошибке (BadRequest/TimedOut)
    отправляет новое сообщение в чат.
    """
    from telegram.error import BadRequest, TimedOut
    try:
        await query.edit_message_text(text, **kwargs)
    except (BadRequest, TimedOut):
        try:
            await update.effective_message.reply_text(text, **kwargs)
        except Exception:
            pass
    except Exception:
        pass

def get_user_settings(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Возвращает настройки пользователя, инициализируя дефолтами если нужно."""
    if "settings" not in context.user_data:
        context.user_data["settings"] = {
            "provider_key": "1",
            "model_key": "1",
            "temperature": 0.7,
            "max_tokens": 2048,
        }
    return context.user_data["settings"]

def settings_summary(context: ContextTypes.DEFAULT_TYPE) -> str:
    s = get_user_settings(context)
    p = PROVIDERS[s["provider_key"]]
    m = p["models"].get(s["model_key"], list(p["models"].values())[0])
    return (
        f"Провайдер: {p['name']}\n"
        f"Модель: {m['label']}\n"
        f"Температура: {s['temperature']}\n"
        f"Макс. токенов: {s['max_tokens']}"
    )

# ─── Обработчики команд ───────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я генерирую PDF-отчёты по диалогам с клиентами.\n\n"
        "Нажми «Новый отчёт» чтобы начать, или /help для справки.",
        reply_markup=kb_main_menu(),
    )
    return STATE_MAIN_MENU

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Как пользоваться:\n\n"
        "1. Нажми «Новый отчёт»\n"
        "2. Выбери тип отчёта\n"
        "3. Отправь транскрибацию диалога (текстом или .txt файлом)\n"
        "4. Получи готовый PDF\n\n"
        "Типы отчётов:\n"
        "• Базовый — клиент, тема, запрос, настроение\n"
        "• Проектный — полный анализ: сроки, бюджет, риски, требования\n"
        "• Дизайн — требования к UI + AI-генерация концепт-изображения\n\n"
        "Команды:\n"
        "/new — новый отчёт\n"
        "/settings — настройки AI\n"
        "/start — главное меню"
    )
    await update.message.reply_text(text, reply_markup=kb_main_menu())
    return STATE_MAIN_MENU

async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("report_data", None)
    context.user_data.pop("transcript", None)
    await update.message.reply_text(
        "Выберите тип отчёта:",
        reply_markup=kb_report_types(),
    )
    return STATE_CHOOSE_REPORT

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Текущие настройки:\n\n{settings_summary(context)}\n\nВыберите провайдера:",
        reply_markup=kb_providers(),
    )
    return STATE_CHOOSE_PROVIDER

# ─── Обработчики текстовых кнопок главного меню ───────────────────────────────

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Новый отчёт":
        return await cmd_new(update, context)
    if text == "Настройки":
        return await cmd_settings(update, context)
    if text == "Помощь":
        return await cmd_help(update, context)
    return STATE_MAIN_MENU

# ─── Выбор типа отчёта ────────────────────────────────────────────────────────

async def cb_report_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    rt = query.data.replace("rt_", "")
    context.user_data["report_type"] = rt
    await query.edit_message_text(
        f"Тип отчёта: {REPORT_TYPES[rt]}\n\nОткуда взять транскрибацию?",
        reply_markup=kb_transcript_source(),
    )
    return STATE_TRANSCRIPT_SOURCE

# ─── Источник транскрибации ───────────────────────────────────────────────────

async def cb_transcript_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    src = query.data

    if src == "src_text":
        await query.edit_message_text("Отправьте текст транскрибации диалога:")
        return STATE_TRANSCRIPT_TEXT

    if src == "src_file":
        await query.edit_message_text("Отправьте .txt файл с транскрибацией:")
        return STATE_TRANSCRIPT_FILE

    if src == "src_example":
        examples = list(Path("examples").glob("*.txt"))
        if not examples:
            await query.edit_message_text("Примеры не найдены в папке examples/")
            return STATE_MAIN_MENU
        rows = [[InlineKeyboardButton(p.stem, callback_data=f"ex_{i}")] for i, p in enumerate(examples)]
        context.user_data["examples"] = [str(p) for p in examples]
        await query.edit_message_text("Выберите пример:", reply_markup=InlineKeyboardMarkup(rows))
        return STATE_TRANSCRIPT_TEXT

async def cb_example_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    idx = int(query.data.replace("ex_", ""))
    path = context.user_data["examples"][idx]
    with open(path, encoding="utf-8") as f:
        context.user_data["transcript"] = f.read().strip()
    await query.edit_message_text(f"Загружен пример: {Path(path).name}\n\nНачинаю обработку...")
    return await _start_processing(update, context, query=query)

async def handle_transcript_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["transcript"] = update.message.text.strip()
    await update.message.reply_text("Транскрибация получена. Начинаю обработку...")
    return await _start_processing(update, context)

async def handle_transcript_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Пожалуйста, отправьте файл в формате .txt")
        return STATE_TRANSCRIPT_FILE
    file = await doc.get_file()
    content = await file.download_as_bytearray()
    context.user_data["transcript"] = content.decode("utf-8", errors="replace").strip()
    await update.message.reply_text(f"Файл получен: {doc.file_name}\n\nНачинаю обработку...")
    return await _start_processing(update, context)

# ─── Выбор бэкенда изображений ────────────────────────────────────────────────

async def cb_image_backend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if query.data == "img_skip":
        context.user_data["image_backend"] = None
        await query.edit_message_text("Генерация изображений пропущена. Создаю PDF...")
        return await _generate_pdf_and_send(update, context, query=query)

    backend_key = query.data.replace("img_", "")
    context.user_data["image_backend"] = backend_key
    await query.edit_message_text("Сколько изображений сгенерировать?", reply_markup=kb_image_count())
    return STATE_IMAGE_COUNT

async def cb_image_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["image_count"] = int(query.data.replace("cnt_", ""))
    await query.edit_message_text("Выберите соотношение сторон:", reply_markup=kb_aspect_ratios())
    return STATE_IMAGE_RATIO

async def cb_image_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["image_ratio"] = query.data.replace("ratio_", "")
    await query.edit_message_text("Генерирую изображения...")
    return await _generate_pdf_and_send(update, context, query=query)

# ─── Настройки провайдера ─────────────────────────────────────────────────────

async def cb_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    p_key = query.data.replace("prov_", "")
    get_user_settings(context)["provider_key"] = p_key
    get_user_settings(context)["model_key"] = "1"
    await query.edit_message_text(
        f"Провайдер: {PROVIDERS[p_key]['name']}\n\nВыберите модель:",
        reply_markup=kb_models(p_key),
    )
    return STATE_CHOOSE_MODEL

async def cb_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    m_key = query.data.replace("model_", "")
    s = get_user_settings(context)
    s["model_key"] = m_key
    p = PROVIDERS[s["provider_key"]]
    m = p["models"][m_key]
    lo, hi = m["temp_range"]
    await query.edit_message_text(
        f"Модель: {m['label']}\n\n"
        f"Введите температуру ({lo}–{hi}), например: 0.7\n"
        f"Или отправьте «-» для значения по умолчанию."
    )
    return STATE_CHOOSE_TEMP

async def handle_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_user_settings(context)
    p = PROVIDERS[s["provider_key"]]
    m = p["models"][s["model_key"]]
    lo, hi = m["temp_range"]
    text = update.message.text.strip()
    if text == "-":
        s["temperature"] = 0.7
    else:
        try:
            s["temperature"] = max(lo, min(hi, float(text)))
        except ValueError:
            s["temperature"] = 0.7
    await update.message.reply_text(
        f"Температура: {s['temperature']}\n\n"
        f"Введите макс. токенов (1–{m['max_tokens']}), например: 2048\n"
        f"Или «-» для значения по умолчанию."
    )
    return STATE_CHOOSE_TOKENS

async def handle_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_user_settings(context)
    p = PROVIDERS[s["provider_key"]]
    m = p["models"][s["model_key"]]
    text = update.message.text.strip()
    if text == "-":
        s["max_tokens"] = 2048
    else:
        try:
            s["max_tokens"] = max(256, min(m["max_tokens"], int(text)))
        except ValueError:
            s["max_tokens"] = 2048
    await update.message.reply_text(
        f"Настройки сохранены!\n\n{settings_summary(context)}",
        reply_markup=kb_main_menu(),
    )
    return STATE_MAIN_MENU

# ─── Основная обработка ───────────────────────────────────────────────────────

async def _start_processing(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Запускает AI-анализ транскрибации."""
    s = get_user_settings(context)
    p_key = s["provider_key"]
    # Валидируем model_key
    provider = PROVIDERS[p_key]
    m_key = s["model_key"]
    if m_key not in provider["models"]:
        m_key = next(iter(provider["models"]))
        s["model_key"] = m_key
    model_id = provider["models"][m_key]["id"]
    temperature = s["temperature"]
    max_tokens = s["max_tokens"]
    report_type = context.user_data.get("report_type", "basic")
    transcript = context.user_data.get("transcript", "")

    send = query.edit_message_text if query else update.message.reply_text

    await send(f"Анализирую диалог через {provider['name']} ({model_id})...")

    try:
        usd_rub = get_usd_rub_rate()
        data, usage = process_dialog_with_ai(
            text=transcript,
            provider_key=p_key,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            report_type=report_type,
        )
    except Exception as e:
        await send(f"Ошибка AI: {e}\n\nПопробуйте другого провайдера (/settings)")
        return STATE_MAIN_MENU

    cost_data = None
    if usage:
        cost_data = calculate_cost(model_id, usage["prompt_tokens"], usage["completion_tokens"], usd_rub)

    context.user_data["report_data"] = data
    context.user_data["cost_data"] = cost_data
    context.user_data["usd_rub"] = usd_rub

    if report_type == "design":
        await send("Диалог проанализирован. Выберите провайдер для генерации изображения:", reply_markup=kb_image_backends())
        return STATE_IMAGE_BACKEND

    return await _generate_pdf_and_send(update, context, query=query)


async def _generate_pdf_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Генерирует PDF и отправляет пользователю."""
    data = context.user_data.get("report_data", {})
    cost_data = context.user_data.get("cost_data")
    report_type = context.user_data.get("report_type", "basic")
    image_paths: list[str] = []
    chat_id = update.effective_chat.id

    async def notify(text: str) -> None:
        """Всегда отправляет новое сообщение — избегаем BadRequest 'not modified'."""
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.warning("notify failed: %s", e)

    # Генерация изображений для дизайн-отчёта
    backend_key = context.user_data.get("image_backend")
    if report_type == "design" and backend_key:
        image_prompt = data.get("image_prompt", "")
        if not image_prompt:
            image_prompt = f"Modern UI design for {data.get('project_name', 'web app')}, clean minimal style"

        await notify("Генерирую изображения...")
        from datetime import datetime
        prefix = f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            image_paths = generate_images(
                prompt=image_prompt,
                backend_key=backend_key,
                count=context.user_data.get("image_count", 1),
                report_prefix=prefix,
                aspect_ratio=context.user_data.get("image_ratio", "16:9"),
            )
        except Exception as e:
            logger.error("Ошибка генерации изображений: %s", e)
            await notify(f"Не удалось сгенерировать изображения: {e}\n\nСоздаю PDF без изображений...")

    data["images"] = image_paths
    data["cost"] = cost_data

    await notify("Создаю PDF...")

    try:
        pdf_path = generate_pdf(data, report_type=report_type)
    except Exception as e:
        await notify(f"Ошибка генерации PDF: {e}")
        return STATE_MAIN_MENU

    cost_line = ""
    if cost_data:
        cost_line = f"\nТокены: {cost_data['total_tokens']} | {cost_data['cost_total_rub']:.4f} ₽"

    caption = f"Отчёт готов: {REPORT_TYPES.get(report_type, report_type)}{cost_line}"

    with open(pdf_path, "rb") as f:
        await context.bot.send_document(
            chat_id=chat_id,
            document=f,
            filename=Path(pdf_path).name,
            caption=caption,
        )

    await context.bot.send_message(
        chat_id=chat_id,
        text="Готово! Нажмите «Новый отчёт» для следующего.",
        reply_markup=kb_main_menu(),
    )
    return STATE_MAIN_MENU

# ─── Глобальный обработчик ошибок ────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    from telegram.error import BadRequest, TimedOut, NetworkError
    err = context.error
    # Игнорируем некритичные ошибки
    if isinstance(err, (TimedOut, NetworkError)):
        logger.warning("Сетевая ошибка (игнорируется): %s", err)
        return
    if isinstance(err, BadRequest) and "not modified" in str(err).lower():
        logger.debug("BadRequest 'not modified' (игнорируется)")
        return
    logger.error("Необработанная ошибка: %s", err, exc_info=err)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Произошла ошибка: {err}\n\nНажмите /start для перезапуска.",
            )
        except Exception:
            pass


# ─── Запуск бота ──────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        print("Ошибка: BOT_TOKEN не найден в .env")
        sys.exit(1)

    app = (
        Application.builder()
        .token(token)
        .request(HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0,
        ))
        .build()
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CommandHandler("new", cmd_new),
            CommandHandler("settings", cmd_settings),
            MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler),
        ],
        states={
            STATE_MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler),
            ],
            STATE_CHOOSE_REPORT: [
                CallbackQueryHandler(cb_report_type, pattern="^rt_"),
            ],
            STATE_CHOOSE_PROVIDER: [
                CallbackQueryHandler(cb_provider, pattern="^prov_"),
            ],
            STATE_CHOOSE_MODEL: [
                CallbackQueryHandler(cb_model, pattern="^model_"),
            ],
            STATE_CHOOSE_TEMP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_temp),
            ],
            STATE_CHOOSE_TOKENS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tokens),
            ],
            STATE_TRANSCRIPT_SOURCE: [
                CallbackQueryHandler(cb_transcript_source, pattern="^src_"),
                CallbackQueryHandler(cb_example_select, pattern="^ex_"),
            ],
            STATE_TRANSCRIPT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transcript_text),
                CallbackQueryHandler(cb_example_select, pattern="^ex_"),
            ],
            STATE_TRANSCRIPT_FILE: [
                MessageHandler(filters.Document.ALL, handle_transcript_file),
            ],
            STATE_IMAGE_BACKEND: [
                CallbackQueryHandler(cb_image_backend, pattern="^img_"),
            ],
            STATE_IMAGE_COUNT: [
                CallbackQueryHandler(cb_image_count, pattern="^cnt_"),
            ],
            STATE_IMAGE_RATIO: [
                CallbackQueryHandler(cb_image_ratio, pattern="^ratio_"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            CommandHandler("help", cmd_help),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_error_handler(error_handler)

    logger.info("Бот запущен")
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
