import sys


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--macos-self-check":
        try:
            from sweety_app.macos_checks import self_check
            self_check(sys.argv[2])
        except Exception:
            raise SystemExit(1)
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--windows-self-check":
        # Avoid a modal PyInstaller error dialog trapping unattended CI checks.
        try:
            from sweety_app.portable_checks import self_check
            self_check(sys.argv[2])
        except Exception:
            import json
            from pathlib import Path
            import traceback
            report = Path(sys.argv[2])
            if not report.exists():
                report.write_text(json.dumps({'ok': False, 'traceback': traceback.format_exc()}), encoding='utf-8')
            raise SystemExit(1)
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--okline-self-check":
        import json
        from pathlib import Path
        from sweety_app.okline_session import sdk_factory, node_path
        from sweety_app.config import LOG_ENABLED
        api = sdk_factory()
        try:
            signature = api.transport.signer.sign("offline-self-check", "/offline", "{}")
            report = {"ok": bool(signature), "node": node_path(), "signatureLength": len(signature), "logging": LOG_ENABLED}
            Path(sys.argv[2]).write_text(json.dumps(report))
            if not signature:
                raise RuntimeError("Empty offline signature")
        finally:
            api.close()
        return
    if sys.platform == "win32":
        from sweety_app.windows import main as run_app
    else:
        from sweety_app.__main__ import main as run_app
    run_app()


if __name__ == "__main__":
    main()
