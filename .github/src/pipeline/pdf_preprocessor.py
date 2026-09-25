# Copyright 2025-2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authored by Michael Coletta, Technical Advisor to OASIS Open.

"""HTML preprocessing stage for enhanced PDF code-block formatting.

:class:`PdfPreprocessor` embeds a targeted monospace/code-block stylesheet into
an HTML document without disturbing existing OASIS CSS, then tags ``<pre>`` and
inline ``<code>`` elements so wkhtmltopdf renders code cleanly. The injected CSS
is intentionally distinct from the renderer stage's CSS.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import PipelineStep

logger = logging.getLogger(__name__)


class PdfPreprocessor(PipelineStep):
    """Inject targeted code-block CSS into an HTML file for PDF rendering."""

    def __init__(self, html_file: Path, output_file: Path) -> None:
        """Store the input and output HTML paths for this preprocessing pass."""
        self.html_file = html_file
        self.output_file = output_file

    @staticmethod
    def get_perfect_code_css() -> str:
        """Return the targeted code-formatting CSS to embed in the document.

        These rules target only code elements and are marked ``!important`` so
        they win over inherited OASIS styles without replacing them. The block
        is preserved verbatim; wkhtmltopdf output depends on its exact content.
        """
        return """
    /* TARGETED MONOSPACE FIXES - PRESERVE ORIGINAL OASIS CSS */
    
    /* Code elements - monospace font only */
    code, pre, .sourceCode, .highlight, tt, kbd, samp {
        font-family: "Courier New", "Liberation Mono", "DejaVu Sans Mono", "Consolas", "Monaco", monospace !important;
        font-weight: normal !important;
        font-style: normal !important;
        letter-spacing: 0 !important;
        word-spacing: 0 !important;
        -webkit-font-feature-settings: normal !important;
        font-feature-settings: normal !important;
    }
    
    /* Inline code styling */
    code {
        font-size: 0.9em !important;
        background-color: #f5f5f5 !important;
        border: 1px solid #ddd !important;
        border-radius: 2px !important;
        padding: 1px 4px !important;
        /* Wrap only when a span is wider than the line. Forbidding wraps let one long
           inline path (DMLex s3.2.1) widen the page, and Chrome then scaled
           every page of the PDF down to fit it. */
        white-space: normal !important;
        overflow-wrap: anywhere !important;
    }
    
    /* Code blocks styling */
    pre {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 10px !important;
        margin: 10px 0 !important;
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        page-break-inside: auto !important;
    }
    
    pre code {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        white-space: pre-wrap !important;
        font-size: inherit !important;
    }
    
    /* Syntax highlighting blocks */
    .sourceCode, .highlight {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 10px !important;
        margin: 10px 0 !important;
    }
    
    /* Language-specific code blocks */
    .json, .xml, .yaml, .bash, .shell, .python, .javascript, .http {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        padding: 10px !important;
        white-space: pre-wrap !important;
    }
    
    /* Code in tables */
    table code, td code, th code {
        font-size: 0.8em !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
    }
    
    /* PDF-specific code formatting */
    @media print {
        code, pre, .sourceCode, .highlight {
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
        
        pre {
            page-break-inside: auto !important;
            orphans: 2 !important;
            widows: 2 !important;
        }
    }

    /* Print type scale, in points. The OASIS Markdown stylesheet sets screen
       sizes only (12pt body and tables, 18pt h1), so the printed size was
       whatever the renderer made of them: wkhtmltopdf shrank NIEM NDR v6.0
       to an 8pt body and 6pt code, headless Chrome printed DMLex at 12pt.
       These sizes match the OASIS DocBook and Word publications (DMLex v1.0
       OS: 10pt body and code). !important where the code rules above are. */
    @media print {
        body { font-size: 10pt !important; line-height: 1.3 !important;
               margin-left: 0 !important; margin-right: 0 !important; }
        /* A table never runs past the column: wkhtmltopdf clips what does
           not fit, and dropped the last column of CSAF v2.1's eight-column
           remediation matrix. Cells may break long words, and code in a cell
           breaks after _ / . - (<wbr> from preprocess()), so its columns can
           narrow. th code takes the header's white on blue. */
        table { font-size: 9pt !important; width: 100% !important; max-width: 100% !important; }
        th, td { padding: 2pt 3pt !important; word-wrap: break-word !important; }
        th code, td code { white-space: normal !important; word-wrap: break-word !important; }
        th code { color: inherit !important; background: transparent !important; border: none !important; }

        h1big { font-size: 20pt !important; }
        h1 { font-size: 16pt !important; }
        h2 { font-size: 14pt !important; }
        h3 { font-size: 12pt !important; }
        h4 { font-size: 11pt !important; }
        h5, h6 { font-size: 10pt !important; }

        pre, .sourceCode, .highlight,
        .json, .xml, .yaml, .bash, .shell, .python, .javascript, .http { font-size: 9pt !important; }
        pre code { font-size: inherit !important; }
        /* word-wrap is the spelling wkhtmltopdf's WebKit reads; it ignores
           overflow-wrap: anywhere, so a long inline path ran past the right
           margin (CSAF v2.1 csd01). Chrome takes the later overflow-wrap. No
           side padding, so a broken span and a wide table fit the column. */
        code { font-size: 9pt !important; padding-left: 0 !important; padding-right: 0 !important;
               word-wrap: break-word !important; overflow-wrap: anywhere !important; }
        table code, td code, th code { font-size: 8.5pt !important; }
        h1 code, h2 code, h3 code, h4 code, h5 code, h6 code { font-size: 0.95em !important; }

        /* A heading, or the caption line before an example (tagged
           keep-with-next by preprocess(), since wkhtmltopdf has no :has()),
           stays with what follows it; a code block split by a page break
           keeps its border on both halves. wkhtmltopdf reads page-break-*. */
        h1, h2, h3, h4, h5, h6, h1big,
        .keep-with-next { page-break-after: avoid !important; break-after: avoid !important; }
        pre { -webkit-box-decoration-break: clone; box-decoration-break: clone; }
    }

    /* Figures: never wider than the line. DMLex v1.0's figures carried no
       width, so each printed at its natural size and the 1505pt UML diagram
       ran off the page. */
    img {
        max-width: 100% !important;
        height: auto !important;
    }
    
    /* Page setup - portrait with wider margins */
    @page {
        size: A4 portrait;
        margin: 2.5cm 2cm 2.5cm 2cm;
    }
    """

    def preprocess(self) -> None:
        """Read the input HTML, embed the code CSS, tag code elements, write out.

        Ensures a ``<head>`` exists, appends the code stylesheet (append, not
        prepend, so existing CSS keeps precedence), adds ``code-block`` /
        ``inline-code`` classes where missing, and writes the result to
        :attr:`output_file`.
        """
        logger.info(f"Preprocessing HTML: {self.html_file} -> {self.output_file}")

        # Read the HTML file
        with open(self.html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Parse HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Ensure document has a proper head section
        if not soup.head:
            head = soup.new_tag('head')
            if soup.html:
                soup.html.insert(0, head)
            else:
                soup.insert(0, head)

        self.drop_base(soup)

        # Add targeted CSS for code formatting
        # Note: Appending rather than prepending to preserve existing CSS precedence
        style_tag = soup.new_tag('style')
        style_tag.string = self.get_perfect_code_css()
        soup.head.append(style_tag)

        # Ensure proper CSS classes for code block elements
        for pre in soup.find_all('pre'):
            if not pre.get('class'):
                pre['class'] = ['code-block']

        # Add CSS classes to inline code elements
        for code in soup.find_all('code'):
            if code.parent and code.parent.name != 'pre':
                if not code.get('class'):
                    code['class'] = ['inline-code']

        self.tag_print_layout(soup)

        # Write preprocessed HTML to output file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        logger.info(f"HTML preprocessing completed successfully: {self.output_file}")

    @staticmethod
    def drop_base(soup: BeautifulSoup) -> None:
        """Remove ``<base href>`` from the PDF copy, never the published HTML.

        CSAF v2.0 OS carries ``<base href="https://docs.oasis-open.org/...">``,
        so wkhtmltopdf fetched its relative stylesheets and images from the
        live site: wrong for a package not yet published, and it hid a
        missing local file. Relative hyperlinks other than ``#fragment`` are
        first made absolute against the base, so the PDF's links still point
        where the published document's do; resources then resolve beside the
        file being rendered.
        """
        base = soup.find('base', href=True)
        if base is None:
            for extra in soup.find_all('base'):
                extra.decompose()
            return
        root = base['href']
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            # "//host/path" is relative too: it takes the base's scheme.
            if href and not href.startswith('#') and not urlsplit(href).scheme:
                a['href'] = urljoin(root, href)
        for extra in soup.find_all('base'):
            extra.decompose()

    @staticmethod
    def tag_print_layout(soup: BeautifulSoup) -> None:
        """Add the classes the print stylesheet keys on.

        ``keep-with-next`` goes on a paragraph directly before a code block or
        before a paragraph holding only an image (an example or figure
        caption); code in a table cell gets a ``<wbr>`` after each _ / . -;
        trailing spaces are removed from each line of a code block.
        """
        def add(tag, name):
            classes = tag.get('class', [])
            if name not in classes:
                tag['class'] = classes + [name]

        def lone_image(tag):
            return (tag.name == 'p' and tag.find('img') is not None
                    and not tag.get_text(strip=True))

        for tag in soup.find_all(['pre', 'p']):
            if tag.name == 'p' and not lone_image(tag):
                continue
            prev = tag.find_previous_sibling()
            if prev is not None and prev.name == 'p' and not lone_image(prev):
                add(prev, 'keep-with-next')

        # Trailing spaces in a code block print nothing, but under pre-wrap
        # they hang past the block's edge: CSAF v2.0 OS's space-aligned
        # "Supported digests" listing ran 0.6pt past the right margin on
        # whitespace alone.
        # A string's own end is a line end only when the next string in the
        # block starts a new line, or there is none.
        for pre in soup.find_all('pre'):
            strings = list(pre.find_all(string=True))
            for i, text in enumerate(strings):
                at_line_end = i + 1 == len(strings) or str(strings[i + 1]).startswith('\n')
                pattern = r'[ \t]+(?=\n)|[ \t]+$' if at_line_end else r'[ \t]+(?=\n)'
                stripped = re.sub(pattern, '', str(text))
                if stripped != str(text):
                    text.replace_with(stripped)

        # Code in a table cell may break after _ / . - (a <wbr>, which adds no
        # character to the text), so a column of identifiers can narrow.
        for code in soup.select('td code, th code'):
            for text in list(code.find_all(string=True)):
                parts = [p for p in re.split(r'(?<=[_/.\-])', str(text)) if p]
                if len(parts) < 2:
                    continue
                for i, part in enumerate(parts):
                    if i:
                        text.insert_before(soup.new_tag('wbr'))
                    text.insert_before(part)
                text.extract()

    def run(self) -> None:
        """Execute the preprocessing stage (alias for :meth:`preprocess`)."""
        self.preprocess()


def main() -> None:
    """CLI entry point: ``fix_html_for_pdf.py <html_file> [-o OUT] [-v]``.

    Defaults the output to ``<stem>_fixed<suffix>`` beside the input, validates
    the input exists, and exits non-zero on failure — preserving the original
    contract exactly.
    """
    parser = argparse.ArgumentParser(
        description="Preprocess HTML for enhanced PDF code block formatting",
        epilog="This tool adds targeted monospace CSS while preserving existing styles and document structure."
    )

    parser.add_argument(
        "html_file",
        help="Input HTML file to preprocess"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output HTML file (default: same as input with _fixed suffix)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging based on verbosity level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    PipelineStep.configure_logging(level=log_level)

    # Determine output file path
    input_path = Path(args.html_file)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_stem(input_path.stem + "_fixed")

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    try:
        PdfPreprocessor(input_path, output_path).preprocess()
        print("HTML preprocessing completed successfully")
        print(f"Output: {output_path}")

    except Exception as e:
        logger.error(f"Preprocessing failed: {str(e)}")
        print(f"HTML preprocessing failed: {str(e)}")
        sys.exit(1)
