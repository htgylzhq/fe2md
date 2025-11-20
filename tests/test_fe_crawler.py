import io

import fe_crawler
from bs4 import BeautifulSoup


def test_download_image_writes_file(monkeypatch, tmp_path):
    class DummyResponse:
        def __init__(self, content: bytes):
            self.raw = io.BytesIO(content)

        def raise_for_status(self):
            return None

    content = b"helloworld"
    monkeypatch.setattr(
        fe_crawler.requests,
        "get",
        lambda url, stream=True, timeout=10: DummyResponse(content),
    )

    rel_path = fe_crawler.download_image(
        "https://example.com/img/file.png", tmp_path, prefix="pre"
    )

    dest = tmp_path / "assets" / "pre_file.png"
    assert rel_path == "./assets/pre_file.png"
    assert dest.exists()
    assert dest.read_bytes() == content


def test_process_element_handles_image_and_prefix(monkeypatch, tmp_path):
    img_html = '<img src="img/sample.png"/>'
    soup = BeautifulSoup(img_html, "html.parser")
    img_tag = soup.img

    captured = {}

    def fake_download(url, output_dir, prefix=""):
        captured["url"] = url
        captured["prefix"] = prefix
        return "./assets/fake.png"

    monkeypatch.setattr(fe_crawler, "download_image", fake_download)

    output = fe_crawler.process_element(
        img_tag, "https://example.com/base/", tmp_path, prefix="pfx"
    )

    assert 'img src="./assets/fake.png"' in output
    assert captured == {
        "url": "https://example.com/base/img/sample.png",
        "prefix": "pfx",
    }


def test_process_element_formats_lists_and_blanks(monkeypatch, tmp_path):
    html = """
    <div class="mondai">
      Text <span class="bb">a</span><br>
      <ul><li>Option</li></ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    mondai_div = soup.find("div", class_="mondai")

    monkeypatch.setattr(fe_crawler, "download_image", lambda *args, **kwargs: None)

    output = fe_crawler.process_element(
        mondai_div, "https://example.com/base/", tmp_path, prefix=""
    )

    assert "<u>&emsp;a&emsp;</u>" in output
    assert "- Option" in output
    assert "Text" in output


def test_process_element_adds_newline_before_list(monkeypatch, tmp_path):
    html = "<div>Text line<ul><li>List Item</li></ul></div>"
    soup = BeautifulSoup(html, "html.parser")
    div = soup.div

    monkeypatch.setattr(fe_crawler, "download_image", lambda *args, **kwargs: None)

    output = fe_crawler.process_element(
        div, "https://example.com", tmp_path
    )

    # We expect a blank line between text and list
    assert "Text line\n\n- List Item" in output


def test_process_element_handles_span_bb_in_list(monkeypatch, tmp_path):
    html = '<ul><li>Text with <span class="bb">a</span> blank</li></ul>'
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.ul

    monkeypatch.setattr(fe_crawler, "download_image", lambda *args, **kwargs: None)

    output = fe_crawler.process_element(
        ul, "https://example.com", tmp_path
    )

    # Should convert span.bb to fill-in-blank format
    assert "- Text with <u>&emsp;a&emsp;</u> blank" in output


def test_process_element_adds_newline_after_list(monkeypatch, tmp_path):
    html = "<div><ul><li>Item</li></ul>Following text</div>"
    soup = BeautifulSoup(html, "html.parser")
    div = soup.div

    monkeypatch.setattr(fe_crawler, "download_image", lambda *args, **kwargs: None)

    output = fe_crawler.process_element(
        div, "https://example.com", tmp_path
    )

    # Should have blank line between list and following text
    assert "- Item\n\nFollowing text" in output


def test_process_element_preserves_u_tags(monkeypatch, tmp_path):
    html = "<div>Text with <u>underlined content</u> here</div>"
    soup = BeautifulSoup(html, "html.parser")
    div = soup.div

    monkeypatch.setattr(fe_crawler, "download_image", lambda *args, **kwargs: None)

    output = fe_crawler.process_element(
        div, "https://example.com", tmp_path
    )

    # Should preserve u tags
    assert "<u>underlined content</u>" in output


def test_process_list_handles_nested_lists(monkeypatch, tmp_path):
    html = """
    <ul>
        <li>Item 1
            <ol>
                <li>Nested 1</li>
                <li>Nested 2</li>
            </ol>
        </li>
        <li>Item 2</li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.ul

    monkeypatch.setattr(fe_crawler, "download_image", lambda *args, **kwargs: None)

    output = fe_crawler.process_list(
        ul, "https://example.com", tmp_path, ""
    )

    # Should have properly indented nested list
    assert "- Item 1\n  - Nested 1\n  - Nested 2\n- Item 2" in output







def test_main_writes_output_when_main_container_present(monkeypatch, tmp_path):
    html = """
    <div class="main kako">
      <div class="mondai">Question text</div>
    </div>
    """

    class DummyResponse:
        def __init__(self, text):
            self.text = text
            self._encoding = "utf-8"
            self.apparent_encoding = "utf-8"

        def raise_for_status(self):
            return None

        @property
        def encoding(self):
            return self._encoding

        @encoding.setter
        def encoding(self, value):
            self._encoding = value

    monkeypatch.setattr(
        fe_crawler.requests, "get", lambda url: DummyResponse(html)
    )
    monkeypatch.setattr(fe_crawler, "download_image", lambda *args, **kwargs: None)

    class DummyArgs:
        url = "https://example.com/q/30_haru/pm04.html"
        output = tmp_path

    monkeypatch.setattr(
        fe_crawler.argparse.ArgumentParser, "parse_args", lambda self: DummyArgs()
    )

    fe_crawler.main()

    output_file = tmp_path / "30_haru_pm04.md"
    assert output_file.exists()
    assert "Question text" in output_file.read_text(encoding="utf-8")
