# RFQ synthetic offline demo verification — 2026-10-12

**Status: PASS, DEMONSTRATION ONLY.** No customer data; no accepted client work; no invoice or confirmed payment. No external messages, accounts or credentials were used.

## Exact commands and actual results

From `/cos-money-agent` repository workdir:

```bash
python3 -m unittest discover -s client-prep/rfq-quote-complete-demo-20261012 -p 'test_*.py' -v
```

**Actual output: Ran 17 tests in 0.060s — OK.**

From the demo folder:

```bash
sh run_demo.sh
python3 test_pipeline.py
```

**Actual runner:** `DEMO ONLY | rows=10 priced=2 review=8 priced_subtotal=61.25 | outputs/quote_demo.xlsx`; then **Ran 17 tests in 0.047s — OK**. Direct script also **Ran 17 tests in 0.042s — OK**. POSIX `/bin/sh` compatibility was verified; no Bash-specific flags remain.

PDF: `pdfinfo` confirms 1 A4 text-layer unencrypted PDF, compatible with local `pdftotext`. ZIP test on XLSX returns no corrupt member; every included XML document parsed successfully. Workbook has exactly three visible sheets: `Run Summary`, `Quote Draft`, `Review Queue`.

Input/result SHA-256 recorded immediately after successful run:

```text
5312e976425d1457d53d13452ab48d096f5132b22492c20ddad83b98db1c03db  samples/synthetic_rfq.pdf
afcb0223fae190902924f684b6c7b057714a2dae97fed3b1c3976f70ada36eb3  samples/catalogue.csv
a44fa5a44054490b6816bd375177ba3940be83e18d588987921665a6bdd82cb0  samples/approved_prices.csv
4330ec2b60d4ca6217680ab92d61ca0cea9daf19cee6377bcb0c965c76dc7d09  outputs/quote_demo.xlsx
```

## Reviewed exception cases

17 tests include exact approved SKU/UOM/price with versioned CSV row references, unknown SKU, unit mismatch, absent approved price, duplicate catalogue SKU, ambiguous duplicate prices, repeated RFQ SKU, zero quantity, unapproved price, currency mismatch, inactive SKU, explicit row-parse failure, duplicate row number rejection, invalid price, physical text-PDF extraction, structural/XLSX formula checks, and invalid PDF fail-closed no-output behavior. All 10 synthetic source line IDs appear in the Quote Draft; 2 approved extensions give **USD 61.25** provisional subtotal, and 8 unpriced exceptions appear in Review Queue. Final client quote is **NOT** approved or sendable.

## Buyer/finance boundary

Rami's original https://community.n8n.io/t/312281 is a **request for estimates and sample-dependent requirements**, not accepted work or authorization. This artifact uses fiction-only data, does not prove a production n8n workflow was run, and creates no receivable. **Before any first contact, the prime must confirm current paid scope, original buyer approval and provider/payer permission for actual age-17 Georgian work with separately adult Luara-owned commercial G&S/GE bank payment.** Never count expected fees as received.
