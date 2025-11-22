"""Tests for the FE Exam Crawler."""
import io

from bs4 import BeautifulSoup
import pytest

import fe_crawler


@pytest.fixture
def no_image_download(monkeypatch):  # pylint: disable=redefined-outer-name,unused-argument
    """Fixture to mock download_image to do nothing."""
    monkeypatch.setattr(fe_crawler, "download_image",
                        lambda *args, **kwargs: None)


def test_download_image_writes_file(monkeypatch, tmp_path):
    """Test that download_image saves the file and returns correct path."""
    class DummyResponse:
        """Mock response object."""

        def __init__(self, content: bytes):
            self.raw = io.BytesIO(content)

        def raise_for_status(self):
            """Mock raise_for_status."""
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
    """Test that process_element handles images and applies prefix."""
    img_html = '<img src="img/sample.png"/>'
    soup = BeautifulSoup(img_html, "html.parser")
    img_tag = soup.img

    captured = {}

    def fake_download(url, _output_dir, prefix=""):

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


def test_process_element_formats_lists_and_blanks(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test formatting of lists and fill-in-the-blank spans."""

    html = """
    <div class="mondai">
      Text <span class="bb">a</span><br>
      <ul><li>Option</li></ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    mondai_div = soup.find("div", class_="mondai")

    output = fe_crawler.process_element(
        mondai_div, "https://example.com/base/", tmp_path, prefix=""
    )

    assert "<u>&emsp;a&emsp;</u>" in output
    assert "- Option" in output
    assert "Text" in output


def test_process_element_adds_newline_before_list(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that a newline is added before a list element."""

    html = "<div>Text line<ul><li>List Item</li></ul></div>"
    soup = BeautifulSoup(html, "html.parser")
    div = soup.div

    output = fe_crawler.process_element(
        div, "https://example.com", tmp_path
    )

    # We expect a blank line between text and list
    assert "Text line\n\n- List Item" in output


def test_process_element_handles_span_bb_in_list(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test handling of span.bb within list items."""

    html = '<ul><li>Text with <span class="bb">a</span> blank</li></ul>'
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.ul

    output = fe_crawler.process_element(
        ul, "https://example.com", tmp_path
    )

    # Should convert span.bb to fill-in-blank format
    assert "- Text with <u>&emsp;a&emsp;</u> blank" in output


def test_process_element_adds_newline_after_list(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that a newline is added after a list element."""

    html = "<div><ul><li>Item</li></ul>Following text</div>"
    soup = BeautifulSoup(html, "html.parser")
    div = soup.div

    output = fe_crawler.process_element(
        div, "https://example.com", tmp_path
    )

    # Should have blank line between list and following text
    assert "- Item\n\nFollowing text" in output


def test_process_element_preserves_u_tags(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that <u> tags are preserved in the output."""

    html = "<div>Text with <u>underlined content</u> here</div>"
    soup = BeautifulSoup(html, "html.parser")
    div = soup.div

    output = fe_crawler.process_element(
        div, "https://example.com", tmp_path
    )

    # Should preserve u tags
    assert "<u>underlined content</u>" in output


def test_process_list_handles_nested_lists(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test processing of nested lists with indentation."""

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

    output = fe_crawler.process_list(
        ul, "https://example.com", tmp_path, ""
    )

    # Should have properly indented nested list
    assert "- Item 1\n\n　1. Nested 1\n\n　2. Nested 2\n\n- Item 2" in output


def test_process_list_formats_ordered_lists(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test formatting of standard ordered lists."""

    html = """
    <ol>
        <li>Step 1</li>
        <li>Step 2</li>
    </ol>
    """
    soup = BeautifulSoup(html, "html.parser")
    ol = soup.ol

    output = fe_crawler.process_list(
        ol, "https://example.com", tmp_path, ""
    )

    assert "1. Step 1" in output
    assert "2. Step 2" in output


def test_process_list_uses_numbered_classes(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that list items with numbered classes (li1, li2) are formatted correctly."""

    html = """
    <ul>
        <li class="li1">Case one</li>
        <li class="li2">Case two</li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.ul

    output = fe_crawler.process_list(
        ul, "https://example.com", tmp_path, ""
    )

    assert "(1) Case one" in output
    assert "(2) Case two" in output


def test_process_list_formats_alpha_ordered_lists(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test formatting of ordered lists with type='a'."""

    html = """
    <ol type="a">
        <li>Alpha</li>
        <li>Beta</li>
    </ol>
    """
    soup = BeautifulSoup(html, "html.parser")
    ol = soup.ol

    output = fe_crawler.process_list(
        ol, "https://example.com", tmp_path, ""
    )

    assert "a. Alpha" in output
    assert "b. Beta" in output


def test_process_list_formats_alpha_with_value(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test formatting of alpha ordered lists with custom value attributes."""

    html = """
    <ol type="a">
        <li value="5">Fifth</li>
        <li>Sixth</li>
    </ol>
    """
    soup = BeautifulSoup(html, "html.parser")
    ol = soup.ol

    output = fe_crawler.process_list(
        ol, "https://example.com", tmp_path, ""
    )

    assert "e. Fifth" in output
    assert "f. Sixth" in output


def test_process_list_handles_maru_numbering(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test handling of 'maru' class numbering (e.g., ①)."""

    html = """
    <ol>
        <li class="maru1">Alpha</li>
        <li class="maru2">Beta</li>
    </ol>
    """
    soup = BeautifulSoup(html, "html.parser")
    ol = soup.ol

    output = fe_crawler.process_list(
        ol, "https://example.com", tmp_path, ""
    )

    assert "① Alpha" in output
    assert "② Beta" in output


def test_process_list_handles_kana_classes(no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test handling of 'kana' class numbering (e.g., ア、)."""

    html = """
    <ul>
        <li class="lia">Option A</li>
        <li class="lii">Option B</li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.ul

    output = fe_crawler.process_list(
        ul, "https://example.com", tmp_path, ""
    )

    assert "ア、 Option A" in output
    assert "イ、 Option B" in output


def test_main_writes_output_when_main_container_present(monkeypatch, no_image_download, tmp_path):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that main() writes the output file when the main container is found."""

    html = """
    <div class="main kako">
      <div class="mondai">Question text</div>
    </div>
    """

    class DummyResponse:
        """Mock response object."""

        def __init__(self, text):
            """Initialize the mock response."""
            self.text = text
            self._encoding = "utf-8"
            self.apparent_encoding = "utf-8"

        def raise_for_status(self):
            """Mock raise_for_status."""
            return None

        @property
        def encoding(self):
            """Mock encoding property."""
            return self._encoding

        @encoding.setter
        def encoding(self, value):
            self._encoding = value

    monkeypatch.setattr(
        fe_crawler.requests, "get", lambda url, **kwargs: DummyResponse(html)
    )

    class DummyArgs:

        """Mock arguments object."""
        url = "https://example.com/q/30_haru/pm04.html"
        output = tmp_path

    monkeypatch.setattr(
        fe_crawler.argparse.ArgumentParser, "parse_args", lambda self: DummyArgs()
    )

    fe_crawler.main()

    output_file = tmp_path / "30_haru_pm04.md"
    assert output_file.exists()
    assert "Question text" in output_file.read_text(encoding="utf-8")
