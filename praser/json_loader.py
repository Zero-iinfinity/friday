import json
from pathlib import Path


def load(path):
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError("json file not found: " + str(p))
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError("invalid json in " + str(p) + ": " + str(e)) from e
    if not isinstance(data, dict) or "operations" not in data:
        raise ValueError("json must be an object with an 'operations' list")
    return data