"""Render REPORT.md with the standard library; never run an analytical pipeline.

The Markdown report is the single source for narrative, numbers and captions.
PNG files are embedded, so the resulting report can be opened independently.
"""
from __future__ import annotations

import base64
import html
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+|[^\s):]+)\)",
                  r'<a href="\2">\1</a>', text)


def render(markdown: str) -> str:
    lines = markdown.splitlines()
    result: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            result.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush()
        elif line.startswith("```"):
            flush()
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            result.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
        elif match := re.match(r"^(#{1,6}) (.+)$", line):
            flush()
            level = len(match[1])
            result.append(f"<h{level}>" + inline(match[2]) + f"</h{level}>")
        elif match := re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            flush()
            image = ROOT / match[2]
            source = match[2]
            if image.is_file():
                mime = mimetypes.guess_type(image.name)[0] or "application/octet-stream"
                source = f"data:{mime};base64," + base64.b64encode(image.read_bytes()).decode()
            result.append(f'<figure><img src="{html.escape(source)}" alt="{html.escape(match[1])}" loading="lazy"></figure>')
        elif line.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    rows.append(cells)
                index += 1
            table = '<div class="table-scroll"><table><thead><tr>'
            table += "".join(f'<th scope="col">{inline(cell)}</th>' for cell in rows[0])
            table += "</tr></thead><tbody>"
            for row in rows[1:]:
                table += "<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>"
            result.append(table + "</tbody></table></div>")
            continue
        elif line.startswith("- "):
            flush()
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append("<li>" + inline(lines[index].strip()[2:]) + "</li>")
                index += 1
            result.append("<ul>" + "".join(items) + "</ul>")
            continue
        else:
            paragraph.append(line)
        index += 1
    flush()
    return "\n".join(result)


def main() -> None:
    source = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    title = source.splitlines()[0].lstrip("# ")
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; line-height: 1.65; }}
body {{ margin: 0 auto; padding: 2rem 1.25rem 5rem; max-width: 64rem; }}
h1 {{ line-height: 1.15; font-size: clamp(1.8rem, 5vw, 3rem); }}
h2 {{ margin-top: 2.5rem; line-height: 1.3; }} p, li {{ max-width: 80ch; }}
a {{ color: light-dark(#174ea6, #9cc5ff); }} img {{ max-width: 100%; height: auto; }}
figure {{ margin: 2rem 0 1rem; }} .table-scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; }} th,td {{ text-align: left; padding: .65rem; border-bottom: 1px solid #888; }}
pre {{ padding: 1rem; overflow-x: auto; background: light-dark(#f0f2f5, #252a30); }}
code {{ font-size: .9em; }} @media print {{ body {{ padding: 0; }} figure, table {{ break-inside: avoid; }} }}
</style></head><body><main>{render(source)}</main></body></html>'''
    destinations = [ROOT / "outputs/report.html"]
    if ROOT.name == "ab-test-framework":
        destinations.append(ROOT / "report.html")
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8", newline="\n")
        print(destination)


if __name__ == "__main__":
    main()
