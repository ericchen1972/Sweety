from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any, Protocol

import requests


class HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


class AboutContentError(RuntimeError):
    pass


class _AboutSanitizer(HTMLParser):
    allowed_tags = {"main", "header", "section", "article", "footer", "div", "span", "h1", "h2", "h3", "p", "ul", "ol", "li", "strong", "em", "br", "a", "img"}
    void_tags = {"br", "img"}
    blocked_tags = {"head", "script", "style", "iframe", "object", "embed", "form", "input", "button", "textarea", "select", "option", "link", "meta", "base"}
    blocked_void_tags = {"input", "link", "meta", "base"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.blocked_tags:
            if tag not in self.blocked_void_tags:
                self.blocked_depth += 1
            return
        if self.blocked_depth or tag not in self.allowed_tags:
            return

        safe_attrs: list[str] = []
        for name, value in attrs:
            name = name.lower()
            value = value or ""
            if name == "class" and re.fullmatch(r"[a-zA-Z0-9 _-]{1,200}", value):
                safe_attrs.append(f'class="{html.escape(value, quote=True)}"')
            elif tag == "a" and name == "href" and value.startswith("https://"):
                safe_attrs.extend([
                    f'href="{html.escape(value, quote=True)}"',
                    'target="_blank"',
                    'rel="noreferrer noopener"',
                ])
            elif tag == "img" and name == "src" and value.startswith("https://sweety.tw/"):
                safe_attrs.append(f'src="{html.escape(value, quote=True)}"')
            elif tag == "img" and name == "alt":
                safe_attrs.append(f'alt="{html.escape(value, quote=True)}"')
            elif tag == "img" and name in {"width", "height"} and re.fullmatch(r"[1-9][0-9]{0,3}", value):
                safe_attrs.append(f'{name}="{value}"')
            elif tag == "img" and name == "loading" and value in {"lazy", "eager"}:
                safe_attrs.append(f'loading="{value}"')
            elif tag == "img" and name == "decoding" and value in {"async", "sync", "auto"}:
                safe_attrs.append(f'decoding="{value}"')
        suffix = f" {' '.join(safe_attrs)}" if safe_attrs else ""
        self.parts.append(f"<{tag}{suffix}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.blocked_tags and self.blocked_depth:
            self.blocked_depth -= 1
            return
        if not self.blocked_depth and tag in self.allowed_tags and tag not in self.void_tags:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth:
            self.parts.append(html.escape(data))


def sanitize_about_html(source: str) -> str:
    parser = _AboutSanitizer()
    parser.feed(source)
    parser.close()
    return "".join(parser.parts).strip()


class AboutContentClient:
    def __init__(self, url: str, session: HttpSession | None = None) -> None:
        self.url = url
        self.session = session or requests.Session()

    def load(self) -> str:
        try:
            response = self.session.get(self.url, timeout=5)
            response.raise_for_status()
            response.encoding = "utf-8"
            content = str(response.text)
            sanitized = sanitize_about_html(content)
            if not sanitized:
                raise ValueError("empty about content")
            return sanitized
        except Exception as exc:
            raise AboutContentError("about_content_unavailable") from exc
