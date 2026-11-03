"""Edit one platform's release after its installer has been uploaded and verified.

Start with the latest production manifest to avoid reverting another platform.
Legacy fields deliberately remain frozen for pre-2.0.3 clients.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
from urllib.parse import urlparse


def with_release(payload: dict, platform: str, version: str, url: str) -> dict:
    if platform not in ("windows", "macos") or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Invalid platform or version")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("An HTTPS download URL is required")
    result = deepcopy(payload)
    if not isinstance(result.get("platforms", {}), dict):
        raise ValueError("Invalid platforms object")
    result.setdefault("platforms", {})[platform] = {"latestVersion": version, "downloadUrl": url}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[2] / "web/sweety-update.json")
    parser.add_argument("--platform", choices=("windows", "macos"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text())
    result = with_release(payload, args.platform, args.version, args.url)
    args.manifest.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Updated only {args.platform}: {args.version}")


if __name__ == "__main__":
    main()
