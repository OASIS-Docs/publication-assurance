#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Convert an OASIS DocBook 4.5 specification to OASIS-style Markdown.

Input is the DocBook file with every XInclude and entity already resolved,
which is what `make dmlex-<version>.xml` (merge.sh) or
`xmllint --xinclude --noent --loaddtd` produces. Output follows the layout of
the OASIS Markdown specifications (CSAF, NIEM): logo, title block, front
matter as level-4 headings, notices, table of contents, then numbered
sections carrying explicit anchors.

Rendering rules mirror the OASIS DocBook HTML stylesheet
(oasis-specification-html.xsl), so the Markdown reads the same as the
published HTML:

- A section or appendix with role="normative"/"informative" gets
  " (Normative)" / " (Informative)" after its title.
- Every DocBook id becomes an anchor, so olink/xref/link targets and existing
  deep links keep working.
- xref text is the target's number and title, as DocBook generates it.
- An element whose condition attribute does not contain "oasis" is dropped,
  as the stylesheet drops it.

What differs between specifications, or between versions of the stylesheet,
comes from the profile (--profile, a JSON file): glossterm_upper (the v1.43
stylesheet uppercases <glossterm>, the BCP 14 key words; earlier ones do
not), figure_dpi (a <graphic contentwidth="16cm"> becomes <img width> at this
many pixels per inch; DocBook XSL's default is 90) and code_languages (the
fence language for a program listing, by the extension of its xml:base).

An element the converter does not know (a table, for one) stops the
conversion rather than being flattened into paragraphs.

Usage: docbook2md.py merged.xml out.md [--profile profile.json] [--images-prefix PREFIX]
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'
LOGO = 'https://docs.oasis-open.org/templates/OASISLogo-v3.0.png'
DEFAULTS = {
    'glossterm_upper': False,
    'figure_dpi': 90,
    'code_languages': {'.json': 'json', '.xml': 'xml', '.sql': 'sql'},
}


def clean_ws(s):
    return re.sub(r'\s+', ' ', s)


def esc(s):
    """Escape characters that Markdown would otherwise interpret."""
    s = s.replace('\\', '\\\\')
    s = re.sub(r'([*_`\[\]<>|])', r'\\\1', s)
    return s


def code_span(s):
    s = clean_ws(s).strip()
    ticks = '`'
    while ticks in s:
        ticks += '`'
    pad = ' ' if s.startswith('`') or s.endswith('`') else ''
    return f'{ticks}{pad}{s}{pad}{ticks}'


class Numberer:
    """Assign DocBook-style numbers to sections, appendices and bibliography."""

    def __init__(self, root):
        self.num = {}      # element -> "3.4" / "A.1.2"
        self.title = {}    # id -> plain title text
        self.byid = {}
        for el in root.iter():
            i = el.get('id')
            if i:
                self.byid[i] = el
        top = [c for c in root if c.tag in ('section', 'appendix')]
        s = a = 0
        for c in top:
            if c.tag == 'section':
                s += 1
                self._walk(c, str(s))
            else:
                self._walk(c, chr(ord('A') + a))
                a += 1

    def _walk(self, el, n):
        self.num[el] = n
        k = 0
        for c in el:
            if c.tag in ('section', 'bibliography'):
                k += 1
                self._walk(c, f'{n}.{k}')


class Converter:
    def __init__(self, root, images_prefix='', profile=None):
        self.profile = dict(DEFAULTS, **(profile or {}))
        self.root = root
        drop_unconditioned(root)
        self.nb = Numberer(root)
        self.images_prefix = images_prefix
        self.toc = []
        self.warnings = []
        self.parent_of = {c: p for p in root.iter() for c in p}
        self.example_num = {}
        body = 0
        for top in root:
            if top.tag == 'appendix':
                letter = self.nb.num[top]
                for k, e in enumerate(top.iter('example'), 1):
                    self.example_num[e] = f'{letter}.{k}'
            else:
                for e in top.iter('example'):
                    body += 1
                    self.example_num[e] = str(body)

    # ---------------------------------------------------------------- inline
    def title_text(self, el):
        t = el.find('title')
        return clean_ws(self.inline(t, plain=True)).strip() if t is not None else ''

    def xref_text(self, target_id):
        el = self.nb.byid.get(target_id)
        if el is None:
            self.warnings.append(f'xref to unknown id {target_id}')
            return target_id
        if el.tag == 'bibliomixed':
            ab = el.find('abbrev')
            return f'[{clean_ws("".join(ab.itertext())).strip()}]' if ab is not None else target_id
        n = self.nb.num.get(el)
        t = self.title_text(el)
        if el.tag == 'appendix':
            return f'Appendix {n}, \u201c{t}\u201d' if n else t
        if el.tag == 'example':
            return f'Example {self.example_num.get(el, "?")}, \u201c{t}\u201d'
        return f'Section {n}, \u201c{t}\u201d' if n else t

    def inline(self, el, plain=False):
        """Render el's mixed content as inline Markdown (or plain text)."""
        out = []
        if el.text:
            out.append(el.text if plain else esc(el.text))
        for c in el:
            out.append(self.inline_el(c, plain))
            if c.tail:
                out.append(c.tail if plain else esc(c.tail))
        return ''.join(out)

    def inline_el(self, c, plain):
        tag = c.tag
        if not isinstance(tag, str):
            return ''
        txt = lambda: self.inline(c, plain)
        if tag == 'glossterm':
            s = clean_ws(''.join(c.itertext()))
            return s.upper() if self.profile['glossterm_upper'] else s
        if tag in ('code', 'literal'):
            inner = [x for x in c if isinstance(x.tag, str)]
            if len(inner) == 1 and inner[0].tag in ('olink', 'link', 'xref') and not (c.text or '').strip():
                link = inner[0]
                label = ''.join(link.itertext())
                tgt = link.get('targetptr') or link.get('linkend')
                return label if plain else f'[{code_span(label)}](#{tgt})'
            s = ''.join(c.itertext())
            return s if plain else code_span(s)
        if tag in ('olink', 'link'):
            tgt = c.get('targetptr') or c.get('linkend')
            label = txt() if (c.text or len(c)) else self.xref_text(tgt)
            if plain:
                return label
            if tgt not in self.nb.byid:
                self.warnings.append(f'{tag} to unknown id {tgt}')
            return f'[{label.strip()}](#{tgt})'
        if tag == 'xref':
            tgt = c.get('linkend')
            label = self.xref_text(tgt)
            return label if plain else f'[{esc(label)}](#{tgt})'
        if tag == 'ulink':
            url = c.get('url')
            label = clean_ws(txt()).strip()
            if not label and not list(c) and not url.startswith(('http', 'mailto')):
                self.warnings.append(f'SOURCE DEFECT: empty ulink to {url!r} dropped')
                return ''
            if plain:
                return label or url
            if not label or clean_ws(''.join(c.itertext())).strip() == url:
                return f'<{url}>'
            return f'[{label}]({url})'
        if tag == 'email':
            s = ''.join(c.itertext()).strip()
            return s
        if tag in ('emphasis',):
            s = txt()
            if plain or not s.strip():
                return s
            mark = '**' if c.get('role') in ('bold', 'strong') else '*'
            return self.wrap(s, mark)
        if tag in ('firstterm', 'citetitle', 'foreignphrase', 'replaceable'):
            s = txt()
            return s if plain or not s.strip() else self.wrap(s, '*')
        if tag == 'citation':
            return f'[{txt()}]' if plain else f'\\[{txt()}\\]'
        if tag == 'quote':
            return f'"{txt()}"'
        if tag == 'filename':
            s = txt()
            return s if plain else self.wrap(s, '**')
        if tag == 'simplelist':
            return ' '.join(clean_ws(self.inline(m, plain)).strip() for m in c.findall('member'))
        if tag in ('edition', 'abbrev', 'acronym', 'phrase', 'productname', 'orgname', 'member', 'title', 'superscript', 'subscript'):
            return txt()
        if tag == 'footnote':
            self.warnings.append('footnote rendered inline')
            return f' ({txt()})'
        if tag in ('itemizedlist', 'orderedlist', 'programlisting', 'note', 'warning', 'graphic', 'example', 'variablelist'):
            # block content nested in a para; handled by the block renderer
            return '\x00BLOCK\x00'
        self.warnings.append(f'UNHANDLED inline <{tag}>')
        return txt()

    @staticmethod
    def wrap(s, mark):
        lead = s[:len(s) - len(s.lstrip())]
        trail = s[len(s.rstrip()):]
        return f'{lead}{mark}{s.strip()}{mark}{trail}'

    # ----------------------------------------------------------------- block
    def para(self, el, indent=''):
        """A para may contain block children (lists inside para)."""
        blocks = []
        buf = [esc(el.text) if el.text else '']
        for c in el:
            if isinstance(c.tag, str) and c.tag in ('itemizedlist', 'orderedlist', 'programlisting', 'note', 'warning', 'example', 'variablelist'):
                blocks.append(('p', ''.join(buf)))
                blocks.append(('b', self.block(c, indent)))
                buf = [esc(c.tail) if c.tail else '']
                continue
            buf.append(self.inline_el(c, False))
            if c.tail:
                buf.append(esc(c.tail))
        blocks.append(('p', ''.join(buf)))
        out = []
        for kind, s in blocks:
            if kind == 'p':
                s = clean_ws(s).strip()
                if s:
                    out.append(indent + s)
            else:
                if s.strip():
                    out.append(s)
        return '\n\n'.join(out)

    def image_path(self, el):
        ref = el.get('fileref')
        return self.images_prefix + ref

    def block(self, el, indent=''):
        tag = el.tag
        if not isinstance(tag, str):
            return ''
        if tag in ('para', 'simpara'):
            # The TC stylesheet suppresses paragraphs directly inside a section that holds
            # a bibliography ("per OASIS layout"); mirror the published output.
            if self.parent_of.get(el) is not None and self.parent_of[el].find('bibliography') is not None \
                    and self.parent_of[el].tag in ('section', 'appendix'):
                self.warnings.append('bibliography-section para suppressed (matches TC stylesheet)')
                return ''
            return self.para(el, indent)
        if tag in ('itemizedlist', 'orderedlist'):
            out = []
            t = el.find('title')
            if t is not None:
                out.append(f'{indent}**{clean_ws(self.inline(t)).strip()}**')
            ordered = tag == 'orderedlist'
            k = 0
            items = []
            for li in el.findall('listitem'):
                k += 1
                marker = f'{k}. ' if ordered else '- '
                sub = indent + ' ' * len(marker)
                body = self.children(li, sub)
                body = body.lstrip()
                anchor = f"<a id='{li.get('id')}'></a>" if li.get('id') else ''
                items.append(f'{indent}{marker}{anchor}{body}')
            spacing_blank = True
            out.append(('\n\n' if spacing_blank else '\n').join(items))
            return '\n\n'.join(out)
        if tag == 'variablelist':
            out = []
            t = el.find('title')
            if t is not None:
                out.append(f'{indent}**{clean_ws(self.inline(t)).strip()}**')
            for ve in el.findall('varlistentry'):
                terms = ', '.join(clean_ws(self.inline(x)).strip() for x in ve.findall('term'))
                out.append(f'{indent}**{terms}**')
                li = ve.find('listitem')
                if li is not None:
                    out.append(self.children(li, indent))
            return '\n\n'.join(out)
        if tag in ('note', 'warning', 'caution', 'important', 'tip'):
            label = self.title_text(el) or tag.capitalize()
            body = self.children(el, '')
            lines = [f'**{label}**', ''] + body.split('\n')
            return '\n'.join(indent + ('> ' + l if l else '>') for l in lines)
        if tag == 'example':
            out = []
            anchor = f"<a id='{el.get('id')}'></a>" if el.get('id') else ''
            t = self.title_text(el)
            n = self.example_num[el]
            out.append(f'{indent}{anchor}*Example {n}. {esc(t)}*')
            out.append(self.children(el, indent))
            return '\n\n'.join(x for x in out if x.strip())
        if tag in ('programlisting', 'screen', 'literallayout'):
            text = ''.join(el.itertext())
            lines = text.split('\n')
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()
            fence = '```'
            while fence in text:
                fence += '`'
            lang = self.lang_for(el)
            body = '\n'.join(indent + l if l else l for l in lines)
            return f'{indent}{fence}{lang}\n{body}\n{indent}{fence}'
        if tag == 'graphic':
            # contentwidth is how a TC sizes a figure; the DocBook stylesheet
            # renders it as a pixel width at figure_dpi, and without it an SVG
            # draws at its natural size.
            m = re.fullmatch(r'([\d.]+)cm', el.get('contentwidth', ''))
            if m:
                px = round(float(m.group(1)) / 2.54 * self.profile['figure_dpi'])
                return f'{indent}<img src="{self.image_path(el)}" alt="" width="{px}">'
            return f'{indent}![]({self.image_path(el)})'
        if tag in ('mediaobject', 'figure', 'informalfigure'):
            return self.children(el, indent)
        if tag == 'imageobject':
            d = el.find('imagedata')
            return f'{indent}![]({self.images_prefix + d.get("fileref")})' if d is not None else ''
        if tag == 'bibliography':
            return self.children(el, indent)
        if tag == 'bibliomixed':
            ab = el.find('abbrev')
            head = ''
            rest = []
            if el.text and el.text.strip():
                rest.append(esc(el.text))
            for c in el:
                if c is ab:
                    head = clean_ws(''.join(c.itertext())).strip()
                else:
                    rest.append(self.inline_el(c, False))
                if c.tail:
                    rest.append(esc(c.tail))
            anchor = f"<a id='{el.get('id')}'></a>" if el.get('id') else ''
            body = clean_ws(''.join(rest)).strip()
            return f'{indent}{anchor}**\\[{head}\\]** {body}'.rstrip()
        if tag in ('title', 'titleabbrev'):
            return ''
        if tag in ('section', 'appendix'):
            return self.section(el)
        if tag == 'simplelist':
            return indent + self.inline_el(el, False)
        if tag in ('blockquote',):
            body = self.children(el, '')
            return '\n'.join(indent + ('> ' + l if l else '>') for l in body.split('\n'))
        self.warnings.append(f'UNHANDLED block <{tag}>')
        return self.children(el, indent)

    def lang_for(self, el):
        base = ''
        p = el.get(XML_BASE) or ''
        if p:
            base = p
        name = (base.split('/')[-1]).lower()
        for ext, lang in self.profile['code_languages'].items():
            if name.endswith(ext + '.xml') or name.endswith(ext):
                return lang
        return ''

    def children(self, el, indent=''):
        out = []
        for c in el:
            if not isinstance(c.tag, str) or c.tag == 'title':
                continue
            b = self.block(c, indent)
            if b.strip():
                out.append(b)
        return '\n\n'.join(out)

    def section(self, el):
        n = self.nb.num.get(el, '')
        depth = n.count('.') + 1
        title = self.title_text(el)
        role = el.get('role')
        suffix = {'normative': ' (Normative)', 'informative': ' (Informative)'}.get(role, '')
        if el.tag == 'appendix':
            label = f'Appendix {n} {title}{suffix}'
        else:
            label = f'{n} {title}{suffix}'
        anchor = el.get('id') or self.slug(label)
        self.toc.append((depth, label, anchor))
        t = el.find('title')
        title_md = clean_ws(self.inline(t)).strip() if t is not None else ''
        md_label = esc(label[:len(label) - len(title) - len(suffix)]) + title_md + suffix
        head = f"{'#' * min(depth, 6)} {md_label} <a id='{anchor}'></a>"
        body = self.children(el)
        return head + ('\n\n' + body if body.strip() else '')

    @staticmethod
    def slug(s):
        s = re.sub(r'[^\w\s.-]', '', s.lower())
        return re.sub(r'[\s.]+', '-', s).strip('-')

    # ----------------------------------------------------------- front matter
    def person(self, p):
        name = f"{p.findtext('firstname', '').strip()} {p.findtext('surname', '').strip()}"
        email = (p.findtext('email') or '').strip()
        org = p.find('affiliation/orgname')
        orgtxt = ''
        if org is not None:
            u = org.find('ulink')
            oname = clean_ws(''.join(org.itertext())).strip()
            orgtxt = f'[{oname}]({u.get("url")})' if u is not None else oname
        return f'{name} ({email}), {orgtxt}'

    def front(self):
        info = self.root.find('articleinfo')
        title = clean_ws(''.join(self.root.find('articleinfo/title').itertext())).strip()
        rel = {r.get('role'): clean_ws(''.join(r.itertext())).strip() for r in info.findall('releaseinfo')}
        stage = self.root.get('status', '')
        out = [f'![OASIS Logo]({LOGO})', '---', f'# {title}', f'## {stage}',
               f"## {info.findtext('pubdate').strip()}"]

        def urls(keys):
            vals = [rel[k] + (' (Authoritative)' if k.endswith('authoritative') else '') for k in keys if k in rel]
            return ' \\\n'.join(vals) if vals else 'N/A'

        out += ['#### This stage:', urls(['OASIS-specification-this', 'OASIS-specification-this-authoritative'])]
        out += ['#### Previous stage:', urls(['OASIS-specification-previous', 'OASIS-specification-previous-authoritative'])]
        out += ['#### Latest stage:', urls(['OASIS-specification-latest', 'OASIS-specification-latest-authoritative'])]
        committee = [r for r in info.findall('releaseinfo') if r.get('role') == 'committee']
        if committee:
            out += ['#### Technical Committee:', clean_ws(self.inline(committee[0])).strip()]
        ag = info.find('authorgroup')
        chairs = [o for o in ag.findall('othercredit') if o.get('role') == 'chair']
        if chairs:
            out += ['#### Chair:' if len(chairs) == 1 else '#### Chairs:', ' \\\n'.join(self.person(c) for c in chairs)]
        eds = ag.findall('editor')
        out += ['#### Editors:', ' \\\n'.join(self.person(e) for e in eds)]
        for ln in info.findall('legalnotice'):
            role = ln.get('role')
            if role == 'notices':
                continue  # rendered after the front matter, as in CSAF
            t = self.title_text(ln)
            out.append(f"#### {t}:" + (f" <a id='{ln.get('id')}'></a>" if ln.get('id') else ''))
            out.append(self.children(ln))
            if role == 'namespaces':
                ab = info.find('abstract')
                if ab is not None:
                    out += ['#### Abstract:', self.children(ab)]
        out.append('---')
        notices = [ln for ln in info.findall('legalnotice') if ln.get('role') == 'notices']
        for ln in notices:
            out += [f'## {self.title_text(ln)}', self.children(ln)]
            out.append('---')
        return '\n\n'.join(x for x in out if x is not None)

    def convert(self):
        body_parts = []
        for c in self.root:
            if c.tag in ('section', 'appendix'):
                body_parts.append(self.section(c))
        toc = ['# Table of Contents', '']
        for depth, label, anchor in self.toc:
            if depth > 3:
                continue
            toc.append(f"{'    ' * (depth - 1)}- [{esc(label)}](#{anchor})")
        doc = '\n\n'.join([self.front(), '\n'.join(toc), '---'] + body_parts)
        doc = re.sub(r'\n{3,}', '\n\n', doc).rstrip() + '\n'
        if '\x00BLOCK\x00' in doc:
            self.warnings.append('block content lost inside an inline context')
        return doc


def drop_unconditioned(root):
    """Drop what the OASIS stylesheet drops: an element whose condition
    attribute is set and does not contain "oasis"."""
    for parent in list(root.iter()):
        for c in list(parent):
            cond = ' '.join((c.get('condition') or '').split())
            if cond and 'oasis' not in cond:
                if c.tail:
                    prev = [x for x in parent][:list(parent).index(c)]
                    if prev:
                        prev[-1].tail = (prev[-1].tail or '') + c.tail
                    else:
                        parent.text = (parent.text or '') + c.tail
                parent.remove(c)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--profile', help='the specification profile (JSON)')
    ap.add_argument('--images-prefix', default='')
    a = ap.parse_args()
    profile = json.load(open(a.profile, encoding='utf-8')) if a.profile else {}
    root = ET.parse(a.src).getroot()
    conv = Converter(root, a.images_prefix, profile)
    md = conv.convert()
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(md)
    for w in sorted(set(conv.warnings)):
        print('WARNING:', w, file=sys.stderr)
    print(f'wrote {a.out}: {len(md.splitlines())} lines, {len(conv.toc)} headings, '
          f'{len(set(conv.warnings))} distinct warnings', file=sys.stderr)
    return 1 if any('unknown id' in w or 'lost' in w or 'UNHANDLED' in w for w in conv.warnings) else 0


if __name__ == '__main__':
    sys.exit(main())
