#!/usr/bin/env python3
"""Strict offline text-PDF RFQ -> approved-catalogue XLSX draft.

DEMO ONLY. No network, no inference/pricing engine, no outreach/ERP integration.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re
import subprocess

from xlsx_writer import write_quote_workbook


MAX_PDF_BYTES = 5_000_000
MAX_CSV_BYTES = 2_000_000
MAX_RFQ_LINES = 50
MAX_REFERENCE_ROWS = 1000
ALLOWED_UNITS = {"EA", "M", "BOX", "PK"}
RFQ_HEADER = re.compile(r"^RFQ ID:\s*(RFQ-[A-Z0-9-]{2,70})\s*$", re.M)
CURRENCY_HEADER = re.compile(r"^Currency:\s*([A-Z]{3})\s*$", re.M)
ROW_START = re.compile(r"^\s*\d{3}\s*\|")
ROW = re.compile(
    r"^\s*(\d{3})\s*\|\s*([A-Z0-9-]{2,40})\s*\|\s*([^|]{1,120})\s*\|\s*([^|]{1,20})\s*\|\s*([A-Z]{1,8})\s*$"
)
SKU = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,39}$")
VERSION = re.compile(r"^[A-Z0-9][A-Z0-9._-]{1,63}$")
MONEY = re.compile(r"^(?:0|[1-9]\d{0,8})(?:\.\d{1,2})?$")


class DataError(ValueError):
    """Unsafe input or layout deviates from this narrow supported demo contract."""


@dataclass(frozen=True)
class Item:
    line: int
    sku: str
    description: str
    quantity_text: str
    uom: str


@dataclass(frozen=True)
class RefRow:
    row: int  # Physical CSV row number including header (first data line = 2).
    sku: str
    values: dict[str, str]


@dataclass(frozen=True)
class Decision:
    item: Item
    status: str
    reason: str
    catalogue_description: str = ""
    catalogue_uom: str = ""
    price: Decimal | None = None
    extension: Decimal | None = None
    catalogue_ref: str = ""
    price_ref: str = ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_pdf_text(pdf: Path) -> str:
    if not pdf.is_file() or pdf.stat().st_size > MAX_PDF_BYTES or pdf.stat().st_size == 0:
        raise DataError("PDF must exist and be <= 5 MB")
    if pdf.read_bytes()[:5] != b"%PDF-":
        raise DataError("Input does not have a PDF header")
    try:
        meta = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True,
                              check=True, timeout=15)
        pages = re.search(r"^Pages:\s*(\d+)", meta.stdout, re.M)
        if not pages or int(pages.group(1)) > 5:
            raise DataError("Only 1-5 page text PDFs are supported")
        result = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"],
                                capture_output=True, text=True, check=True, timeout=15)
    except FileNotFoundError as exc:
        raise DataError("poppler tools pdfinfo and pdftotext must be installed") from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise DataError("Unable to read the supplied text-based PDF") from exc
    if not result.stdout.strip() or len(result.stdout) > 250_000:
        raise DataError("PDF has no extractable text or is too large (scans/OCR unsupported)")
    return result.stdout.replace("\r\n", "\n")


def parse_rfq_text(text: str) -> tuple[str, str, list[Item]]:
    ids = RFQ_HEADER.findall(text)
    currencies = CURRENCY_HEADER.findall(text)
    if len(ids) != 1 or len(currencies) != 1:
        raise DataError("Expected exactly one 'RFQ ID:' and one 'Currency:' header")
    items: list[Item] = []
    for raw in text.splitlines():
        if ROW_START.match(raw):
            match = ROW.fullmatch(raw)
            if not match:
                raise DataError(f"Malformed item row (would risk silently dropping a line): {raw[:100]!r}")
            number, sku, description, qty, uom = match.groups()
            items.append(Item(int(number), sku, description.strip(), qty.strip(), uom))
    if not items or len(items) > MAX_RFQ_LINES:
        raise DataError(f"Expected 1-{MAX_RFQ_LINES} explicitly numbered RFQ lines")
    expected = list(range(1, len(items) + 1))
    actual = [x.line for x in items]
    if actual != expected:
        raise DataError("RFQ line numbers must be unique and contiguous starting from 001")
    return ids[0], currencies[0], items


def load_reference(path: Path, fields: tuple[str, ...], version_col: str) -> tuple[str, dict[str, list[RefRow]]]:
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_CSV_BYTES:
        raise DataError(f"Reference CSV unavailable or exceeds 2 MB: {path.name}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(k not in reader.fieldnames for k in fields):
            raise DataError(f"{path.name} must have columns: {', '.join(fields)}")
        by_code: dict[str, list[RefRow]] = defaultdict(list)
        seen_versions: set[str] = set()
        count = 0
        for row_no, values in enumerate(reader, start=2):
            count += 1
            if count > MAX_REFERENCE_ROWS or None in values:
                raise DataError(f"Invalid or excessive reference rows in {path.name}")
            values = {k: (v or "").strip() for k, v in values.items()}
            code = values['sku'].upper()
            version = values[version_col]
            if not SKU.fullmatch(code) or not VERSION.fullmatch(version):
                raise DataError(f"Invalid SKU/version at {path.name}:{row_no}")
            seen_versions.add(version)
            by_code[code].append(RefRow(row_no, code, values))
    if count == 0 or len(seen_versions) != 1:
        raise DataError(f"Reference must have one nonempty version and at least one row: {path.name}")
    return seen_versions.pop(), by_code


def money(text: str) -> Decimal | None:
    if not MONEY.fullmatch(text):
        return None
    try:
        return Decimal(text).quantize(Decimal('0.01'))
    except InvalidOperation:
        return None


def match_items(items: list[Item], currency: str, catalog_version: str,
                catalog: dict[str, list[RefRow]], price_version: str,
                prices: dict[str, list[RefRow]]) -> list[Decision]:
    seen_rfqs = Counter(x.sku for x in items)
    decisions: list[Decision] = []
    for item in items:
        cat_rows = catalog.get(item.sku, [])
        price_rows = prices.get(item.sku, [])
        cat_ref = "; ".join(f"{catalog_version}:row{x.row}" for x in cat_rows)
        price_ref = "; ".join(f"{price_version}:row{x.row}" for x in price_rows)
        cat_descr = cat_rows[0].values.get('description', '') if len(cat_rows) == 1 else ""
        cat_unit = cat_rows[0].values.get('uom', '') if len(cat_rows) == 1 else ""
        def held(status: str, reason: str) -> Decision:
            return Decision(item, status, reason, cat_descr, cat_unit, None, None, cat_ref, price_ref)

        if seen_rfqs[item.sku] > 1:
            decisions.append(held("DUPLICATE_RFQ_SKU", "Repeated request code; review potential duplicate billing"))
            continue
        if not re.fullmatch(r"[1-9]\d{0,6}", item.quantity_text):
            decisions.append(held("INVALID_QUANTITY", "Only positive whole-unit quantities are supported"))
            continue
        if item.uom not in ALLOWED_UNITS:
            decisions.append(held("UNKNOWN_UNIT", "Requested unit not in approved unit vocabulary"))
            continue
        if len(cat_rows) == 0:
            decisions.append(held("UNKNOWN_SKU", "Code absent from catalogue; no description substitution"))
            continue
        if len(cat_rows) > 1:
            decisions.append(held("AMBIGUOUS_CATALOGUE", "Several catalogue entries share this code"))
            continue
        if cat_rows[0].values.get('active') != 'yes':
            decisions.append(held("INACTIVE_SKU", "Catalogue item not marked active"))
            continue
        if cat_unit != item.uom:
            decisions.append(held("UNIT_MISMATCH", "Unit mismatch; no implicit pack or length conversion"))
            continue
        if len(price_rows) == 0:
            decisions.append(held("MISSING_PRICE", "No approved price for this exact SKU"))
            continue
        if len(price_rows) > 1:
            decisions.append(held("AMBIGUOUS_PRICE", "Multiple prices found; human must choose reference"))
            continue
        price_row = price_rows[0]
        if price_row.values.get('approved') != 'yes':
            decisions.append(held("UNAPPROVED_PRICE", "Price approval flag is not yes"))
            continue
        if price_row.values.get('currency') != currency:
            decisions.append(held("CURRENCY_MISMATCH", "Price currency differs from RFQ currency"))
            continue
        unit_price = money(price_row.values.get('unit_price', ''))
        if unit_price is None:
            decisions.append(held("INVALID_PRICE", "Price is missing, negative or not a decimal amount"))
            continue
        qty = int(item.quantity_text)
        decisions.append(Decision(item, "APPROVED", "Exact SKU, unit and approved reference price",
                                  cat_descr, cat_unit, unit_price,
                                  (unit_price * qty).quantize(Decimal('0.01')), cat_ref, price_ref))
    return decisions


def run(pdf: Path, catalogue_csv: Path, approved_prices_csv: Path, output: Path) -> list[Decision]:
    rfq_id, currency, items = parse_rfq_text(extract_pdf_text(pdf))
    catalog_version, catalog = load_reference(
        catalogue_csv, ('catalog_version','sku','description','uom','active'), 'catalog_version')
    price_version, prices = load_reference(
        approved_prices_csv, ('price_version','sku','currency','unit_price','approved'), 'price_version')
    results = match_items(items, currency, catalog_version, catalog, price_version, prices)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_quote_workbook(output, rfq_id, currency, catalog_version, price_version,
                         results, pdf.name, sha256(pdf),
                         sha256(catalogue_csv), sha256(approved_prices_csv))
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description='OFFLINE / SYNTHETIC DEMO ONLY: text RFQ PDF to reviewable XLSX quote')
    ap.add_argument('--rfq', type=Path, required=True)
    ap.add_argument('--catalogue', type=Path, required=True)
    ap.add_argument('--prices', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    try:
        results = run(args.rfq, args.catalogue, args.prices, args.out)
    except (DataError, OSError) as error:
        ap.exit(2, f"ERROR (no quote accepted): {error}\n")
    priced = [r for r in results if r.status == 'APPROVED']
    subtotal = sum((r.extension or Decimal('0.00') for r in priced), Decimal('0.00'))
    print(f"DEMO ONLY | rows={len(results)} priced={len(priced)} review={len(results)-len(priced)} "
          f"priced_subtotal={subtotal:.2f} | {args.out}")


if __name__ == '__main__':
    main()
