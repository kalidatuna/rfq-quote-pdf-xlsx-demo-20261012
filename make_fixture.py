#!/usr/bin/env python3
"""Regenerate the static *fictional* text-layer RFQ using ReportLab (test setup only)."""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BASE = Path(__file__).resolve().parent
TARGET = BASE / 'samples' / 'synthetic_rfq.pdf'

LINES = [
    'DEMONSTRATION INPUT ONLY - NOT A REAL CUSTOMER REQUEST',
    'RFQ ID: RFQ-DEMO-20261012-A',
    'Customer: Blue Lantern Electrical (fictional)',
    'Currency: USD',
    'LINE | CODE | DESCRIPTION | QTY | UOM',
    '001 | BRK-20A | Miniature circuit breaker 20A | 4 | EA',
    '002 | CAB-2M | Power cable 2 metres | 3 | EA',
    '003 | NOT-999 | Imaginary DIN rail adaptor | 1 | EA',
    '004 | LGT-12W | LED downlight 12W | 5 | M',
    '005 | SWT-ONE | Single gang wall switch | 6 | EA',
    '006 | CON-DUP | Connector fitting | 2 | EA',
    '007 | CAB-5M | Power cable 5 metres | 2 | EA',
    '008 | CLIP-01 | Cable clip pack | 7 | PK',
    '009 | EURO-01 | European fitting | 1 | EA',
    '010 | OLD-01 | Retired terminal | 2 | EA',
    'END OF DEMONSTRATION RFQ - ALL DATA IS SYNTHETIC',
]


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(TARGET), pagesize=A4, pageCompression=0, invariant=1)
    pdf.setTitle('Synthetic RFQ - DEMO ONLY')
    pdf.setAuthor('Offline RFQ Demo / no buyer data')
    pdf.setFont('Courier', 10)
    height = A4[1]
    for number, line in enumerate(LINES):
        pdf.drawString(45, height - 65 - number * 26, line)
    pdf.showPage()
    pdf.save()
    print('Created synthetic text-layer PDF:', TARGET)


if __name__ == '__main__':
    main()
