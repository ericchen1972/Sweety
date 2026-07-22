from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable


class PersonaSafetyError(RuntimeError):
    code = "persona_safety_error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class PersonaRejectedError(PersonaSafetyError):
    code = "custom_persona_rejected"


class PersonaReviewUnavailable(PersonaSafetyError):
    code = "persona_review_unavailable"


_LINK_PATTERN = re.compile(
    r"(?ix)"
    r"(?:https?|hxxps?)\s*:\s*/\s*/"
    r"|\b(?:ftp|mailto|tel|tg)\s*:"
    r"|\bwww\s*\."
    r"|\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\s*\.\s*)+[a-z]{2,63}\b"
    r"|\b[\w.+-]+\s*@\s*(?:[a-z0-9-]+\s*\.\s*)+[a-z]{2,63}\b"
    r"|\b(?:\d{1,3}\s*\.\s*){3}\d{1,3}\b"
)

_ABUSE_PATTERNS = (
    re.compile(r"(?:任務|目標|目的).{0,30}(?:介紹|推銷|宣傳|說服|招募|加入|註冊|下載|投資|購買|匯款|聯絡)", re.I | re.S),
    re.compile(r"(?:引導|要求|鼓勵|說服).{0,30}(?:投資|購買|匯款|付款|註冊|下載|加入|聯絡)", re.I | re.S),
    re.compile(r"(?:telegram|whatsapp|line\s*id|微信|wechat|加好友|外部聯絡)", re.I),
    re.compile(r"(?:忽略|推翻|覆寫|取代|否定|繞過).{0,24}(?:system|系統|prompt|提示|規則|指令)", re.I | re.S),
)


def normalize_safety_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    text = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", text)
    return text.replace("[.]", ".").replace("(.)", ".").replace("(dot)", ".")


def contains_external_link(value: str) -> bool:
    return bool(_LINK_PATTERN.search(normalize_safety_text(value)))


def contains_obvious_persona_abuse(value: str) -> bool:
    text = normalize_safety_text(value)
    return contains_external_link(text) or any(pattern.search(text) for pattern in _ABUSE_PATTERNS)


class PersonaSafetyGuard:
    def __init__(self) -> None:
        self._approved_digests: set[str] = set()

    def validate(self, text: str, classifier: Callable[[str], bool]) -> None:
        normalized = normalize_safety_text(text).strip()
        if contains_obvious_persona_abuse(normalized):
            raise PersonaRejectedError()

        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if digest in self._approved_digests:
            return

        try:
            allowed = classifier(normalized)
        except PersonaSafetyError:
            raise
        except Exception as exc:
            raise PersonaReviewUnavailable() from exc
        if allowed is not True:
            raise PersonaRejectedError()
        self._approved_digests.add(digest)
