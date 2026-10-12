"""Dependency-free, explicitly limited OOXML writer for this offline demo.

Uses only zipfile + XML; never evaluates untrusted text as an Excel formula.
Human review annotations do not trigger approval or price changes.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import re
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED


XML_PREFIX = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def clean(value: object) -> str:
    s = str(value)
    # Excel XML 1.0 cannot contain certain characters; never turn user text into formulas.
    return escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s), {'"': '&quot;', "'": '&apos;'})


def col_name(index: int) -> str:
    result = ''
    while index:
        index, rest = divmod(index - 1, 26)
        result = chr(65 + rest) + result
    return result


def cell(row: int, col: int, value: object, style: int = 0,
         formula: str | None = None, cached: object | None = None) -> str:
    coord = f'{col_name(col)}{row}'
    if formula is not None:
        # Formulas are hardcoded and operate only on numeric/approved cells.
        attrs = ' t="str"' if cached is None else ''
        val = '' if cached is None else str(cached)
        return f'<c r="{coord}" s="{style}"{attrs}><f>{clean(formula)}</f><v>{clean(val)}</v></c>'
    if value is None or value == '':
        return ''
    if isinstance(value, (Decimal, int, float)):
        return f'<c r="{coord}" s="{style}"><v>{clean(value)}</v></c>'
    text = clean(value)
    return f'<c r="{coord}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def sheet_xml(rows: list[list[str]], widths: list[int], frozen: int = 0,
              filter_header: int = 0, filter_cols: int = 0,
              extra: str = '') -> str:
    longest = max((len(x) for x in rows), default=1)
    col_xml = ''.join(f'<col min="{i}" max="{i}" width="{min(60, max(10, w))}" customWidth="1"/>'
                      for i, w in enumerate(widths, 1))
    data = ''.join(f'<row r="{r}" ht="{24 if r == 1 else 20}" customHeight="1">'
                   + ''.join(line) + '</row>' for r, line in enumerate(rows, 1))
    views = ('<sheetViews><sheetView workbookViewId="0">'
             + (f'<pane ySplit="{frozen}" topLeftCell="A{frozen + 1}" activePane="bottomLeft" state="frozen"/>'
                f'<selection pane="bottomLeft" activeCell="A{frozen + 1}" sqref="A{frozen + 1}"/>' if frozen else '')
             + '</sheetView></sheetViews>')
    filt = (f'<autoFilter ref="A{filter_header}:{col_name(filter_cols)}{longest}"/>'
            if filter_header and filter_cols and longest >= filter_header else '')
    return (XML_PREFIX + f'<worksheet xmlns="{NS}">' + views
            + f'<cols>{col_xml}</cols><sheetData>{data}</sheetData>'
            + filt + extra + '</worksheet>')


def rows_from_cells(raw: list[list[tuple[object, int] | object]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for i, values in enumerate(raw, 1):
        current = []
        for j, entry in enumerate(values, 1):
            v, style = entry if isinstance(entry, tuple) else (entry, 0)
            current.append(cell(i, j, v, style))
        rows.append(current)
    return rows


STYLES = XML_PREFIX + f'''<styleSheet xmlns="{NS}">
<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts>
<fonts count="4"><font><sz val="10"/><name val="Aptos"/></font>
<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Aptos"/></font>
<font><b/><sz val="15"/><color rgb="FF142D48"/><name val="Aptos"/></font>
<font><b/><sz val="10"/><color rgb="FF142D48"/><name val="Aptos"/></font></fonts>
<fills count="6"><fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF173A5E"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE6F2FA"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF0CE"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE5F4EB"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="8">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="3" fillId="3" borderId="0" xfId="0" applyFill="1" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="3" fillId="3" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1"/>
</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def write_quote_workbook(output: Path, rfq: str, currency: str, catalog_version: str,
                         price_version: str, decisions: list, pdf_filename: str,
                         pdf_hash: str, catalog_hash: str, price_hash: str) -> None:
    approved = [d for d in decisions if d.status == 'APPROVED']
    reviewed = [d for d in decisions if d.status != 'APPROVED']
    subtotal = sum((d.extension for d in approved), Decimal('0.00'))

    summary = rows_from_cells([
        [('SYNTHETIC RFQ | DEMO ONLY — NOT A CLIENT QUOTE', 6)],
        ['Every price must be supported by the approved source. No quote may be sent without human review.'],
        [],
        [('RFQ reference', 2), rfq],
        [('Currency', 2), currency],
        [('Catalogue version', 2), catalog_version],
        [('Approved price version', 2), price_version],
        [('PDF fixture', 2), pdf_filename],
        [],
        [('RFQ lines', 2), len(decisions)],
        [('Priced lines', 2), len(approved)],
        [('Human-review lines', 2), len(reviewed)],
        [('Approved-lines subtotal (not grand total)', 2), (subtotal, 7)],
        [('Final quotation status', 2), 'DRAFT / NOT APPROVED / DO NOT SEND'],
        [],
        [('RFQ SHA-256', 2), pdf_hash],
        [('Catalogue CSV SHA-256', 2), catalog_hash],
        [('Approved prices SHA-256', 2), price_hash],
        [],
        [('Controls', 2), 'Exact SKU and unit only; no automatic substitution or conversion'],
        ['', 'Price and catalogue row numbers are physical CSV rows (header = row 1)'],
        ['', 'Review sheet is an annotation queue, never a price approval workflow'],
        ['', 'Formula totals show confirmed items only; unresolved lines remain unpriced'],
    ])
    end = len(decisions) + 4
    summary[9][1] = cell(10, 2, None, formula=f"COUNTA('Quote Draft'!A5:A{end})", cached=len(decisions))
    summary[10][1] = cell(11, 2, None, formula=f'COUNTIF(\'Quote Draft\'!J5:J{end},"APPROVED")', cached=len(approved))
    summary[11][1] = cell(12, 2, None, formula=f'B10-B11', cached=len(reviewed))
    summary[12][1] = cell(13, 2, None, style=7,
                         formula=f"SUM('Quote Draft'!I5:I{end})", cached=f'{subtotal:.2f}')

    header = ['RFQ line', 'Requested SKU', 'Requested description', 'Quantity', 'Requested unit',
              'Catalogue description', 'Catalogue unit', 'Approved unit price', 'Priced extension',
              'Decision', 'Review reason / accepted match', 'Catalogue row ref', 'Price row ref', 'Reviewer notes']
    quote = rows_from_cells([
        [('SYNTHETIC QUOTATION DRAFT — DO NOT SEND', 6)],
        ['All prices from the independent approved-price CSV only. Reviewer approval required for all flagged lines.'],
        [],
        [(x, 1) for x in header],
    ])
    for index, d in enumerate(decisions, 5):
        status_style = 3 if d.status == 'APPROVED' else 4
        details = [d.item.line, d.item.sku, d.item.description,
                   int(d.item.quantity_text) if d.item.quantity_text.isdigit() else d.item.quantity_text,
                   d.item.uom, d.catalogue_description, d.catalogue_uom,
                   (d.price, 5) if d.price is not None else '', None,
                   (d.status, status_style), d.reason,
                   d.catalogue_ref, d.price_ref, '']
        cells = rows_from_cells([details])[0]
        # rows_from_cells above creates row-1 addresses; rebase to actual Excel row.
        cells = [re.sub(r' r="([A-Z]+)1"', rf' r="\g<1>{index}"', x, count=1) for x in cells]
        cells[8] = cell(index, 9, None, style=5,
                        formula=f'IF(J{index}="APPROVED",ROUND(D{index}*H{index},2),"")',
                        cached=f'{d.extension:.2f}' if d.extension is not None else None)
        quote.append(cells)

    review_header = ['RFQ line', 'SKU', 'Requested description', 'Quantity', 'Unit',
                     'Hold reason', 'Review guidance', 'Catalogue candidates', 'Price candidates',
                     'Reviewer disposition (manual)', 'Reviewer notes (manual)']
    review = rows_from_cells([
        [('HUMAN REVIEW QUEUE — NOTHING AUTO-APPROVED', 6)],
        ['Do not approve substitutions or prices in this demo. Use notes for verification with client.'],
        [],
        [(x, 1) for x in review_header],
    ])
    for i, d in enumerate(reviewed, start=5):
        x = [d.item.line, d.item.sku, d.item.description,
             int(d.item.quantity_text) if d.item.quantity_text.isdigit() else d.item.quantity_text,
             d.item.uom, (d.status, 4), d.reason, d.catalogue_ref,
             d.price_ref, '', '']
        cs = rows_from_cells([x])[0]
        review.append([re.sub(r' r="([A-Z]+)1"', rf' r="\g<1>{i}"', c, count=1) for c in cs])

    names = ['Run Summary', 'Quote Draft', 'Review Queue']
    sheets = [
        sheet_xml(summary, [43, 84]),
        sheet_xml(quote, [12, 20, 33, 13, 17, 38, 19, 22, 23, 26, 52, 27, 27, 31],
                  frozen=4, filter_header=4, filter_cols=14),
        sheet_xml(review, [12, 20, 40, 13, 14, 24, 56, 34, 33, 31, 42],
                  frozen=4, filter_header=4, filter_cols=11),
    ]
    ct = XML_PREFIX + ('''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
    ''' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,4))
    + '</Types>')
    root_rel = XML_PREFIX + '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook = XML_PREFIX + f'''<workbook xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>''' + ''.join(f'<sheet name="{clean(n)}" sheetId="{i}" r:id="rId{i}"/>' for i,n in enumerate(names,1)) + '</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>'
    workbook_rel = XML_PREFIX + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,4)) + '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    temp = output.with_suffix('.xlsx.tmp')
    with ZipFile(temp, 'w', compression=ZIP_DEFLATED) as book:
        for name, contents in [('[Content_Types].xml', ct), ('_rels/.rels', root_rel),
                               ('xl/workbook.xml', workbook),
                               ('xl/_rels/workbook.xml.rels', workbook_rel),
                               ('xl/styles.xml', STYLES)]:
            book.writestr(name, contents)
        for i, xml in enumerate(sheets, 1):
            book.writestr(f'xl/worksheets/sheet{i}.xml', xml)
    temp.replace(output)
