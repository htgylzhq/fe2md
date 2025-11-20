# FE Exam Crawler

A Python crawler for scraping Japanese Fundamental Information Technology Engineer (基本情報技術者) exam questions and converting them to Markdown format.

## Features

- 🎯 Crawl FE exam questions from fe-siken.com
- 📝 Convert HTML to well-formatted Markdown
- 🖼️ Auto-download and manage image assets
- ✅ Preserve special formatting (fill-in-blanks, underlines, nested lists)
- 📂 Customizable output directory

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python fe_crawler.py <URL> -o <output_directory>
```

**Example:**
```bash
python fe_crawler.py https://www.fe-siken.com/kakomon/01_aki/pm04.html -o samples
```

## Output Format

The crawler converts HTML elements to Markdown with the following formatting:

- **Fill-in-blanks**: `<span class="bb">a</span>` → `<u>&emsp;a&emsp;</u>`
- **Images**: Centered with white background, saved to `assets/` folder
- **Nested lists**: Properly indented with 2 spaces per level
- **Underlines**: Preserved as `<u>` tags in Markdown

## Testing

```bash
pytest tests/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.
