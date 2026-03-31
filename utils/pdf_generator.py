"""
pdf_generator.py — генерация PDF из HTML-шаблона через Jinja2 + WeasyPrint.
Поддерживает три типа отчётов: basic, project, design.
Изображения встраиваются как base64 data URI для надёжной работы на Windows.
"""
import base64
import logging
import mimetypes
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
REPORTS_DIR = Path(__file__).parent.parent / "reports"

TEMPLATE_MAP = {
    "basic":   "report_template.html",
    "project": "report_project.html",
    "design":  "report_design.html",
}


def _to_data_uri(image_path: str) -> str:
    """Конвертирует файл изображения в data URI (base64) для встраивания в HTML."""
    path = Path(image_path)
    if not path.exists():
        logger.warning("Изображение не найдено: %s", image_path)
        return ""
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def generate_pdf(data: dict, report_type: str = "basic") -> str:
    """
    Подставляет данные в HTML-шаблон и сохраняет PDF.
    data может содержать ключ 'cost' (dict из calculate_cost) для отображения затрат.
    report_type: "basic" | "project" | "design"
    """
    REPORTS_DIR.mkdir(exist_ok=True)

    template_name = TEMPLATE_MAP.get(report_type, "report_template.html")
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(template_name)

    now = datetime.now()
    data["generated_at"] = now.strftime("%d.%m.%Y %H:%M")

    # Конвертируем пути изображений в base64 data URI
    raw_images = data.get("images", [])
    if raw_images:
        data["images"] = [_to_data_uri(p) for p in raw_images if p]
        data["images"] = [uri for uri in data["images"] if uri]  # убираем пустые
        logger.info("Встроено изображений в PDF: %d из %d", len(data["images"]), len(raw_images))

    html_content = template.render(**data)
    logger.info("HTML-шаблон '%s' отрендерен", template_name)

    prefix = {"basic": "report", "project": "project_report", "design": "design_report"}.get(report_type, "report")
    filename = f"{prefix}_{now.strftime('%Y-%m-%d_%H-%M')}.pdf"
    output_path = REPORTS_DIR / filename

    HTML(string=html_content).write_pdf(str(output_path))
    logger.info("PDF сохранён: %s", output_path)

    return str(output_path)
