from __future__ import annotations

from sweety_app.about import AboutContentClient, sanitize_about_html


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
