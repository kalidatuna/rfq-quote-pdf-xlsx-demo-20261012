"""Offline regression tests; never touch a real buyer or external service."""
import csv
from decimal import Decimal
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from pipeline import (DataError, extract_pdf_text, load_reference,
                      match_items, parse_rfq_text, run, Item)

HERE = Path(__file__).resolve().parent
CAT = HERE / 'samples' / 'catalogue.csv'
PRICES = HERE / 'samples' / 'approved_prices.csv'
PDF = HERE / 'samples' / 'synthetic_rfq.pdf'
BAD_ROW_PDF = HERE / 'samples' / 'malformed_row_rfq.pdf'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def catalogues():
    cv, c = load_reference(CAT, ('catalog_version','sku','description','uom','active'), 'catalog_version')
    pv, p = load_reference(PRICES, ('price_version','sku','currency','unit_price','approved'), 'price_version')
    return cv, c, pv, p


def check(items):
    cv, c, pv, p = catalogues()
    return match_items(items, 'USD', cv, c, pv, p)


def item(sku='BRK-20A', unit='EA', qty='4', line=1):
    return Item(line, sku, 'Safe synthetic test item', qty, unit)


class PipelineTests(unittest.TestCase):
    def test_real_text_pdf_extracts_and_keeps_all_lines(self):
        rfq, currency, items = parse_rfq_text(extract_pdf_text(PDF))
        self.assertEqual((rfq, currency, len(items)), ('RFQ-DEMO-20261012-A', 'USD', 10))
        self.assertEqual([x.line for x in items], list(range(1,11)))

    def test_exact_match_and_stable_csv_physical_row_refs(self):
        d = check([item()])[0]
        self.assertEqual(d.status, 'APPROVED')
        self.assertEqual(d.price, Decimal('12.50'))
        self.assertEqual(d.extension, Decimal('50.00'))
        self.assertEqual(d.catalogue_ref, 'CAT-DEMO-V1:row2')
        self.assertEqual(d.price_ref, 'PR-DEMO-V1:row2')

    def test_unknown_sku_unpriced(self):
        d = check([item('NOT-999')])[0]
        self.assertEqual(d.status, 'UNKNOWN_SKU')
        self.assertIsNone(d.price)

    def test_unit_mismatch_no_conversion(self):
        d = check([item('LGT-12W', 'M')])[0]
        self.assertEqual(d.status, 'UNIT_MISMATCH')
        self.assertIsNone(d.extension)

    def test_missing_price(self):
        d = check([item('SWT-ONE')])[0]
        self.assertEqual(d.status, 'MISSING_PRICE')
        self.assertEqual(d.catalogue_ref, 'CAT-DEMO-V1:row5')

    def test_duplicate_catalog_is_ambiguous_even_when_price_exists(self):
        d = check([item('CON-DUP')])[0]
        self.assertEqual(d.status, 'AMBIGUOUS_CATALOGUE')
        self.assertEqual(d.catalogue_ref, 'CAT-DEMO-V1:row6; CAT-DEMO-V1:row7')
        self.assertIsNone(d.price)

    def test_duplicate_price_never_picks_first(self):
        d = check([item('CAB-5M')])[0]
        self.assertEqual(d.status, 'AMBIGUOUS_PRICE')
        self.assertEqual(d.price_ref, 'PR-DEMO-V1:row6; PR-DEMO-V1:row7')

    def test_repeated_rfq_sku_both_held(self):
        a, b = check([item(line=1), item(line=2)])
        self.assertEqual(a.status, 'DUPLICATE_RFQ_SKU')
        self.assertEqual(b.status, 'DUPLICATE_RFQ_SKU')
        self.assertTrue(a.price is None and b.price is None)

    def test_invalid_zero_quantity(self):
        self.assertEqual(check([item(qty='0')])[0].status, 'INVALID_QUANTITY')

    def test_unapproved_price(self):
        self.assertEqual(check([item('CLIP-01', 'PK')])[0].status, 'UNAPPROVED_PRICE')

    def test_currency_conflict(self):
        self.assertEqual(check([item('EURO-01')])[0].status, 'CURRENCY_MISMATCH')

    def test_inactive_catalogue_entry(self):
        self.assertEqual(check([item('OLD-01')])[0].status, 'INACTIVE_SKU')

    def test_invalid_document_row_fails_closed(self):
        with self.assertRaisesRegex(DataError, 'Malformed item'):
            parse_rfq_text('RFQ ID: RFQ-DEMO-1\nCurrency: USD\n001 | BRK-20A | Test | 2 | EA\n'
                           '002 | CAB-2M | Test | 5 | EA | EXTRA')

    def test_malformed_item_like_rows_rejected_but_page_notes_preserved(self):
        header = ('RFQ ID: RFQ-DEMO-1\nCurrency: USD\n'
                  'LINE | CODE | DESCRIPTION | QTY | UOM\n'
                  'Page 1 of 2\nNote: dimensions | specifications are illustrative\n'
                  '1 | 2\n001 | BRK-20A | Test item | 4 | EA\n')
        rfq, currency, rows = parse_rfq_text(header + 'Page 2 of 2\n')
        self.assertEqual((rfq, currency, len(rows)), ('RFQ-DEMO-1', 'USD', 1))
        for bad in ('2 | LGT-12W | LED lamp | 3 | EA',
                    '0002 | LGT-12W | LED lamp | 3 | EA',
                    '12345678 | LGT-12W | LED lamp | 3 | EA',
                    'ABC | LGT-12W | LED lamp | 3 | EA',
                    '2 | | LED lamp | 3 | EA',
                    '2 | LGT-12W | LED lamp | 3',
                    '002 | LGT-12W | LED lamp | 3 | EA | EXTRA'):
            with self.subTest(bad=bad), self.assertRaisesRegex(DataError, 'Malformed item'):
                parse_rfq_text(header + bad)

    def test_real_pdf_malformed_second_row_fails_closed_without_quote(self):
        extracted = extract_pdf_text(BAD_ROW_PDF)
        self.assertIn('001 | BRK-20A', extracted)
        self.assertIn('2 | LGT-12W', extracted)
        with tempfile.TemporaryDirectory() as temporary:
            quote = Path(temporary) / 'must_not_generate.xlsx'
            with self.assertRaisesRegex(DataError, 'Malformed item'):
                run(BAD_ROW_PDF, CAT, PRICES, quote)
            self.assertFalse(quote.exists())

    def test_duplicate_line_number_rejected(self):
        with self.assertRaisesRegex(DataError, 'line numbers'):
            parse_rfq_text('RFQ ID: RFQ-DEMO-1\nCurrency: USD\n001 | BRK-20A | Test | 2 | EA\n'
                           '001 | CAB-2M | Test | 5 | EA')

    def test_invalid_prices_are_not_guessed(self):
        cv, c, pv, p = catalogues()
        p['BRK-20A'][0].values['unit_price'] = 'unknown'
        d = match_items([item()], 'USD', cv, c, pv, p)[0]
        self.assertEqual(d.status, 'INVALID_PRICE')
        self.assertIsNone(d.extension)

    def test_workbook_contains_quote_review_summary_and_formulas(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'demo.xlsx'
            results = run(PDF, CAT, PRICES, dest)
            self.assertEqual(len(results), 10)
            self.assertEqual(sum(x.status=='APPROVED' for x in results), 2)
            self.assertEqual(sum(x.status!='APPROVED' for x in results), 8)
            with ZipFile(dest) as z:
                self.assertIsNone(z.testzip())
                for path in z.namelist():
                    if path.endswith('.xml'):
                        ET.fromstring(z.read(path))
                workbook = z.read('xl/workbook.xml').decode()
                quote = z.read('xl/worksheets/sheet2.xml').decode()
                review = z.read('xl/worksheets/sheet3.xml').decode()
                summary = z.read('xl/worksheets/sheet1.xml').decode()
            self.assertIn('Run Summary', workbook)
            self.assertIn('Quote Draft', workbook)
            self.assertIn('Review Queue', workbook)
            self.assertIn('SUM(', summary)
            self.assertIn('IF(J5', quote)
            self.assertIn('CAT-DEMO-V1:row2', quote)
            self.assertIn('UNKNOWN_SKU', review)
            self.assertIn('AMBIGUOUS_CATALOGUE', review)
            self.assertIn('MISSING_PRICE', review)
            self.assertNotIn('50.00', review)

    def test_bad_pdf_does_not_create_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'bad.pdf'
            bad.write_bytes(b'Not a PDF')
            out = Path(tmp) / 'must_not_exist.xlsx'
            with self.assertRaises(DataError):
                run(bad, CAT, PRICES, out)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
