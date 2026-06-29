from pathlib import Path
from typing import Dict


def load_cookies(filename: str) -> Dict[str, str]:
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Файл с куками не найден: {filename}")

    cookies = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]

    print(f"✅ Загружено {len(cookies)} кук из {filename}")
    return cookies
