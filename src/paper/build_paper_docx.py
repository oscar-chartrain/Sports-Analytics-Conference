"""
build_paper_docx.py -- builds the SSAC submission .docx from paper/full_paper.md
on top of the conference's own "Paper Template.docx" (kept in paper/, not committed:
it is SSAC's file; download it from the competition and place it there),
so the template's page setup, footers and logo are preserved. SSAC does not
accept LaTeX; this is the submission format.

Template rules applied (from the template's own text): Cambria; body 11pt,
single spaced, 11pt after each paragraph; section headers 16pt bold,
subsection headers 12pt bold; title 18pt bold; track line 14pt; margins
1in sides, 1.1in top, 1.2in bottom (inherited from the template's section).

Supported markdown subset: # title, ## section, ### subsection, paragraphs,
"- " bullets, "1. " numbered items, pipe tables, ![alt](path) images,
**bold**, *italic*, `code`. Image paths resolve relative to paper/.

Usage: python3 build_paper_docx.py --paper-id "<ID>" [--out paper/submission.docx]
"""
import argparse
import copy
import os
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE = os.path.join(REPO_ROOT, 'paper', 'Paper Template.docx')
SRC_MD = os.path.join(REPO_ROOT, 'paper', 'full_paper.md')
FONT = 'Cambria'
TRACK = 'Other Sports'

INLINE = re.compile(r'(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)')


def set_font(run, size, bold=None, italic=None, mono=False):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    for attr in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rfonts.set(qn(attr), 'Consolas' if mono else FONT)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_runs(par, text, size, bold=False):
    """Adds text with **bold**, *italic* and `code` spans as runs."""
    text = text.replace('\\*', '∗')  # literal asterisk (rho*) must not parse as italic
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith('**') and piece.endswith('**'):
            r = par.add_run(piece[2:-2])
            set_font(r, size, bold=True)
        elif piece.startswith('`') and piece.endswith('`'):
            r = par.add_run(piece[1:-1])
            set_font(r, size - 1, bold=bold, mono=True)
        elif piece.startswith('*') and piece.endswith('*') and len(piece) > 2:
            r = par.add_run(piece[1:-1])
            set_font(r, size, bold=bold, italic=True)
        else:
            r = par.add_run(piece)
            set_font(r, size, bold=bold)


def fmt(par, after=11, before=0, keep_next=False, align=None):
    pf = par.paragraph_format
    pf.space_after = Pt(after)
    pf.space_before = Pt(before)
    pf.line_spacing = 1.0
    pf.keep_with_next = keep_next
    if align is not None:
        par.alignment = align


def add_par(doc, text, size=11, bold=False, after=11, before=0, keep_next=False, align=None):
    par = doc.add_paragraph()
    add_runs(par, text, size, bold=bold)
    fmt(par, after=after, before=before, keep_next=keep_next, align=align)
    return par


def add_list_item(doc, text, marker):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Inches(0.3)
    par.paragraph_format.first_line_indent = Inches(-0.2)
    add_runs(par, f'{marker} ' + text, 11)
    fmt(par, after=4)
    par.paragraph_format.left_indent = Inches(0.3)
    par.paragraph_format.first_line_indent = Inches(-0.2)
    return par


def set_cell_borders(cell):
    tcpr = cell._element.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:color'), '808080')
        borders.append(el)
    tcpr.append(borders)


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    ncols = len(header)
    table = doc.add_table(rows=1 + len(body), cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ci, text in enumerate(header):
        cell = table.rows[0].cells[ci]
        cell.paragraphs[0].text = ''
        add_runs(cell.paragraphs[0], text, 9, bold=True)
        fmt(cell.paragraphs[0], after=2)
        set_cell_borders(cell)
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:fill'), 'E7E6E6')
        cell._element.get_or_add_tcPr().append(shd)
    for ri, row in enumerate(body, start=1):
        for ci in range(ncols):
            cell = table.rows[ri].cells[ci]
            cell.paragraphs[0].text = ''
            add_runs(cell.paragraphs[0], row[ci] if ci < len(row) else '', 9)
            fmt(cell.paragraphs[0], after=2)
            set_cell_borders(cell)
    if header[0] == 'Fix':
        table.autofit = False
        widths = [3.1] + [0.85] * (ncols - 1)
        for r in table.rows:
            for ci, w in enumerate(widths):
                r.cells[ci].width = Inches(w)
    if len(body) <= 12:
        for r in table.rows[:-1]:
            for c in r.cells:
                for pp in c.paragraphs:
                    pp.paragraph_format.keep_with_next = True
    # keep header row from splitting, repeat on page break
    trpr = table.rows[0]._tr.get_or_add_trPr()
    hdr = OxmlElement('w:tblHeader')
    hdr.set(qn('w:val'), 'true')
    trpr.append(hdr)
    spacer = doc.add_paragraph()
    fmt(spacer, after=6)


def add_image(doc, path, alt):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # text width is 6.5 in; widths chosen so the figures stay legible without dominating a page
    name = str(path)
    width = 4.6 if any(k in name for k in ('leverage_explainer','split_half','positive_control','bootstrap_rank')) else 5.6 if 'allshots' in name else 3.8 if 'disattenuation' in name else 6.0
    par.add_run().add_picture(path, width=Inches(width))
    fmt(par, after=4, keep_next=True, align=WD_ALIGN_PARAGRAPH.CENTER)


def split_row(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def clear_body(doc):
    body = doc.element.body
    sect = body.find(qn('w:sectPr'))
    for child in list(body):
        if child is not sect:
            body.remove(child)


def build(paper_id, out_path):
    if not os.path.exists(TEMPLATE):
        raise SystemExit(f'Template not found at {TEMPLATE}. Place the conference template there first.')
    doc = Document(TEMPLATE)
    clear_body(doc)
    lines = open(SRC_MD, encoding='utf8').read().split('\n')

    i = 0
    title_done = False
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith('# ') and not title_done:
            add_par(doc, line[2:].strip(), size=18, bold=True, after=4)
            add_par(doc, f'Track: {TRACK}', size=14, after=4)
            add_par(doc, f'Paper ID: {paper_id}', size=11, after=11)
            title_done = True
            i += 1
        elif line.startswith('## '):
            add_par(doc, line[3:].strip(), size=16, bold=True, after=8, before=6, keep_next=True)
            i += 1
        elif line.startswith('### '):
            add_par(doc, line[4:].strip(), size=12, bold=True, after=6, before=4, keep_next=True)
            i += 1
        elif line.startswith('!['):
            m = re.match(r'!\[(.*?)\]\((.*?)\)', line)
            add_image(doc, os.path.normpath(os.path.join(REPO_ROOT, 'paper', m.group(2))), m.group(1))
            i += 1
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = split_row(lines[i])
                if not all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            add_table(doc, rows)
        elif re.match(r'^- ', line):
            add_list_item(doc, line[2:], '•')
            i += 1
        elif re.match(r'^\d+\. ', line):
            num = re.match(r'^(\d+)\. ', line).group(1)
            add_list_item(doc, re.sub(r'^\d+\. ', '', line), f'{num}.')
            i += 1
        else:
            # caption lines ("**Table n.**", "**Figure n.**") stay with their table or figure
            is_caption = line.startswith('**Table') or line.startswith('**Figure')
            add_par(doc, line, size=10 if is_caption else 11, after=6 if is_caption else 11,
                    keep_next=line.startswith('**Table') or line.startswith('**At a glance'))
            i += 1

    # blind review: drop the template authors' names from the file properties
    doc.core_properties.author = ''
    doc.core_properties.last_modified_by = ''
    doc.save(out_path)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--paper-id', default='[Paper ID to be filled in]')
    ap.add_argument('--out', default=os.path.join(REPO_ROOT, 'paper', 'submission.docx'))
    args = ap.parse_args()
    build(args.paper_id, args.out)
