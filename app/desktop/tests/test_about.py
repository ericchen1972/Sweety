from __future__ import annotations

import re
from pathlib import Path

from sweety_app.about import AboutContentClient, sanitize_about_html


FRONTEND_CSS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "index.css"


def test_sanitizer_keeps_semantic_content_and_removes_active_markup():
    source = """
    <html><head><style>body{display:none}</style><script>alert(1)</script></head><body>
      <main class="about-page"><h1 onclick="alert(1)">關於 Sweety</h1>
      <p>安全內容</p><form><input value="secret"></form>
      <a href="javascript:alert(1)">危險</a>
      <a href="https://sweety.tw/privacy">隱私</a></main>
    </body></html>
    """

    result = sanitize_about_html(source)

    assert "關於 Sweety" in result
    assert "安全內容" in result
    assert "<script" not in result
    assert "onclick" not in result
    assert "<form" not in result
    assert "<input" not in result
    assert "javascript:" not in result
    assert 'href="https://sweety.tw/privacy"' in result


def test_sanitizer_keeps_safe_author_card_and_remote_portrait():
    source = """
    <section class="author-section">
      <article class="author-card">
        <img class="author-avatar" src="https://sweety.tw/images/eric.png"
             alt="Eric" width="256" height="256" loading="lazy"
             decoding="async" onerror="alert(1)">
        <div><h2>Eric / 網站 / AI 工程師</h2></div>
      </article>
      <img src="javascript:alert(1)" alt="unsafe">
      <img src="https://tracking.example/pixel.png" alt="third-party">
    </section>
    """

    result = sanitize_about_html(source)

    assert '<article class="author-card">' in result
    assert '<img class="author-avatar" src="https://sweety.tw/images/eric.png"' in result
    assert 'alt="Eric"' in result
    assert 'width="256"' in result
    assert 'height="256"' in result
    assert 'loading="lazy"' in result
    assert 'decoding="async"' in result
    assert "onerror" not in result
    assert "javascript:" not in result
    assert "tracking.example" not in result


def test_frontend_styles_remote_author_card_and_circular_portrait():
    css = FRONTEND_CSS.read_text(encoding="utf-8")

    assert re.search(r"\.about-content \.author-card\s*\{", css)
    assert re.search(r"\.about-content \.author-avatar\s*\{", css)
    assert "rounded-full" in css
    assert "dark:bg-zinc-900" in css


def test_client_decodes_remote_document_as_utf8():
    class Response:
        encoding = None

        def raise_for_status(self):
            return None

        @property
        def text(self):
            return "<main><h1>關於 Sweety</h1></main>".encode().decode(
                self.encoding or "latin-1"
            )

    class Session:
        def get(self, _url, timeout):
            assert timeout == 5
            return Response()

    content = AboutContentClient("https://example.test/about", Session()).load()

    assert "關於 Sweety" in content
