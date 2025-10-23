#!/usr/bin/env python3
"""
Pack the dictionary directory into multiple archive formats.
Supports: zip, tar.gz, tar.bz2, tar.xz
"""

import argparse
import shutil
import sys
from pathlib import Path


def pack_directory(
    source_dir: Path,
    output_dir: Path,
    formats: list[str],
    base_name: str = "open-c2e-dictionary",
) -> list[Path]:
    """
    Pack the source directory into specified archive formats.

    Args:
        source_dir: Directory to pack
        output_dir: Directory to save archives
        formats: List of archive formats (zip, tar.gz, tar.bz2, tar.xz)
        base_name: Base name for output archives

    Returns:
        List of created archive paths
    """
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    created_archives = []

    format_mapping = {
        "zip": "zip",
        "tar.gz": "gztar",
        "tar.bz2": "bztar",
        "tar.xz": "xztar",
    }

    for fmt in formats:
        if fmt not in format_mapping:
            print(f"Warning: Unknown format '{fmt}', skipping", file=sys.stderr)
            continue

        archive_format = format_mapping[fmt]
        output_base = output_dir / base_name

        print(f"Creating {fmt} archive...")
        try:
            archive_path = shutil.make_archive(
                str(output_base),
                archive_format,
                root_dir=source_dir.parent,
                base_dir=source_dir.name,
            )
            created_path = Path(archive_path)

            # Rename to include format in name if multiple formats
            if len(formats) > 1:
                final_path = output_dir / f"{base_name}-{fmt.replace('.', '-')}{created_path.suffix}"
                if created_path != final_path:
                    created_path.rename(final_path)
                    created_path = final_path

            created_archives.append(created_path)
            print(f"✓ Created: {created_path} ({created_path.stat().st_size / 1024 / 1024:.2f} MB)")

        except Exception as e:
            print(f"✗ Failed to create {fmt} archive: {e}", file=sys.stderr)

    return created_archives


def main():
    parser = argparse.ArgumentParser(
        description="Pack the dictionary directory into archive formats"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("dictionary"),
        help="Source directory to pack (default: dictionary)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist"),
        help="Output directory for archives (default: dist)",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=["zip", "tar.gz", "tar.bz2", "tar.xz"],
        default=["zip", "tar.gz"],
        help="Archive formats to create (default: zip tar.gz)",
    )
    parser.add_argument(
        "--name",
        default="open-c2e-dictionary",
        help="Base name for output archives (default: open-c2e-dictionary)",
    )

    args = parser.parse_args()

    try:
        archives = pack_directory(
            source_dir=args.source,
            output_dir=args.output,
            formats=args.formats,
            base_name=args.name,
        )

        if archives:
            print(f"\n✓ Successfully created {len(archives)} archive(s)")
            return 0
        else:
            print("\n✗ No archives were created", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
