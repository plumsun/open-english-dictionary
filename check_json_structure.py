#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set


@dataclass(frozen=True)
class Schema:
    top_level_keys: Set[str]
    definition_keys: Set[str]
    comparison_keys: Set[str]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate dictionary JSON files against the structure described in "
            "lib/query.py system_instructions."
        )
    )
    parser.add_argument(
        "--dictionary-dir",
        type=Path,
        default=Path("dictionary"),
        help="Directory containing JSON dictionary entries.",
    )
    parser.add_argument(
        "--instructions-file",
        type=Path,
        default=Path("lib/query.py"),
        help="File that defines system_instructions.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display successful validations as well.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after validating this many files.",
    )
    args = parser.parse_args()

    try:
        instructions = extract_system_instructions(args.instructions_file)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    examples = extract_example_jsons(instructions)
    if not examples:
        print(
            "Error: No JSON examples could be parsed from system_instructions.",
            file=sys.stderr,
        )
        return 1

    schema = build_schema(examples)
    total = 0
    failures = 0
    invalid_files: List[Path] = []
    for json_path in sorted(args.dictionary_dir.glob("*.json")):
        total += 1
        errors = validate_json_file(json_path, schema)
        if errors:
            failures += 1
            print(f"{json_path}:")
            for err in errors:
                print(f"  - {err}")
            invalid_files.append(json_path)
        elif args.verbose:
            print(f"{json_path}: OK")

        if args.limit is not None and total >= args.limit:
            break

    if failures:
        print(f"\nValidation failed for {failures} of {total} files.")
        prompt_delete_and_regenerate(invalid_files)
        return 1

    print(f"All {total} files passed validation.")
    return 0


def extract_system_instructions(instructions_path: Path) -> str:
    if not instructions_path.is_file():
        raise ValueError(f"Instructions file not found: {instructions_path}")

    content = instructions_path.read_text(encoding="utf-8")
    match = re.search(
        r"system_instructions\s*=\s*(?P<quote>\"\"\"|''')", content, re.MULTILINE
    )
    if not match:
        raise ValueError("Could not locate system_instructions assignment.")

    quote = match.group("quote")
    start = match.end()
    end = find_closing_triple_quote(content, start, quote)
    if end == -1:
        raise ValueError("Unterminated system_instructions triple-quoted string.")

    return content[start:end]


def find_closing_triple_quote(text: str, start: int, quote: str) -> int:
    cursor = start
    while True:
        idx = text.find(quote, cursor)
        if idx == -1:
            return -1
        # Triple quotes inside the string are extremely unlikely and would
        # require escaping; the instructions file does not escape quotes.
        return idx


def extract_example_jsons(instructions: str) -> List[dict]:
    examples: List[dict] = []
    marker = "**模型输出:**"
    cursor = 0
    while True:
        marker_idx = instructions.find(marker, cursor)
        if marker_idx == -1:
            break

        brace_idx = instructions.find("{", marker_idx)
        if brace_idx == -1:
            break

        block, next_cursor = extract_json_block(instructions, brace_idx)
        try:
            examples.append(json.loads(block))
        except json.JSONDecodeError:
            pass
        cursor = next_cursor

    return examples


def extract_json_block(text: str, start: int) -> tuple[str, int]:
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1], idx + 1

    raise ValueError("Unterminated JSON block found in instructions.")


def build_schema(examples: Iterable[dict]) -> Schema:
    examples = list(examples)
    top_level_keys = intersect_keysets(example.keys() for example in examples)
    definition_keys = intersect_nested_keysets(
        example.get("definitions", []) for example in examples
    )
    comparison_keys = intersect_nested_keysets(
        example.get("comparison", []) for example in examples
    )

    return Schema(
        top_level_keys=top_level_keys,
        definition_keys=definition_keys,
        comparison_keys=comparison_keys,
    )


def intersect_keysets(key_iters: Iterable[Iterable[str]]) -> Set[str]:
    iterator = iter(key_iters)
    try:
        first = set(next(iterator))
    except StopIteration:
        return set()

    for keys in iterator:
        first &= set(keys)
    return first


def intersect_nested_keysets(
    nested_items: Iterable[Iterable[dict]],
) -> Set[str]:
    combined: Set[str] | None = None
    for collection in nested_items:
        for item in collection:
            if combined is None:
                combined = set(item.keys())
            else:
                combined &= set(item.keys())

    return combined or set()


def validate_json_file(path: Path, schema: Schema) -> List[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return ["Top-level JSON element must be an object."]

    errors: List[str] = []

    missing_top = schema.top_level_keys - data.keys()
    if missing_top:
        errors.append(f"Missing top-level keys: {sorted(missing_top)}")

    type_checks = (
        ("word", str),
        ("pronunciation", str),
        ("concise_definition", str),
    )
    for key, expected in type_checks:
        value = data.get(key)
        if not isinstance(value, expected) or not value.strip():
            errors.append(f"'{key}' must be a non-empty {expected.__name__}.")

    forms = data.get("forms")
    if not isinstance(forms, dict):
        errors.append("'forms' must be an object.")
    else:
        for sub_key, sub_value in forms.items():
            if not isinstance(sub_key, str):
                errors.append("Form keys must be strings.")
                break
            if not isinstance(sub_value, str) or not sub_value.strip():
                errors.append(f"'forms.{sub_key}' must be a non-empty string.")

    errors.extend(validate_entries(data.get("definitions"), "definitions", schema.definition_keys))
    errors.extend(validate_entries(data.get("comparison"), "comparison", schema.comparison_keys))

    unexpected = set(data.keys()) - schema.top_level_keys
    if unexpected:
        errors.append(f"Unexpected top-level keys: {sorted(unexpected)}")

    return errors


def validate_entries(value, field_name: str, required_keys: Set[str]) -> List[str]:
    if not isinstance(value, list) or not value:
        return [f"'{field_name}' must be a non-empty list."]

    entry_errors: List[str] = []
    for index, item in enumerate(value):
        prefix = f"{field_name}[{index}]"
        if not isinstance(item, dict):
            entry_errors.append(f"{prefix} must be an object.")
            continue

        missing = required_keys - item.keys()
        if missing:
            entry_errors.append(f"{prefix} missing keys: {sorted(missing)}")

        for key in required_keys:
            field_value = item.get(key)
            if not isinstance(field_value, str) or not field_value.strip():
                entry_errors.append(f"{prefix}.{key} must be a non-empty string.")

        unexpected = set(item.keys()) - required_keys
        if unexpected:
            entry_errors.append(
                f"{prefix} contains unexpected keys: {sorted(unexpected)}"
            )

    return entry_errors


def prompt_delete_and_regenerate(files: List[Path]) -> None:
    if not files:
        return

    print(
        "\nThe files listed above deviate from the expected structure. "
        "You may delete them and regenerate fresh entries."
    )
    if not sys.stdin.isatty():
        print("Skipping deletion prompt because the session is non-interactive.")
        return

    response = input(
        "Delete these files now so they can be regenerated? [y/N]: "
    ).strip().lower()
    if response not in {"y", "yes"}:
        print("No files deleted. Regenerate them manually when convenient.")
        return

    for path in files:
        try:
            path.unlink()
            print(f"Deleted {path}")
        except OSError as exc:
            print(f"Failed to delete {path}: {exc}")

    print("Deletion complete. Regenerate the removed entries before publishing.")


if __name__ == "__main__":
    sys.exit(main())
