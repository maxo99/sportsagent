import os
from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, Template

prompt_loader = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "prompts"))
)


@lru_cache
def get_queryparser_template(template_name: str) -> Template:
    template = prompt_loader.get_template(template_name)
    return template
