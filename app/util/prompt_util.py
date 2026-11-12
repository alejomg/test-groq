from pathlib import Path

# PROMPT TYPES
SYSTEM_PROMPT_FILE = "system_prompt.txt"


def _read_prompt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_prompts_path() -> Path:
    return Path(__file__).parent.parent / "prompts"


def _get_prompt(prompt_file: str) -> str:
    return _read_prompt_text(get_prompts_path() / prompt_file)


def get_system_prompt() -> str:
    return _get_prompt(SYSTEM_PROMPT_FILE)
