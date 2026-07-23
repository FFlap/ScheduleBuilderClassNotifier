import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _load_env_var(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Create a .env file with {name}=<value>.")
    return value


def load_schedule_urls(path: Path | str | None = None) -> list[str]:
    urls_path = Path(path) if path else Path(__file__).with_name("scheduleUrls.txt")
    urls: list[str] = []

    with urls_path.open() as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)

    if not urls:
        raise RuntimeError(f"No schedule URLs found in {urls_path}.")

    return urls


_load_env_file(Path(__file__).with_name(".env"))
NTFY_TOPIC_URL: str = _load_env_var("NTFY_TOPIC_URL")
