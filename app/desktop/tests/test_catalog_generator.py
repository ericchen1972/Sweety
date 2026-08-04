from __future__ import annotations

import importlib.util
from pathlib import Path


GENERATOR_PATH = Path(__file__).parents[2] / "tools" / "generate_persona_catalogs.py"
SPEC = importlib.util.spec_from_file_location("generate_persona_catalogs", GENERATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def test_catalog_compatibility_block_generation_is_idempotent():
    source = '''DEFAULT_SYSTEM_PROMPT_TEMPLATE = "prompt"

from .catalog_personas import BASE_PERSONAS

BASE_PERSONA_TEXT = {persona["id"]: persona["content"]["zh-TW"] for persona in BASE_PERSONAS}

BASE_WEAPON_TEXT = {"persona-only": ""}
'''

    once = generator.update_catalog_module(source)
    twice = generator.update_catalog_module(once)

    assert twice == once
    assert once.count("from .catalog_personas import BASE_PERSONAS") == 1
    assert once.count("BASE_PERSONA_TEXT =") == 1
    assert once.index("from .catalog_personas import BASE_PERSONAS") < once.index("BASE_PERSONA_TEXT =")


def test_generator_requires_all_three_supported_locales():
    assert generator.SUPPORTED_LOCALES == ("zh-TW", "en", "ja")


def test_generator_keeps_ai_persona_source_in_traditional_chinese():
    source = 'BASE_WEAPON_TEXT = {"persona-only": ""}\n'
    generated = generator.update_catalog_module(source)
    assert 'persona["content"]["zh-TW"]' in generated
