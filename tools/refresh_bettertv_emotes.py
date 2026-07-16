"""Refresh or verify the checked BTTV emote assets.

The backend's packaged JSON is canonical because analytics consumes it at
runtime. The frontend JSON is a generated copy used by the chat renderer.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DATASET = REPOSITORY_ROOT / "backend/stream_sniper/analytics/data/bttv_emotes.json"
FRONTEND_DATASET = REPOSITORY_ROOT / "frontend/lib/bettertv_emotes.json"
BTTV_TOP_EMOTES_URL = "https://api.betterttv.net/3/emotes/shared/top"
PAGE_SIZE = 100


def _read_dataset(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(
        isinstance(name, str) and isinstance(emote_id, str)
        for name, emote_id in value.items()
    ):
        raise ValueError(f"Expected a string-to-string BTTV map in {path}")
    return value


def _atomic_write_dataset(path: Path, emotes: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(dict(sorted(emotes.items())), file, indent=4, ensure_ascii=False)
            file.write("\n")
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def fetch_shared_emotes(session: requests.Session | None = None) -> dict[str, str]:
    client: Any = session or requests
    fetched: dict[str, str] = {}
    for offset in tqdm(range(0, 1_000_000, PAGE_SIZE), desc="BTTV pages"):
        response = client.get(
            BTTV_TOP_EMOTES_URL,
            params={"offset": offset, "limit": PAGE_SIZE},
            timeout=30,
        )
        response.raise_for_status()
        page = response.json()
        if not page:
            break
        for item in page:
            emote = item["emote"]
            fetched[emote["code"]] = emote["id"]
    return fetched


def refresh() -> int:
    emotes = fetch_shared_emotes()
    if not emotes:
        raise RuntimeError("BTTV refresh returned no emotes")
    _atomic_write_dataset(CANONICAL_DATASET, emotes)
    _atomic_write_dataset(FRONTEND_DATASET, emotes)
    print(f"Wrote {len(emotes)} emotes to canonical and frontend datasets")
    return 0


def sync() -> int:
    emotes = _read_dataset(CANONICAL_DATASET)
    _atomic_write_dataset(FRONTEND_DATASET, emotes)
    print(f"Synchronized {len(emotes)} canonical emotes to the frontend")
    return 0


def check() -> int:
    canonical = _read_dataset(CANONICAL_DATASET)
    frontend = _read_dataset(FRONTEND_DATASET)
    if canonical != frontend:
        print("BTTV datasets differ; run tools/refresh_bettertv_emotes.py")
        return 1
    print(f"BTTV datasets match semantically ({len(canonical)} emotes)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true", help="fetch BTTV and replace both datasets")
    mode.add_argument("--check", action="store_true", help="fail if the generated frontend copy has drifted")
    args = parser.parse_args()
    if args.refresh:
        return refresh()
    if args.check:
        return check()
    return sync()


if __name__ == "__main__":
    raise SystemExit(main())
