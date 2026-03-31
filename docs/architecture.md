# AI Client PDF Generator — Architecture Documentation

## Project Overview

Dual-interface system (CLI + Telegram bot) that analyzes client dialog transcriptions
using LLM providers and generates professional PDF reports with optional AI-generated UI mockups.

## Quick Start

```bash
# CLI
python main.py
python main.py examples/example_dialog_marketplace.txt

# Telegram Bot
python bot.py
```

## Project Structure

```
.
├── main.py                       # CLI entry point
├── bot.py                        # Telegram bot
├── config.py                     # Providers & models registry
├── .env                          # API keys
├── requirements.txt
├── pdf_generator_settings.json   # Saved user settings (auto-created)
├── utils/
│   ├── ai_processor.py           # LLM analysis, 3 system prompts
│   ├── image_generator.py        # 4 image generation backends
│   ├── pdf_generator.py          # Jinja2 + WeasyPrint pipeline
│   ├── cost_calculator.py        # USD/RUB cost calculation
│   ├── cbr_rate.py               # CBR exchange rate fetching
│   └── settings.py               # Config persistence
├── templates/
│   ├── report_template.html      # Basic report
│   ├── report_project.html       # Project report
│   └── report_design.html        # Design report + images
├── examples/
│   ├── example_dialog_marketplace.txt
│   ├── example_dialog_tokenization.txt
│   └── example_dialog_software.txt
├── reports/                      # Generated PDFs
│   └── images/                   # Generated AI images
├── logs/
│   ├── app.log                   # CLI log
│   └── bot.log                   # Bot log
└── docs/
    └── architecture.md           # This file
```

---

## C4 Model

### Level 1 — System Context

```mermaid
C4Context
    title System Context — AI Client PDF Generator

    Person(user_cli, "CLI-пользователь", "Запускает python main.py,\nвводит транскрибацию")
    Person(user_tg, "Telegram-пользователь", "Работает через бота\n@your_bot")

    System(app, "AI Client PDF Generator", "Анализирует диалог через LLM,\nгенерирует PDF-отчёт")

    System_Ext(zai, "Z.AI", "GLM-4.7/4.5\napi.z.ai")
    System_Ext(proxy, "ProxyAPI", "GPT-4.1/4o\napi.proxyapi.ru")
    System_Ext(genapi, "GenAPI", "GPT/Claude/Gemini/DeepSeek\nproxy.gen-api.ru")
    System_Ext(cerebras, "Cerebras", "Llama/Qwen (free)\napi.cerebras.ai")
    System_Ext(hf, "HuggingFace", "Llama/Qwen/DeepSeek (free)\nrouter.huggingface.co")
    System_Ext(pollinations, "Pollinations.ai", "FLUX (free, no key)\nimage.pollinations.ai")
    System_Ext(together, "Together.ai", "FLUX.1 schnell/dev\napi.together.ai")
    System_Ext(dalle, "DALL-E via ProxyAPI", "DALL-E 3/2\napi.proxyapi.ru")
    System_Ext(cbr, "ЦБ РФ API", "Курс USD/RUB\nwww.cbr.ru")
    System_Ext(telegram, "Telegram API", "Bot API\napi.telegram.org")

    Rel(user_cli, app, "CLI / файл транскрибации")
    Rel(user_tg, telegram, "Сообщения, файлы")
    Rel(telegram, app, "Webhook / Polling")
    Rel(app, zai, "Chat Completions", "HTTPS")
    Rel(app, proxy, "Chat Completions", "HTTPS")
    Rel(app, genapi, "Chat Completions", "HTTPS")
    Rel(app, cerebras, "Chat Completions", "HTTPS")
    Rel(app, hf, "Chat Completions", "HTTPS")
    Rel(app, pollinations, "Image Generation", "HTTPS GET")
    Rel(app, together, "Image Generation", "HTTPS POST")
    Rel(app, dalle, "Image Generation", "HTTPS POST")
    Rel(app, cbr, "XML_daily.asp", "HTTPS GET")
```

---

### Level 2 — Container Diagram

```mermaid
C4Container
    title Container Diagram — AI Client PDF Generator

    Person(user, "Пользователь")

    Container_Boundary(app, "AI Client PDF Generator") {
        Container(main, "main.py", "Python CLI", "Оркестрирует весь процесс.\nПоддерживает аргумент файла.")
        Container(bot, "bot.py", "Python / python-telegram-bot", "Telegram-бот.\n13 состояний ConversationHandler.")
        Container(config, "config.py", "Python Module", "Реестр провайдеров и моделей.\n5 провайдеров, 20+ моделей.")
        Container(settings, "utils/settings.py", "Python Module", "Сохранение/загрузка настроек.\npdf_generator_settings.json")
        Container(ai_proc, "utils/ai_processor.py", "Python Module", "Запрос к LLM.\n3 системных промпта.\nRetry для нестабильных провайдеров.")
        Container(img_gen, "utils/image_generator.py", "Python Module", "4 бэкенда генерации изображений.\nPollinations / Together / DALL-E.")
        Container(pdf_gen, "utils/pdf_generator.py", "Python Module", "Jinja2 рендер + WeasyPrint.\nBase64 встраивание изображений.")
        Container(cost, "utils/cost_calculator.py", "Python Module", "Расчёт стоимости в USD и RUB.")
        Container(cbr_mod, "utils/cbr_rate.py", "Python Module", "Курс USD/RUB от ЦБ РФ.\nFallback: 90.0")
        ContainerDb(settings_file, "pdf_generator_settings.json", "JSON", "Настройки пользователя")
        ContainerDb(reports_dir, "reports/", "File System", "PDF-отчёты и изображения")
        ContainerDb(logs_dir, "logs/", "Log Files", "app.log, bot.log")
        Container(tmpl, "templates/", "Jinja2 HTML", "3 шаблона отчётов")
    }

    System_Ext(llm_api, "LLM Provider APIs", "Z.AI / ProxyAPI / GenAPI / Cerebras / HuggingFace")
    System_Ext(img_api, "Image APIs", "Pollinations / Together.ai / DALL-E")
    System_Ext(cbr_api, "ЦБ РФ API")
    System_Ext(tg_api, "Telegram API")

    Rel(user, main, "CLI / файл")
    Rel(user, tg_api, "Telegram")
    Rel(tg_api, bot, "Polling")
    Rel(main, settings, "load/save")
    Rel(main, ai_proc, "process_dialog_with_ai()")
    Rel(main, img_gen, "generate_images()")
    Rel(main, pdf_gen, "generate_pdf()")
    Rel(main, cost, "calculate_cost()")
    Rel(main, cbr_mod, "get_usd_rub_rate()")
    Rel(bot, ai_proc, "process_dialog_with_ai()")
    Rel(bot, img_gen, "generate_images()")
    Rel(bot, pdf_gen, "generate_pdf()")
    Rel(bot, cost, "calculate_cost()")
    Rel(bot, cbr_mod, "get_usd_rub_rate()")
    Rel(ai_proc, config, "PROVIDERS dict")
    Rel(img_gen, config, "PROVIDERS dict")
    Rel(settings, settings_file, "R/W JSON")
    Rel(ai_proc, llm_api, "Chat Completions", "HTTPS")
    Rel(img_gen, img_api, "Image Generation", "HTTPS")
    Rel(cbr_mod, cbr_api, "XML_daily.asp", "HTTPS")
    Rel(pdf_gen, tmpl, "Jinja2 render()")
    Rel(pdf_gen, reports_dir, "Сохранить PDF")
    Rel(main, logs_dir, "logging")
    Rel(bot, logs_dir, "logging")
```

---

## LLM Providers & Models

| # | Провайдер | Ключ | Базовый URL | Модели |
|---|-----------|------|-------------|--------|
| 1 | Z.AI | ZAI_API_KEY | api.z.ai/api/paas/v4/ | GLM-4.7-Flash (free), GLM-4.5-Flash (free), GLM-4.7, GLM-4.5, GLM-5 |
| 2 | ProxyAPI | PROXY_API_KEY | api.proxyapi.ru/openai/v1 | GPT-4.1-Nano, GPT-4.1-Mini, GPT-4.1, GPT-4o-Mini, GPT-4o |
| 3 | GenAPI | GEN_API_KEY | proxy.gen-api.ru/v1 | GPT-4.1-Mini, GPT-4.1, GPT-4o, Claude Sonnet 4.5, Gemini 2.5 Flash, DeepSeek Chat, DeepSeek R1 |
| 4 | Cerebras | CEREBRAS_API_KEY | api.cerebras.ai/v1 | Llama 3.1 8B (free), Qwen 3 235B MoE (free) |
| 5 | HuggingFace | HF_TOKEN | router.huggingface.co/v1 | Llama 3.3 70B (free), Qwen 2.5 72B (free), DeepSeek R1 32B (free) |

HuggingFace использует retry: 3 попытки с паузой 8 секунд (нестабильный inference).

---

## Image Generation Backends

| # | Провайдер | Бесплатно | Ключ | Модель | Особенности |
|---|-----------|-----------|------|--------|-------------|
| 1 | Pollinations.ai | Да | Не нужен | FLUX | GET-запрос, без регистрации |
| 2 | Together.ai | Нет | TOGETHER_API_KEY | FLUX.1 [schnell] | $0.003/img, 1-4 шага |
| 3 | Together.ai | Нет | TOGETHER_API_KEY | FLUX.1 [dev] | $0.025/img, 10-50 шагов |
| 4 | ProxyAPI | Нет | PROXY_API_KEY | DALL-E 3 | standard/hd, 1024-1792px |

Все бэкенды добавляют UI-суффикс к промпту для лучшего качества мокапов.
Изображения сохраняются в `reports/images/` и встраиваются в PDF как base64 data URI.

---

## Report Types

### 1. Basic Report (`basic`)

Шаблон: `report_template.html`

Поля JSON от LLM:
```json
{
  "client_name": "...",
  "topic": "...",
  "main_request": "...",
  "mood": "позитивное|нейтральное|негативное|смешанное",
  "next_steps": "..."
}
```

### 2. Project Report (`project`)

Шаблон: `report_project.html`

Поля JSON от LLM:
```json
{
  "project_name": "...",
  "client_company": "...",
  "client_representative": "...",
  "client_position": "...",
  "analyst_name": "...",
  "topic": "...",
  "main_request": "...",
  "key_requirements": ["..."],
  "desired_deadline": "...",
  "estimated_duration": "...",
  "budget": "...",
  "tech_stack": "...",
  "risks": ["..."],
  "client_satisfaction": "позитивная|нейтральная|негативная|смешанная",
  "mood": "...",
  "next_steps": "..."
}
```

### 3. Design Report (`design`)

Шаблон: `report_design.html`

Поля JSON от LLM:
```json
{
  "project_name": "...",
  "client_company": "...",
  "client_representative": "...",
  "client_position": "...",
  "topic": "...",
  "design_style": "...",
  "color_scheme": "...",
  "key_screens": ["..."],
  "references": ["..."],
  "target_audience": "...",
  "platform": "веб|мобильное|десктоп",
  "mood": "...",
  "image_prompt": "English prompt for image generation, max 400 chars",
  "next_steps": "..."
}
```

Дополнительно: генерация изображений через выбранный бэкенд, каждое изображение на отдельной странице PDF.

Все три шаблона содержат блок затрат (`cost`):
- Входные/выходные токены
- Стоимость в USD и RUB
- Курс ЦБ РФ на момент генерации

---

## BPMN — Бизнес-процесс (CLI)

```mermaid
flowchart TD
    Start([Запуск main.py]) --> LoadSettings{Настройки\nсохранены?}

    LoadSettings -- Нет --> PickProvider[Выбор провайдера]
    PickProvider --> PickModel[Выбор модели]
    PickModel --> PickParams[Температура и токены]
    PickParams --> SaveSettings[(Сохранить JSON)]

    LoadSettings -- Да --> ShowSettings[Показать настройки]
    ShowSettings --> Change{Изменить?}
    Change -- Да --> PickProvider
    Change -- Нет --> PickReportType

    SaveSettings --> PickReportType

    PickReportType[Выбор типа отчёта\nbasic / project / design]
    PickReportType --> InputSource{Источник\nтранскрибации}

    InputSource -- Вручную --> ManualInput[Ввод текста]
    InputSource -- Файл --> FileInput[Чтение .txt]
    InputSource -- Пример --> ExampleInput[Выбор из examples/]

    ManualInput --> Validate{Текст\nне пустой?}
    FileInput --> Validate
    ExampleInput --> Validate

    Validate -- Нет --> ErrEmpty[Ошибка: пусто]
    ErrEmpty --> End

    Validate -- Да --> GetRate[Курс USD/RUB от ЦБ РФ]
    GetRate --> RateFail{Ошибка?}
    RateFail -- Да --> UseDefault[Fallback: 90.0]
    RateFail -- Нет --> SendAI
    UseDefault --> SendAI

    SendAI[Отправить в LLM\nprocess_dialog_with_ai]
    SendAI --> AIFail{Ошибка?}
    AIFail -- Да --> ErrAI[Ошибка AI]
    ErrAI --> End

    AIFail -- Нет --> ParseJSON[Парсинг JSON]
    ParseJSON --> CalcCost[Расчёт стоимости]
    CalcCost --> PrintCost[Вывод токенов и стоимости]

    PrintCost --> IsDesign{Тип = design?}
    IsDesign -- Нет --> GenPDF
    IsDesign -- Да --> PickImageBackend[Выбор бэкенда изображений]
    PickImageBackend --> GenImages[Генерация изображений]
    GenImages --> ImgFail{Ошибка?}
    ImgFail -- Да --> WarnNoImg[Предупреждение,\nPDF без изображений]
    ImgFail -- Нет --> GenPDF
    WarnNoImg --> GenPDF

    GenPDF[Jinja2 рендер + WeasyPrint]
    GenPDF --> SavePDF[(Сохранить PDF\nreports/)]
    SavePDF --> PrintResult[Отчёт создан: путь к файлу]
    PrintResult --> Again{Ещё один?}
    Again -- Да --> PickReportType
    Again -- Нет --> End([Завершение])
```

---

## BPMN — Бизнес-процесс (Telegram Bot)

```mermaid
flowchart TD
    TGStart([Пользователь → /start или Новый отчёт]) --> ChooseReport[Выбор типа отчёта\nInline кнопки]
    ChooseReport --> ChooseSource[Источник транскрибации\nТекст / Файл / Пример]

    ChooseSource -- Текст --> WaitText[Ожидание текста]
    ChooseSource -- Файл --> WaitFile[Ожидание .txt файла]
    ChooseSource -- Пример --> ShowExamples[Список примеров]
    ShowExamples --> SelectExample[Выбор примера]

    WaitText --> GotTranscript
    WaitFile --> GotTranscript
    SelectExample --> GotTranscript

    GotTranscript[Транскрибация получена] --> AIAnalysis[AI-анализ\nprocess_dialog_with_ai]
    AIAnalysis --> AIFail{Ошибка?}
    AIFail -- Да --> NotifyError[Сообщение об ошибке]
    NotifyError --> TGEnd

    AIFail -- Нет --> IsDesignBot{Тип = design?}
    IsDesignBot -- Нет --> GenPDFBot
    IsDesignBot -- Да --> ChooseBackend[Выбор бэкенда изображений\nInline кнопки]
    ChooseBackend -- Пропустить --> GenPDFBot
    ChooseBackend --> ChooseCount[Количество изображений 1-4]
    ChooseCount --> ChooseRatio[Соотношение сторон]
    ChooseRatio --> GenImagesBot[Генерация изображений]
    GenImagesBot --> GenPDFBot

    GenPDFBot[Генерация PDF\nWeasyPrint] --> SendPDF[Отправить PDF в чат\nsend_document]
    SendPDF --> Done[Готово! Новый отчёт?]
    Done --> TGEnd([Конец])
```

---

## UML — Sequence Diagram (полный цикл CLI)

```mermaid
sequenceDiagram
    actor User
    participant Main as main.py
    participant Settings as settings.py
    participant CBR as cbr_rate.py
    participant AI as ai_processor.py
    participant LLM as LLM Provider API
    participant ImgGen as image_generator.py
    participant ImgAPI as Image API
    participant PDF as pdf_generator.py
    participant FS as File System

    User->>Main: python main.py [file.txt]
    Main->>Settings: load_settings()
    alt Нет настроек
        Settings-->>Main: None
        Main->>User: Меню выбора провайдера/модели
        User->>Main: Выбор
        Main->>Settings: save_settings()
        Settings->>FS: pdf_generator_settings.json
    else Настройки есть
        Settings-->>Main: settings dict
        Main->>User: Показать текущие настройки
    end

    Main->>User: Выбор типа отчёта
    User->>Main: basic / project / design

    Main->>User: Источник транскрибации
    User->>Main: Текст / файл / пример
    Main->>FS: Чтение файла (если нужно)

    Main->>CBR: get_usd_rub_rate()
    CBR->>LLM: GET cbr.ru/XML_daily.asp
    LLM-->>CBR: XML с курсами
    CBR-->>Main: usd_rub: float

    Main->>AI: process_dialog_with_ai(text, provider, model, ...)
    AI->>LLM: POST /chat/completions
    Note over AI,LLM: system_prompt + transcript
    LLM-->>AI: JSON response + usage
    AI->>AI: regex extract JSON
    AI-->>Main: (data dict, usage dict)

    Main->>Main: calculate_cost(model, tokens, usd_rub)
    Main->>User: Вывод токенов и стоимости

    opt report_type == design
        Main->>User: Выбор бэкенда изображений
        User->>Main: backend_key, count, ratio
        Main->>ImgGen: generate_images(prompt, backend_key, ...)
        ImgGen->>ImgAPI: HTTP запрос (GET/POST)
        ImgAPI-->>ImgGen: Изображение (bytes/b64)
        ImgGen->>FS: Сохранить reports/images/*.png
        ImgGen-->>Main: [paths]
    end

    Main->>PDF: generate_pdf(data, report_type)
    PDF->>PDF: _to_data_uri(image_paths) → base64
    PDF->>PDF: Jinja2 render(template, **data)
    PDF->>PDF: WeasyPrint HTML → PDF
    PDF->>FS: Сохранить reports/*.pdf
    PDF-->>Main: pdf_path

    Main->>User: Отчёт создан: reports/...pdf
```

---

## UML — Sequence Diagram (Telegram Bot)

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant TG as Telegram API
    participant Bot as bot.py
    participant AI as ai_processor.py
    participant ImgGen as image_generator.py
    participant PDF as pdf_generator.py

    User->>TG: /start или "Новый отчёт"
    TG->>Bot: Update
    Bot->>TG: Inline кнопки типа отчёта
    TG->>User: Показать кнопки

    User->>TG: Нажать кнопку (rt_project)
    TG->>Bot: CallbackQuery
    Bot->>TG: Inline кнопки источника транскрибации
    TG->>User: Показать кнопки

    User->>TG: Отправить текст или .txt файл
    TG->>Bot: Message / Document
    Bot->>TG: "Анализирую диалог..."

    Bot->>AI: process_dialog_with_ai(...)
    AI-->>Bot: (data, usage)
    Bot->>Bot: calculate_cost(...)

    alt report_type == design
        Bot->>TG: Inline кнопки бэкенда изображений
        User->>TG: Выбор бэкенда
        TG->>Bot: CallbackQuery
        Bot->>TG: Inline кнопки количества
        User->>TG: Выбор количества
        TG->>Bot: CallbackQuery
        Bot->>TG: Inline кнопки соотношения сторон
        User->>TG: Выбор соотношения
        TG->>Bot: CallbackQuery
        Bot->>TG: "Генерирую изображения..."
        Bot->>ImgGen: generate_images(...)
        ImgGen-->>Bot: [image_paths]
    end

    Bot->>TG: "Создаю PDF..."
    Bot->>PDF: generate_pdf(data, report_type)
    PDF-->>Bot: pdf_path

    Bot->>TG: send_document(pdf_path, caption)
    TG->>User: PDF файл + стоимость
    Bot->>TG: "Готово! Новый отчёт?"
    TG->>User: Reply keyboard
```

---

## UML — State Diagram (Telegram Bot)

```mermaid
stateDiagram-v2
    [*] --> MAIN_MENU : /start

    MAIN_MENU --> CHOOSE_REPORT : Новый отчёт / /new
    MAIN_MENU --> CHOOSE_PROVIDER : Настройки / /settings
    MAIN_MENU --> MAIN_MENU : Помощь / /help

    CHOOSE_REPORT --> TRANSCRIPT_SOURCE : Выбор типа (rt_basic/project/design)

    TRANSCRIPT_SOURCE --> TRANSCRIPT_TEXT : src_text
    TRANSCRIPT_SOURCE --> TRANSCRIPT_FILE : src_file
    TRANSCRIPT_SOURCE --> TRANSCRIPT_TEXT : src_example (показать список)

    TRANSCRIPT_TEXT --> GENERATING : Текст получен
    TRANSCRIPT_FILE --> GENERATING : Файл получен

    GENERATING --> IMAGE_BACKEND : report_type == design
    GENERATING --> MAIN_MENU : report_type != design (PDF отправлен)

    IMAGE_BACKEND --> IMAGE_COUNT : Выбор бэкенда
    IMAGE_BACKEND --> MAIN_MENU : Пропустить (PDF без изображений)

    IMAGE_COUNT --> IMAGE_RATIO : Выбор количества
    IMAGE_RATIO --> MAIN_MENU : Выбор соотношения (PDF отправлен)

    CHOOSE_PROVIDER --> CHOOSE_MODEL : Выбор провайдера
    CHOOSE_MODEL --> CHOOSE_TEMP : Выбор модели
    CHOOSE_TEMP --> CHOOSE_TOKENS : Ввод температуры
    CHOOSE_TOKENS --> MAIN_MENU : Ввод токенов (настройки сохранены)

    MAIN_MENU --> [*] : /start (перезапуск)
```

---

## UML — Class Diagram

```mermaid
classDiagram
    direction TB

    class Config {
        +PROVIDERS: dict
    }

    class Settings {
        +SETTINGS_FILE: str
        +pick_settings() dict
        +save_settings(settings) None
        +load_settings() dict|None
        +get_active_config(settings) tuple
    }

    class AIProcessor {
        +SYSTEM_PROMPT_BASIC: str
        +SYSTEM_PROMPT_PROJECT: str
        +SYSTEM_PROMPT_DESIGN: str
        +_RETRY_PROVIDERS: set
        +_MAX_RETRIES: int
        +_RETRY_DELAY: int
        +process_dialog_with_ai(text, provider_key, model_id, temperature, max_tokens, report_type) tuple
        -_call_ai(messages, provider_key, model_id, temperature, max_tokens) tuple
        -_extract_json(content) dict
        -_clean_error(e) str
    }

    class PDFGenerator {
        +TEMPLATES_DIR: Path
        +REPORTS_DIR: Path
        +TEMPLATE_MAP: dict
        +generate_pdf(data, report_type) str
        -_to_data_uri(image_path) str
    }

    class ImageGenerator {
        +IMAGE_BACKENDS: dict
        +UI_PROMPT_SUFFIX: str
        +generate_images(prompt, backend_key, count, ...) list
        +pick_image_settings() dict
        -_generate_pollinations(prompt, count, aspect_ratio, prefix) list
        -_generate_together(prompt, model, count, aspect_ratio, steps, prefix) list
        -_generate_dalle(prompt, provider_key, model, count, size, quality, prefix) list
    }

    class CostCalculator {
        +MODEL_PRICES: dict
        +calculate_cost(model_id, prompt_tokens, completion_tokens, usd_rub) dict
        +format_cost_line(cost) str
    }

    class CbrRate {
        +CBR_URL: str
        +get_usd_rub_rate() float
    }

    class MainCLI {
        +REPORT_TYPES: dict
        +main() None
        +get_transcript(file_arg) str
        +pick_report_type() str
        +run_image_generation(data, ...) tuple
    }

    class TelegramBot {
        +STATE_MAIN_MENU: int
        +STATE_CHOOSE_REPORT: int
        +IMAGE_BACKENDS: dict
        +cmd_start(update, context)
        +cmd_new(update, context)
        +cmd_settings(update, context)
        +cb_report_type(update, context)
        +cb_transcript_source(update, context)
        +cb_image_backend(update, context)
        -_start_processing(update, context, query)
        -_generate_pdf_and_send(update, context, query)
        -safe_answer(query, text)
        -safe_edit(query, update, text)
        -error_handler(update, context)
    }

    MainCLI --> Settings : load/save
    MainCLI --> AIProcessor : process_dialog
    MainCLI --> ImageGenerator : generate_images
    MainCLI --> PDFGenerator : generate_pdf
    MainCLI --> CostCalculator : calculate_cost
    MainCLI --> CbrRate : get_rate

    TelegramBot --> AIProcessor : process_dialog
    TelegramBot --> ImageGenerator : generate_images
    TelegramBot --> PDFGenerator : generate_pdf
    TelegramBot --> CostCalculator : calculate_cost
    TelegramBot --> CbrRate : get_rate

    AIProcessor --> Config : PROVIDERS
    ImageGenerator --> Config : PROVIDERS
    Settings --> Config : PROVIDERS
```

---

## Cost Calculation

Формула расчёта стоимости запроса:

```
cost_input_usd  = (prompt_tokens     / 1_000_000) × input_price_per_1M
cost_output_usd = (completion_tokens / 1_000_000) × output_price_per_1M
cost_total_usd  = cost_input_usd + cost_output_usd
cost_total_rub  = cost_total_usd × usd_rub_rate
```

Цены (USD за 1M токенов):

| Модель | Вход | Выход |
|--------|------|-------|
| GLM-4.7-Flash | 0.00 | 0.00 |
| GLM-4.5-Flash | 0.00 | 0.00 |
| GLM-4.7 / GLM-4.5 | 0.14 | 0.14 |
| GLM-5 | 1.00 | 1.00 |
| GPT-4.1-Nano | 0.10 | 0.40 |
| GPT-4.1-Mini | 0.40 | 1.60 |
| GPT-4.1 | 2.00 | 8.00 |
| GPT-4o-Mini | 0.15 | 0.60 |
| GPT-4o | 2.50 | 10.00 |
| Claude Sonnet 4.5 | 3.00 | 15.00 |
| Gemini 2.5 Flash | 0.15 | 0.60 |
| DeepSeek Chat | 0.27 | 1.10 |
| DeepSeek R1 | 0.55 | 2.19 |

Курс USD/RUB получается от ЦБ РФ (`cbr.ru/scripts/XML_daily.asp`). При недоступности используется fallback 90.0 ₽.

---

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input["Входные данные"]
        T["Транскрибация диалога"]
        S["Настройки пользователя"]
        K["API-ключи .env"]
    end

    subgraph Processing["Обработка"]
        AI["ai_processor.py"]
        CBR["cbr_rate.py"]
        COST["cost_calculator.py"]
        TMPL["pdf_generator.py"]
        IMG["image_generator.py"]
    end

    subgraph Output["Выходные данные"]
        PDF["PDF-отчёт reports/"]
        LOG["Лог logs/app.log"]
        CONSOLE["Консоль токены и стоимость"]
        IMGFILES["Изображения reports/images/"]
    end

    T --> AI
    S --> AI
    K --> AI
    AI -->|JSON данные| TMPL
    AI -->|usage токены| COST
    CBR -->|usd_rub float| COST
    COST -->|cost dict| CONSOLE
    COST -->|cost dict| TMPL
    T --> IMG
    IMG -->|image paths| TMPL
    IMG --> IMGFILES
    TMPL --> PDF
    AI --> LOG
    TMPL --> LOG
    COST --> LOG
```

---

## Error Handling

| Ошибка | Место | Поведение |
|--------|-------|-----------|
| LLM API timeout/5xx | ai_processor.py | Retry 3x с паузой 8с (HuggingFace) |
| HTML в теле ошибки | ai_processor._clean_error | Парсинг `<h1>` и `<p>` тегов |
| ЦБ РФ недоступен | cbr_rate.py | Fallback 90.0 ₽ |
| Изображение не найдено | pdf_generator._to_data_uri | Пустая строка, изображение пропускается |
| Telegram TimedOut | bot.error_handler | Логируется как warning, игнорируется |
| Telegram BadRequest "not modified" | bot.error_handler | Тихо игнорируется |
| query.answer() timeout | bot.safe_answer | try/except, игнорируется |
| query.edit_message_text BadRequest | bot.safe_edit | Fallback на reply_text |
| KeyboardInterrupt | main.py | Чистый выход с сообщением |
| Устаревший model_key в настройках | settings.get_active_config | Fallback на первую модель провайдера |

---

## Dependencies

```
openai>=1.30.0          # LLM API client (OpenAI-compatible)
jinja2>=3.1.0           # HTML template rendering
weasyprint>=62.0        # HTML to PDF conversion
python-dotenv>=1.0.0    # .env file loading
requests>=2.31.0        # HTTP for CBR, Pollinations, Together.ai
python-telegram-bot>=21.0  # Telegram Bot API
```

## Environment Variables

```bash
BOT_TOKEN=          # Telegram Bot Token (от @BotFather)
ZAI_API_KEY=        # Z.AI API key
PROXY_API_KEY=      # ProxyAPI key
GEN_API_KEY=        # GenAPI key
CEREBRAS_API_KEY=   # Cerebras API key
HF_TOKEN=           # HuggingFace token
TOGETHER_API_KEY=   # Together.ai API key (для платных FLUX моделей)
```
