import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

def test_macho_compatibility_load_commands():
    from audit_macos import validate_binary
    modern = "cmd LC_BUILD_VERSION\n platform 1\n minos 12.7\n sdk 15.0"
    legacy = "cmd LC_VERSION_MIN_MACOSX\n version 10.15\n sdk 13.0"
    validate_binary("arm64", modern, "arm64")
    validate_binary("x86_64", legacy, "x86_64")
    for archs, output, target in [
        ("arm64", modern.replace("12.7", "13.0"), "arm64"),
        ("x86_64", legacy.replace("10.15", "12.8"), "x86_64"),
        ("x86_64", legacy, "arm64"),
        ("arm64", "cmd LC_UUID", "arm64"),
        ("arm64", modern + "\n" + modern.replace("12.7", "14.0"), "arm64"),
    ]:
        with pytest.raises(ValueError):
            validate_binary(archs, output, target)
