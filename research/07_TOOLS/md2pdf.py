#!/usr/bin/env python3
"""Minimal Markdown -> PDF renderer for the Find Us research deliverables.

Uses reportlab platypus. Handles: ATX headings (#..######), paragraphs,
unordered/ordered lists, fenced code blocks, tables (| ... |), bold/italic,
inline code, blockquotes. Falls back gracefully. Tables are rendered with a
pre-pass so column widths are consistent.
"""
import os, re, sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle,
                                Preformatted, HRFlowable)
from reportlab.lib import colors

styles = {}


def build_styles():
    def mk(name, b=False, size=9.3, lead=12.6, indent=0, leftind=0, mono=False,
           color=colors.HexColor('#222222'), parent=None, sb=None, sa=None):
        s = ParagraphStyle(name, parent=parent,
                           fontName='Helvetica-Bold' if b else ('Courier' if mono else 'Helvetica'),
                           fontSize=size, leading=lead, textColor=color,
                           alignment=TA_LEFT, spaceAfter=5, spaceBefore=0,
                           leftIndent=leftind, firstLineIndent=indent)
        if sb is not None:
            s.spaceBefore = sb
        if sa is not None:
            s.spaceAfter = sa
        styles[name] = s
    mk('h1', b=True, size=17, lead=20, sb=14, sa=8, color=colors.HexColor('#0d1b2a'))
    mk('h2', b=True, size=13.5, lead=16, sb=10, sa=6, color=colors.HexColor('#1b3a5b'))
    mk('h3', b=True, size=11.5, lead=14, sb=7, sa=4, color=colors.HexColor('#2d5a80'))
    mk('h4', b=True, size=10, lead=13, sb=5, sa=3, color=colors.HexColor('#3a6d99'))
    mk('body3', parent=None)
    mk('body', parent=None)
    mk('bullet', leftind=12)
    mk('num', leftind=14)
    mk('quote', parent=None)
    mk('codeblock', mono=True, size=7.4, lead=9.4)
    mk('tcell', size=7.6, lead=9.8)
    mk('tcellb', b=True, size=7.6, lead=9.8, color=colors.white)
    # fix h1..h4 spaceBefore
    for k in ('h1', 'h2', 'h3', 'h4'):
        styles[k].spaceBefore = 10 if k != 'h1' else 14
        styles[k].spaceAfter = 6 if k != 'h1' else 8
    styles['quote'] = ParagraphStyle('quote', parent=styles['body'], fontSize=8.9,
                                     leading=11.6, leftIndent=14,
                                     textColor=colors.HexColor('#444444'), spaceAfter=5)


def inline(text):
    t = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'`([^`]+)`', lambda m: '<font face="Courier" size="8">%s</font>' % m.group(1), t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', t)
    return t


def extract_tables(path):
    """Return list of (start_line, end_line, list[list[str]])."""
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    tables = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('|'):
            j = i
            rows = []
            while j < len(lines) and lines[j].strip().startswith('|'):
                cells = [c.strip() for c in lines[j].strip().strip('|').split('|')]
                # skip separator rows like |---|---|
                if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                    rows.append(cells)
                j += 1
            if rows:
                tables.append((i, j, rows))
            i = j
        else:
            i += 1
    return tables


def render_tables(path):
    flow = []
    for start, end, rows in extract_tables(path):
        ncols = max(len(r) for r in rows)
        data = []
        for ri, r in enumerate(rows):
            cells = []
            for c in (r[:ncols] + [''] * (ncols - len(r))):
                cells.append(Paragraph(inline(c), styles['tcellb'] if ri == 0 else styles['tcell']))
            data.append(cells)
        tbl = Table(data, colWidths=[(_width - 24 * mm) / ncols] * ncols, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#9fb3c8')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b3a5b')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        flow.append(tbl)
        flow.append(Spacer(1, 8))
    return flow


def table_at(path):
    """Return dict {start_line: rows} for tables."""
    return {s: rows for s, e, rows in extract_tables(path)}


def parse_body(path):
    """Return flowables for every line of the document, tables rendered in place."""
    with open(path, encoding='utf-8') as f:
        content = f.read()
    table_ranges = [(s, e) for s, e, _ in extract_tables(path)]
    tbl_rows = {s: rows for s, e, rows in extract_tables(path)}
    lines = content.split('\n')
    story = []
    in_code = False
    codebuf = []
    quote_lines = []
    list_mode = None      # 'bullet' / 'num'
    list_items = []
    normal = []
    i = 0

    def table_flow(rows):
        ncols = max(len(r) for r in rows)
        data = []
        for ri, r in enumerate(rows):
            cells = []
            for c in (r[:ncols] + [''] * (ncols - len(r))):
                cells.append(Paragraph(inline(c), styles['tcellb'] if ri == 0 else styles['tcell']))
            data.append(cells)
        tbl = Table(data, colWidths=[(_width - 24 * mm) / ncols] * ncols, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#9fb3c8')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b3a5b')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return [tbl, Spacer(1, 8)]

    def flush_quote():
        nonlocal quote_lines
        if quote_lines:
            story.append(Paragraph(inline(' '.join(l.lstrip('>').strip() for l in quote_lines)),
                                   ParagraphStyle('quote', parent=styles['body'],
                                                  leftIndent=14, textColor=colors.HexColor('#444444'))))
            quote_lines = []

    def flush_list():
        nonlocal list_items, list_mode
        if list_mode == 'bullet':
            for t in list_items:
                story.append(Paragraph(inline(t), styles['bullet'], bulletText='\u2022'))
        elif list_mode == 'num':
            for n, t in enumerate(list_items, 1):
                story.append(Paragraph(inline(t), styles['num'], bulletText=f'{n}.'))
        list_items, list_mode = [], None

    def flush_code():
        nonlocal codebuf
        if codebuf:
            story.append(Preformatted(''.join(codebuf).rstrip('\n'), styles['codeblock']))
            story.append(Spacer(1, 3))
            codebuf = []

    def flush_para():
        nonlocal normal
        if normal:
            story.append(Paragraph(inline(' '.join(normal)), styles['body']))
            normal = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()
        # table start: render entire table, skip to end
        if stripped.startswith('|'):
            flush_quote(); flush_list(); flush_code(); flush_para()
            if i in tbl_rows:
                story.extend(table_flow(tbl_rows[i]))
                end = i
                while end < len(lines) and lines[end].strip().startswith('|'):
                    end += 1
                i = end
                continue
        # fences
        if stripped.startswith('```'):
            if in_code:
                in_code = False
            else:
                flush_quote(); flush_list(); flush_code(); flush_para()
                in_code = True
            i += 1
            continue
        if in_code:
            codebuf.append(line + '\n')
            i += 1
            continue
        if not stripped:
            flush_quote(); flush_list(); flush_code(); flush_para()
            i += 1
            continue
        if stripped == '---':
            flush_quote(); flush_list(); flush_code(); flush_para()
            story.append(HRFlowable(width='100%', thickness=0.7,
                                    color=colors.HexColor('#9fb3c8'),
                                    spaceBefore=6, spaceAfter=8))
            i += 1
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            level = min(len(m.group(1)), 4)
            flush_quote(); flush_list(); flush_code(); flush_para()
            story.append(Paragraph(inline(re.sub(r'\s*\*\*.*\*\*$', '', m.group(2))),
                                   styles[f'h{level}']))
            i += 1
            continue
        if stripped.startswith('>'):
            flush_list(); flush_code(); flush_para()
            quote_lines.append(line)
            i += 1
            continue
        mb = re.match(r'^(\s*)[-*+]\s+(.*)$', line)
        mn = re.match(r'^(\s*)\d+[.)]\s+(.*)$', line)
        if mb:
            flush_quote(); flush_code(); flush_para()
            if list_mode != 'bullet':
                flush_list(); list_mode = 'bullet'
            list_items.append(mb.group(2))
            i += 1
            continue
        if mn:
            flush_quote(); flush_code(); flush_para()
            if list_mode != 'num':
                flush_list(); list_mode = 'num'
            list_items.append(mn.group(2))
            i += 1
            continue
        flush_quote(); flush_list(); flush_code()
        if list_mode:
            list_items[-1] += ' ' + stripped
        else:
            normal.append(stripped)
        i += 1
    flush_quote(); flush_list(); flush_code(); flush_para()
    return story


def render(md_path, pdf_path):
    global _width
    doc = BaseDocTemplate(pdf_path, pagesize=A4,
                          leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=18 * mm, bottomMargin=18 * mm,
                          title=os.path.basename(pdf_path))
    _width = doc.width
    build_styles()
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='f')

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont('Helvetica', 7.2)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(20 * mm, 9 * mm, 'Find Us — research deliverable')
        canvas.drawRightString(A4[0] - 20 * mm, 9 * mm, 'Page %d' % d.page)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[frame], onPage=footer)])
    story = parse_body(md_path)
    doc.build(story)
    print('wrote', pdf_path)


if __name__ == '__main__':
    for src in sys.argv[1:]:
        base = os.path.splitext(os.path.basename(src))[0]
        out = os.path.join(os.path.dirname(src) or '.', base + '.pdf')
        render(src, out)