import os
from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, Template


@lru_cache
def get_prompt_template(template_name: str) -> Template:
    template_dir = os.path.join(os.path.dirname(__file__), "../prompts")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    return template

def map_exception_to_error(exception: Exception) -> dict:
    """Map an exception to a user-friendly error message and log details.

    Args:
        exception (Exception): The exception to map.
    Returns:
        dict: A dictionary containing 'user_message' and 'log_details'.
    """
    user_message = "An unexpected error occurred. Please try again later."
    log_details = {"exception_type": type(exception).__name__, "exception_message": str(exception)}

    return {
        "user_message": user_message,
        "log_details": log_details,
    }