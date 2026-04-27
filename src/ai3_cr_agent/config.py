from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RuntimeConfig:
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: int = 60


def load_runtime_config() -> RuntimeConfig:
    _load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Fill it in AI3_CR_Agent/.env or export it in your shell."
        )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    timeout_seconds = _parse_timeout(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
    return RuntimeConfig(
        openai_api_key=api_key,
        openai_model=model,
        openai_base_url=base_url.rstrip("/"),
        openai_timeout_seconds=timeout_seconds,
    )


def _parse_timeout(value: str) -> int:
    try:
        timeout = int(value)
    except ValueError as exc:
        raise RuntimeError("OPENAI_TIMEOUT_SECONDS must be an integer.") from exc
    if timeout <= 0:
        raise RuntimeError("OPENAI_TIMEOUT_SECONDS must be greater than 0.")
    return timeout


def _load_dotenv() -> None:
    for path in _candidate_env_files():
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            item = line.strip()
            if not item or item.startswith("#") or "=" not in item:
                continue
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)


def _candidate_env_files() -> list[Path]:
    cwd = Path.cwd().resolve()
    package_root = Path(__file__).resolve().parents[2]
    return [
        cwd / ".env",
        package_root / ".env",
    ]
