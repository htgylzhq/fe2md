"""
FE Exam Crawler

Crawls questions from the FE Exam website and converts them to Markdown.
"""
import argparse

import os
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_REQUESTS_TIMEOUT = 10
_LI_CLASS_RE = re.compile(r"li(\d+)$")
_MARU_CLASS_RE = re.compile(r"maru(\d+)$")

_CIRCLED_NUMBERS = {
    1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤",
    6: "⑥", 7: "⑦", 8: "⑧", 9: "⑨", 10: "⑩",
    11: "⑪", 12: "⑫", 13: "⑬", 14: "⑭", 15: "⑮",
    16: "⑯", 17: "⑰", 18: "⑱", 19: "⑲", 20: "⑳",
}

_KANA_MAP = {
    "lia": "ア", "lii": "イ", "liu": "ウ", "lie": "エ", "lio": "オ",
    "lika": "カ", "liki": "キ", "liku": "ク", "like": "ケ", "liko": "コ",
}

_BLOCK_ELEMENTS = frozenset((
    'p', 'div', 'ul', 'ol', 'blockquote',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img'
))


def clean_text(text):
    """Clean whitespace from text."""

    if not text:
        return ""
    return text.strip()


def download_image(img_url, output_dir, prefix="", assets_dir_name="assets"):
    """Downloads an image and returns the relative path for markdown."""
    try:
        response = requests.get(img_url, stream=True,
                                timeout=_REQUESTS_TIMEOUT)
        response.raise_for_status()

        original_filename = Path(urlparse(img_url).path).name
        filename = f"{prefix}_{original_filename}" if prefix else original_filename

        assets_dir = Path(output_dir) / assets_dir_name
        assets_dir.mkdir(parents=True, exist_ok=True)

        filepath = assets_dir / filename
        with filepath.open("wb") as f:
            shutil.copyfileobj(response.raw, f)

        return f"./{assets_dir_name}/{filename}"
    except (requests.RequestException, OSError) as e:
        print(f"Error downloading image {img_url}: {e}")
        return None


def _get_ordered_start(list_element):
    if list_element.name != 'ol':
        return 1
    try:
        return int(list_element.get("start", 1))
    except (TypeError, ValueError):
        return 1


def _circled_number(value: int) -> str:
    return _CIRCLED_NUMBERS.get(value, f"({value})")


def _marker_from_classes(li_element):
    class_number = None
    maru_number = None
    for cls in li_element.get('class', []):
        if cls in _KANA_MAP:
            return f"{_KANA_MAP[cls]}、"
        if (li_match := _LI_CLASS_RE.match(cls)):
            class_number = int(li_match.group(1))
        elif (maru_match := _MARU_CLASS_RE.match(cls)):
            maru_number = int(maru_match.group(1))

    if maru_number is not None:
        return _circled_number(maru_number)

    if class_number is not None:
        return f"({class_number})"

    return None


def _marker_from_type(list_element, number, type_attr: str | None):
    if list_element.name != 'ol' or not type_attr:
        return None

    lower_type = type_attr.lower()
    if lower_type == 'a' and 1 <= number <= 26:
        start_char = 'A' if type_attr == 'A' else 'a'
        letter = chr(ord(start_char) + number - 1)
        return f'{letter}.'

    return None


def _default_marker(list_element, number):
    if list_element.name == 'ol':
        return f"{number}."
    return "-"


def _get_list_marker(list_element, li_element, number):
    """Return the marker string for a list item, preserving numbering when present."""
    type_attr = (list_element.get("type") or "").strip()

    if marker := _marker_from_classes(li_element):
        return marker

    if marker := _marker_from_type(list_element, number, type_attr):
        return marker

    return _default_marker(list_element, number)


def process_list(list_element, base_url, output_dir, prefix, indent_level=0):
    """Process a ul or ol element and return markdown with proper indentation."""
    md_lines = []
    indent_unit = "　"  # full-width space to ensure visible indentation in rendered markdown
    indent = indent_unit * indent_level
    start_value = _get_ordered_start(list_element)
    current_number = start_value

    for li in list_element.find_all('li', recursive=False):
        # Get direct text content (not from nested lists)
        li_text = ""
        try:
            value_number = int(li.get('value'))
        except (TypeError, ValueError):
            value_number = None

        for child in li.children:
            if child.name == 'span' and 'bb' in child.get('class', []):
                text = child.get_text().strip()
                li_text += f"<u>&emsp;{text}&emsp;</u>"
            elif child.name in ['ul', 'ol']:
                # Nested list - process with increased indentation
                nested_text = process_list(
                    child, base_url, output_dir, prefix, indent_level + 1)
                # Add a blank line before nested list for readability
                li_text += "\n\n" + nested_text
            elif child.name is None:
                if child.string:
                    stripped_text = child.string.strip()
                    if stripped_text:
                        prefix_space = ""
                        if child.string[0].isspace() and li_text \
                                and not li_text.endswith((" ", "\n")):
                            prefix_space = " "
                        suffix_space = " " if child.string[-1].isspace() else ""

                        li_text += f"{prefix_space}{stripped_text}{suffix_space}"
            elif child.name == 'u':
                u_content = ""
                for u_child in child.children:
                    if u_child.name is None:
                        u_content += u_child.string if u_child.string else ""
                    else:
                        u_content += u_child.get_text()
                li_text += f"<u>{u_content}</u>"
            else:
                # Get text from other elements, but not from nested lists
                if child.name not in ['ul', 'ol']:
                    text = child.get_text().strip()
                    if text:
                        li_text += text

        # Normalize trailing spaces before newlines but keep leading indentation for nested lists
        li_text = re.sub(r"[ \t]+\n", "\n", li_text)
        li_text = li_text.rstrip()
        number_for_marker = value_number if value_number is not None else current_number
        marker = _get_list_marker(list_element, li, number_for_marker)
        md_lines.append(f"{indent}{marker} {li_text}")
        if list_element.name == 'ol':
            current_number = number_for_marker + 1

    return "\n\n".join(md_lines)


def process_element(element, base_url, output_dir, prefix=""):
    """Processes a single element and returns markdown text."""
    md_text = ""

    if element.name in ['ul', 'ol']:
        # Delegate list processing to keep numbering consistent
        return process_list(element, base_url, output_dir, prefix) + "\n\n"

    # Handle images directly
    if element.name == 'img':
        src = element.get('src')
        if not src:
            return ""
        full_url = urljoin(base_url, src)
        local_path = download_image(full_url, output_dir, prefix)
        if not local_path:
            return ""
        return (
            '<div style="text-align: center;">\n'
            f'  <img src="{local_path}" style="max-width: 100%; background-color: white;">\n'
            '</div>\n\n'
        )

    # Handle text with specific children processing
    for child in element.children:
        if child.name == 'span' and 'bb' in child.get('class', []):
            # Handle blanks: <span class="bb">a</span> -> <u>&emsp;a&emsp;</u>
            text = child.get_text().strip()
            md_text += f"<u>&emsp;{text}&emsp;</u>"
        elif child.name == 'br':
            md_text += "\n\n"
        elif child.name is None:  # NavigableString
            md_text += child.string if child.string else ""
        elif child.name == 'u':
            # Preserve underline tags
            u_content = ""
            for u_child in child.children:
                if u_child.name is None:
                    u_content += u_child.string if u_child.string else ""
                else:
                    u_content += u_child.get_text()
            md_text += f"<u>{u_content}</u>"
        else:
            # Recursively process other tags
            child_text = process_element(child, base_url, output_dir, prefix)

            # Check if child is a block element
            if child.name in _BLOCK_ELEMENTS:
                md_text += "\n\n" + child_text.strip() + "\n\n"
            else:
                # Inline elements - do not strip aggressively if it removes necessary spaces,
                # but here we rely on text nodes for spaces usually.
                # However, process_element adds \n\n at the end. We must strip that for inline.
                md_text += child_text.strip()

    return md_text + "\n\n"


def main():
    """Main entry point for the crawler."""

    parser = argparse.ArgumentParser(description='Crawl FE Exam Question')
    parser.add_argument('url', help='URL of the question page')
    parser.add_argument('--output', '-o', default='.', help='Output directory')
    args = parser.parse_args()

    url = args.url
    output_dir = args.output

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        response = requests.get(url, timeout=_REQUESTS_TIMEOUT)

        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find main content container (class list, not a single spaced string)
        main_container = soup.select_one('div.main.kako')
        if not main_container:
            print("Could not find main content container (div.main.kako)")
            return

        # Extract Title - Skip adding it manually as h2, rely on h3 qno
        # title_tag = main_container.find('h2')
        # title = clean_text(title_tag.get_text()) if title_tag else "Unknown Title"

        # Generate filename and prefix
        path_parts = urlparse(url).path.split('/')
        prefix = ""
        if len(path_parts) >= 2:
            # path_parts[-2] is likely the year/season code e.g. '30_haru'
            prefix = path_parts[-2]
            filename_base = f"{prefix}_{path_parts[-1].replace('.html', '')}"
        else:
            filename_base = "question"

        output_file = os.path.join(output_dir, f"{filename_base}.md")

        markdown_content = ""

        # Iterate through children of main_container
        # We want to skip the title h2 we already got, and maybe some other metadata

        for element in main_container.children:
            if element.name is None:
                continue

            if element.name == 'h2':
                continue  # Skip the generic page title

            classes = element.get('class', [])

            # Skip navigation/buttons
            if (any(c in classes for c in ('pan', 'pdflink')) or
                    ('img_margin' in classes and element.find('ul', id='btmNav'))):
                continue

            # Headers - Check for stop conditions
            if element.name == 'h3':
                text = element.get_text().strip()
                if "問題一覧" in text:
                    break  # Stop processing at the end

                if any(x in text for x in ["解答", "解説"]):
                    continue  # Skip interactive sections

                markdown_content += f"### {text}\n\n"
                continue

            # Question Text
            if 'mondai' in classes:
                markdown_content += process_element(
                    element, url, output_dir, prefix)
                continue

            # Answer Groups
            if 'select' in classes and 'ansbg' in classes:
                markdown_content += "---\n\n"
                markdown_content += process_element(
                    element, url, output_dir, prefix).rstrip() + "\n\n"
                continue

            # Handle images that might be direct children (e.g. inside div.img_margin)
            if element.name == 'div' and 'img_margin' in classes:
                markdown_content += process_element(
                    element, url, output_dir, prefix)
                continue

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f"Successfully saved to {output_file}")

    except (requests.RequestException, OSError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
