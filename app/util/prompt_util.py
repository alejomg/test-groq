from pathlib import Path

from loguru import logger


def _read_prompt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_prompts_path() -> Path:
    return Path(__file__).parent.parent / "prompts"


def _get_prompt(prompt_file: str) -> str:
    return _read_prompt_text(get_prompts_path() / prompt_file)


def get_system_prompt(role: str) -> str:

    role_name = getattr(role, "value", role)
    logger.info(f"[*** Prompts ***] get_system_prompt role: {role_name} ")

    role_prompt_file = f"system_{role_name.lower()}_prompt.txt"

    role_prompt_path = get_prompts_path() / role_prompt_file

    if role_name != "NOT_SUPPORTED" and role_prompt_path.exists():
        return _read_prompt_text(role_prompt_path)

    return _get_prompt("system_prompt.txt")
