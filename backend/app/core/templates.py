from pathlib import Path
from .config import settings


def list_placeholders(template_name: str) -> list[str]:
    md = Path(settings.templates_path, f"{template_name}.md").read_text()
    return [p.strip("{}") for p in set(__import__("re").findall(r"{{(.*?)}}", md))]
