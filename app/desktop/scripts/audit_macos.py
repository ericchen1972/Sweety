"""Reject bundled Mach-O files incompatible with the selected macOS target."""
import argparse
import re
import subprocess
from pathlib import Path

MAGICS = {bytes.fromhex(value) for value in (
    "feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca"
)}


def validate_binary(architectures: str, load_commands: str, target: str) -> None:
    if target not in architectures.split():
        raise ValueError(f"missing {target} architecture: {architectures.strip()}")
    versions = []
    for command in re.split(r"(?m)^\s*cmd\s+", load_commands):
        if command.startswith("LC_BUILD_VERSION"):
            match = re.search(r"\bminos\s+(\d+(?:\.\d+)*)", command)
        elif command.startswith("LC_VERSION_MIN_MACOSX"):
            match = re.search(r"\bversion\s+(\d+(?:\.\d+)*)", command)
        else:
            continue
        if match:
            versions.append(tuple(int(x) for x in match[1].split(".")))
    if not versions:
        raise ValueError("missing macOS minimum OS load command")
    if any((version + (0, 0, 0))[:3] > (12, 7, 0) for version in versions):
        raise ValueError(f"minimum OS exceeds macOS 12.7: {versions}")


def audit_bundle(root: Path, target: str) -> int:
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            if stream.read(4) not in MAGICS:
                continue
        architectures = subprocess.check_output(["lipo", "-archs", str(path)], text=True)
        commands = subprocess.check_output(["otool", "-l", str(path)], text=True)
        try:
            validate_binary(architectures, commands, target)
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from error
        count += 1
    if not count:
        raise ValueError(f"no Mach-O files found in {root}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--arch", required=True, choices=("arm64", "x86_64"))
    args = parser.parse_args()
    print(f"Passed macOS 12.7 audit: {audit_bundle(args.bundle, args.arch)} Mach-O files ({args.arch})")
