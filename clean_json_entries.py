#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Tuple


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Remove empty key-value pairs from dictionary JSON files and drop "
            "objects or arrays that become empty."
        )
    )
    parser.add_argument(
        "--dictionary-dir",
        type=Path,
        default=Path("dictionary"),
        help="Directory containing JSON dictionary entries.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write cleaned data back to disk. Without this flag, a dry run is performed.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation level for rewritten JSON files.",
    )
    args = parser.parse_args()

    try:
        files = sorted(iter_dictionary_files(args.dictionary_dir))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not files:
        print("No JSON files found to clean.", file=sys.stderr)
        return 1

    total = 0
    changed = 0
    skipped = 0

    for path in files:
        total += 1
        try:
            original_text = path.read_text(encoding="utf-8")
            data = json.loads(original_text)
        except (OSError, json.JSONDecodeError) as exc:
            skipped += 1
            print(f"Skipping {path}: {exc}", file=sys.stderr)
            continue

        cleaned, removed_any = clean_value(data)
        if cleaned is None:
            cleaned = {}

        if not removed_any:
            continue

        changed += 1
        if args.apply:
            try:
                path.write_text(
                    json.dumps(cleaned, ensure_ascii=False, indent=args.indent) + "\n",
                    encoding="utf-8",
                )
                print(f"Cleaned {path}")
            except OSError as exc:
                skipped += 1
                print(f"Failed to write {path}: {exc}", file=sys.stderr)
        else:
            print(f"[Dry Run] Would clean {path}")

    mode = "Dry run" if not args.apply else "Apply"
    print(
        f"{mode} complete. Processed {total} files, cleaned {changed}, skipped {skipped}."
    )
    return 0


def iter_dictionary_files(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        raise ValueError(f"Dictionary directory not found: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Dictionary path is not a directory: {directory}")
    return directory.glob("*.json")


def clean_value(value: Any) -> Tuple[Any, bool]:
    """
    Recursively clean a JSON-compatible Python value.

    Returns a tuple of (cleaned_value, removed_anything).
    If cleaned_value becomes empty, None is returned.
    """
    removed_anything = False

    if isinstance(value, str):
        if value.strip():
            return value, False
        return None, True

    if isinstance(value, list):
        cleaned_items = []
        for item in value:
            cleaned_item, removed = clean_value(item)
            removed_anything = removed_anything or removed
            if cleaned_item is not None:
                cleaned_items.append(cleaned_item)
        if cleaned_items:
            return cleaned_items, removed_anything
        return None, True

    if isinstance(value, dict):
        cleaned_dict = {}
        for key, item in value.items():
            cleaned_item, removed = clean_value(item)
            removed_anything = removed_anything or removed
            if cleaned_item is not None:
                cleaned_dict[key] = cleaned_item
            else:
                removed_anything = True
        if cleaned_dict:
            return cleaned_dict, removed_anything
        return None, True

    # numeric, boolean, null (None)
    return value, False


if __name__ == "__main__":
    sys.exit(main())
