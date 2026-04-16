#!/usr/bin/env python3
"""
convert_readme.py — Convert GFM README.md to RTF via HTML intermediate.
Uses Python 'markdown' library for GFM parsing, then converts HTML to RTF.

Usage: python3 convert_readme.py [input.md] [output.rtf]
Dependencies: markdown (pip3 install markdown)
"""
import sys
import re
from markdown import markdown

# ---------------------------------------------------------------------------
# STEP 1: GFM Markdown -> HTML (using Python markdown lib with extensions)
# ---------------------------------------------------------------------------

GFM_EXTENSIONS = [
    'tables',
    'fenced_code',
    'codehilite',
    'nl2br',
    'sane_lists',
    'smarty',
]

GFM_EXTENSION_CONFIGS = {
    'codehilite': {'css_class': 'code', 'noclasses': True},
}


def markdown_to_html(md_text):
    """Convert GFM markdown to HTML string."""
    return markdown(md_text, extensions=GFM_EXTENSIONS, extension_configs=GFM_EXTENSION_CONFIGS)


# ---------------------------------------------------------------------------
# STEP 2: HTML -> RTF
# ---------------------------------------------------------------------------

RTF_HEADER = r"""{\rtf1\ansi\deff0
{\fonttbl
{\f0\fswiss\fcharset0 Calibri;}
{\f1\fmodern\fcharset0 Consolas;}
}
{\colortbl;
\red0\green0\blue0;
\red54\green95\blue145;
\red102\green102\blue102;
\red230\green240\blue250;
}
"""
RTF_FOOTER = "}"

# Ordered list of HTML tag -> RTF conversion rules.
# Each entry: (html_pattern, rtf_replacement_or_handler)
# Applied in order via re.sub. Use DOTALL where tags span lines.

def _rtf_escape_text(text):
    """Escape RTF special chars in plain text."""
    result = []
    for ch in text:
        if ch == '\\':
            result.append('\\\\')
        elif ch == '{':
            result.append('\\{')
        elif ch == '}':
            result.append('\\}')
        elif ord(ch) > 127:
            result.append(f'\\u{ord(ch)}?')
        else:
            result.append(ch)
    return ''.join(result)


def _handle_heading(match):
    level = int(match.group(1))
    content = _strip_html_tags(match.group(2))
    sizes = {1: 48, 2: 36, 3: 30, 4: 26, 5: 24, 6: 22}
    fs = sizes.get(level, 24)
    spacing = max(360 - (level * 40), 120)
    return f'{{\\pard\\sb{spacing}\\sa120\\keepn\\f0\\fs{fs}\\cf2\\b {content}\\par}}\n'


def _handle_code_block(match):
    code = match.group(1)
    # Strip any inner HTML tags from syntax highlighting
    code = _strip_html_tags(code)
    code = code.strip()
    lines = code.split('\n')
    escaped_lines = [_rtf_escape_text(line) for line in lines]
    content = '\\line\n'.join(escaped_lines)
    return f'{{\\pard\\sb100\\sa100\\f1\\fs20\\cbpat4\\li360\\ri360 {content}\\par}}\n'


def _handle_table_row(match, is_header=False):
    cells_html = match.group(1)
    cell_pattern = r'<t[hd][^>]*>(.*?)</t[hd]>'
    cells = re.findall(cell_pattern, cells_html, re.DOTALL)
    num_cols = len(cells) if cells else 1
    col_width = 9000 // max(num_cols, 1)

    rtf = '{\\trowd\n'
    for i in range(num_cols):
        rtf += f'\\clbrdrt\\brdrs\\clbrdrb\\brdrs\\clbrdrl\\brdrs\\clbrdrr\\brdrs\\cellx{col_width * (i + 1)}\n'
    rtf += '\\pard\\intbl\n'
    for cell in cells:
        clean = _strip_html_tags(cell).strip()
        if is_header:
            rtf += f'{{\\b {_rtf_escape_text(clean)}}}\\cell\n'
        else:
            rtf += f'{_rtf_escape_text(clean)}\\cell\n'
    rtf += '\\row}\n'
    return rtf


def _strip_html_tags(text):
    """Remove all HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


def html_to_rtf(html_text):
    """Convert HTML string to RTF string."""
    rtf = html_text

    # Headings
    rtf = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', _handle_heading, rtf, flags=re.DOTALL)

    # Code blocks (pre > code)
    rtf = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', _handle_code_block, rtf, flags=re.DOTALL)

    # Tables — process thead and tbody rows
    def _handle_full_table(match):
        table_html = match.group(0)
        result = ''
        # Header rows
        thead_match = re.search(r'<thead>(.*?)</thead>', table_html, re.DOTALL)
        if thead_match:
            for row_match in re.finditer(r'<tr>(.*?)</tr>', thead_match.group(1), re.DOTALL):
                result += _handle_table_row(row_match, is_header=True)
        # Body rows
        tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_html, re.DOTALL)
        if tbody_match:
            for row_match in re.finditer(r'<tr>(.*?)</tr>', tbody_match.group(1), re.DOTALL):
                result += _handle_table_row(row_match, is_header=False)
        # Fallback: rows without thead/tbody
        if not thead_match and not tbody_match:
            rows = list(re.finditer(r'<tr>(.*?)</tr>', table_html, re.DOTALL))
            for i, row_match in enumerate(rows):
                result += _handle_table_row(row_match, is_header=(i == 0))
        return result

    rtf = re.sub(r'<table>.*?</table>', _handle_full_table, rtf, flags=re.DOTALL)

    # Horizontal rules
    rtf = re.sub(r'<hr\s*/?>', lambda m: '{\\pard\\sb120\\sa120\\brdrb\\brdrs\\brdrw15\\brsp40\\par}\n', rtf)

    # Links
    def _handle_link(match):
        url = match.group(1)
        text = _strip_html_tags(match.group(2))
        return f'{{\\field{{\\*\\fldinst HYPERLINK "{url}"}}{{\\fldrslt \\cf2 {text}}}}}'
    rtf = re.sub(r'<a\s+href="([^"]*)"[^>]*>(.*?)</a>', _handle_link, rtf, flags=re.DOTALL)

    # Images
    def _handle_img(match):
        tag = match.group(0)
        src = re.search(r'src="([^"]*)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        src_text = src.group(1) if src else ''
        alt_text = alt.group(1) if alt else 'image'
        return f'{{\\cf3 [Image: {_rtf_escape_text(alt_text)} \\u8212? {_rtf_escape_text(src_text)}]}}'
    rtf = re.sub(r'<img\s+[^>]*/?\s*>', _handle_img, rtf)

    # Bold
    rtf = re.sub(r'<strong>(.*?)</strong>', lambda m: '{\\b ' + m.group(1) + '}', rtf, flags=re.DOTALL)
    rtf = re.sub(r'<b>(.*?)</b>', lambda m: '{\\b ' + m.group(1) + '}', rtf, flags=re.DOTALL)

    # Italic
    rtf = re.sub(r'<em>(.*?)</em>', lambda m: '{\\i ' + m.group(1) + '}', rtf, flags=re.DOTALL)
    rtf = re.sub(r'<i>(.*?)</i>', lambda m: '{\\i ' + m.group(1) + '}', rtf, flags=re.DOTALL)

    # Strikethrough
    rtf = re.sub(r'<del>(.*?)</del>', lambda m: '{\\strike ' + m.group(1) + '}', rtf, flags=re.DOTALL)

    # Inline code
    rtf = re.sub(r'<code>(.*?)</code>', lambda m: '{\\f1\\fs20\\chshdng1\\chcbpat4 ' + m.group(1) + '}', rtf, flags=re.DOTALL)

    # Subscript / superscript / underline
    rtf = re.sub(r'<sub>(.*?)</sub>', lambda m: '{\\sub ' + m.group(1) + '}', rtf, flags=re.DOTALL)
    rtf = re.sub(r'<sup>(.*?)</sup>', lambda m: '{\\super ' + m.group(1) + '}', rtf, flags=re.DOTALL)
    rtf = re.sub(r'<ins>(.*?)</ins>', lambda m: '{\\ul ' + m.group(1) + '}', rtf, flags=re.DOTALL)

    # Line breaks
    rtf = re.sub(r'<br\s*/?>', lambda m: '\\line ', rtf)

    # List items
    rtf = re.sub(r'<li>(.*?)</li>', lambda m: '{\\pard\\sb36\\sa36\\li480\\fi-360\\f0\\fs22 \\u8226?  ' + m.group(1) + '\\par}\n', rtf, flags=re.DOTALL)

    # Blockquotes
    def _handle_blockquote(match):
        content = _strip_html_tags(match.group(1)).strip()
        return f'{{\\pard\\sb60\\sa60\\li480\\brdrl\\brdrs\\brdrw20\\brsp80\\cf3\\f0\\fs22 {_rtf_escape_text(content)}\\par}}\n'
    rtf = re.sub(r'<blockquote>(.*?)</blockquote>', _handle_blockquote, rtf, flags=re.DOTALL)

    # Paragraphs
    rtf = re.sub(r'<p>(.*?)</p>', lambda m: '{\\pard\\sb0\\sa120\\f0\\fs22 ' + m.group(1) + '\\par}\n', rtf, flags=re.DOTALL)

    # Strip any remaining HTML tags
    rtf = re.sub(r'<[^>]+>', '', rtf)

    # Clean up blank lines
    rtf = re.sub(r'\n{3,}', '\n\n', rtf)

    # Escape any remaining plain text that wasn't caught
    # (most should already be escaped by handlers above)

    return RTF_HEADER + rtf.strip() + '\n' + RTF_FOOTER


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    input_path = sys.argv[1] if len(sys.argv) > 1 else 'README.md'
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.rsplit('.', 1)[0] + '.rtf'

    with open(input_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    html_content = markdown_to_html(md_content)

    # Debug: save intermediate HTML
    html_path = input_path.rsplit('.', 1)[0] + '.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f'Intermediate HTML: {html_path}')

    rtf_content = html_to_rtf(html_content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rtf_content)

    print(f'Converted: {input_path} -> {output_path}')
