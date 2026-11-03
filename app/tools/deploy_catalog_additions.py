"""Upsert selected canonical personas without replacing the shared prompt or other rows.

Uses the existing local FTP/SSH configuration; backups stay outside the repository.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from ftplib import FTP
import hashlib
import io
import json
from pathlib import Path
import re
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="+")
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    canonical = json.loads((ROOT / "app/catalog/base_personas.json").read_text())
    selected = [p for p in canonical if p["id"] in args.ids]
    if {p["id"] for p in selected} != set(args.ids):
        raise ValueError("Unknown persona IDs")
    args.backup_dir.mkdir(parents=True, exist_ok=True)
    config_text = (ROOT / "web/sftp-config.json").read_text()
    config_text = re.sub(r"^\s*//.*$", "", config_text, flags=re.M)
    config = json.loads(re.sub(r",\s*([}\]])", r"\1", config_text))
    name = ".__sweety_additions_" + secrets.token_hex(8)
    runner_path = "/sweety.tw/" + name + ".php"
    payload_path = "/sweety.tw/" + name + ".json"
    template = (ROOT / "app/tools/catalog_additions_runner.template.php").read_text()
    runner = template.replace("__PAYLOAD__", name + ".json")
    with FTP() as ftp:
        ftp.connect(config["host"], int(config.get("port", 21)), timeout=30)
        ftp.login(config["user"], config["password"])
        ftp.set_pasv(bool(config.get("ftp_passive_mode", True)))
        # Back up the raw DB rows and prompt before any image or DB mutation.
        ftp.storbinary("STOR " + runner_path, io.BytesIO(runner.encode()))
        payload = {"selected": selected, "localizations": [
            {"id": p["id"], "name": p["name"]["ja"], "content": p["content"]["ja"]} for p in canonical
        ]}
        ftp.storbinary("STOR " + payload_path, io.BytesIO(json.dumps(payload, ensure_ascii=False).encode()))
        def execute(mode: str) -> dict:
            result = subprocess.run(
                ["/usr/bin/expect", str(ROOT / "app/tools/synology_ssh.exp"),
                 "/usr/local/bin/php82 /volume1" + runner_path + " " + mode],
                capture_output=True, text=True, timeout=120,
            )
            for line in reversed(result.stdout.splitlines()):
                if line.strip().startswith("{"):
                    value = json.loads(line.strip())
                    if value.get("ok"):
                        return value
                    raise RuntimeError("Catalog operation failed: " + str(value.get("error")))
            raise RuntimeError("Catalog SSH runner returned no result")
        try:
            backup = execute("backup")
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = args.backup_dir / ("db-before-" + stamp + ".json")
            backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2))
            for persona in selected:
                data = (ROOT / "web" / persona["image"].lstrip("/")).read_bytes()
                for remote_root in {"/sweety.tw", "/" + config["remote_path"].strip("/")}:
                    remote = remote_root + persona["image"]
                    # Existing image must be backed up before replacement.
                    existing = io.BytesIO()
                    try:
                        ftp.retrbinary("RETR " + remote, existing.write)
                    except Exception as error:
                        if not str(error).startswith("550"):
                            raise
                    else:
                        suffix = hashlib.sha256(remote.encode()).hexdigest()[:8]
                        (args.backup_dir / f"{persona['id']}-{stamp}-{suffix}.jpg").write_bytes(existing.getvalue())
                    ftp.storbinary("STOR " + remote + ".upload", io.BytesIO(data))
                    check = io.BytesIO()
                    ftp.retrbinary("RETR " + remote + ".upload", check.write)
                    if check.getvalue() != data:
                        raise RuntimeError("Image verification failed")
                    ftp.rename(remote + ".upload", remote)
            result = execute("apply")
            # Publish the API only after its required DB columns exist.
            for filename in ("sweety-catalog.php", "sweety-catalog-lib.php"):
                for remote_root in {"/sweety.tw", "/" + config["remote_path"].strip("/")}:
                    remote = remote_root + "/" + filename
                    old = io.BytesIO()
                    ftp.retrbinary("RETR " + remote, old.write)
                    suffix = hashlib.sha256(remote.encode()).hexdigest()[:8]
                    (args.backup_dir / f"{filename}-{stamp}-{suffix}.bak").write_bytes(old.getvalue())
                    data = (ROOT / "web" / filename).read_bytes()
                    ftp.storbinary("STOR " + remote + ".upload", io.BytesIO(data))
                    check = io.BytesIO()
                    ftp.retrbinary("RETR " + remote + ".upload", check.write)
                    if check.getvalue() != data:
                        raise RuntimeError("API upload verification failed")
                    ftp.rename(remote + ".upload", remote)
            print(json.dumps({"ok": True, "ids": result["ids"], "backup": str(backup_path)}))
        finally:
            for remote in (runner_path, payload_path):
                try:
                    ftp.delete(remote)
                except Exception:
                    pass


if __name__ == "__main__":
    main()
