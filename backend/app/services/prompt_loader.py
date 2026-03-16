from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from app.core.config import PROMPTS_DIR


@lru_cache(maxsize=1)
def _get_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def render_prompt(template_name: str, **context: object) -> str:
    template = _get_environment().get_template(template_name)
    return template.render(**context).strip()