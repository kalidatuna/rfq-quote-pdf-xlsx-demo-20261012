# Synthetic RFQ PDF -> approved catalogue -> XLSX quotation demo

**DEMO ONLY. NO CLIENT AUTHORIZATION, NO ACCEPTED PAID TASK, NO REVENUE.** This is original, reusable sample code created with entirely fictitious customer/product data. No buyer data, accounts, API keys, paid OCR/AI, hosting, emails or network calls are used. Do **not** submit, invoice or send the output as a real quotation.

**Background reference (not authorization):** Eng_Rami_Sebai's original n8n discussion, [Seeking estimates: n8n developer for a small RFQ-to-quote prototype](https://community.n8n.io/t/312281), posted September 10, 2026. The buyer requested estimates, a text-based RFQ PDF layout, extraction of product codes/descriptions/quantities/units, matching with an approved catalogue and price list, human review of uncertain matches, and Excel export. **No agreed fee, contract, buyer-supplied fixture, claim, legal payment arrangement or acceptance exists for this demo.** The code here is an **offline standalone core demonstration**, **not** an implemented/deployed n8n workflow and **not** a completed paid client project.

## Real files

| Path | Purpose |
| --- | --- |
| `pipeline.py` | Bounded Poppler text-PDF reader, strict layout parsing, exact-SKU + UOM + price matching, validation/hold status engine, command-line entry point |
| `xlsx_writer.py` | Local Python-stdlib ZIP/XML writer for a formatted Excel `.xlsx`; no spreadsheet API or internet required |
| `make_fixture.py` | Generates the reproducible **synthetic** RFQ text-PDF; requires ReportLab only to regenerate this included fixture |
| `samples/synthetic_rfq.pdf` | Actual text-layer demonstration RFQ (10 lines, completely fictional) |
| `samples/catalogue.csv` | Fictitious product-catalogue snapshot `CAT-DEMO-V1`, with physical CSV row references |
| `samples/approved_prices.csv` | Separate fictitious approved price snapshot `PR-DEMO-V1`, with ambiguous and withheld prices |
| `outputs/quote_demo.xlsx` | **Generated and tested** Excel draft: `Run Summary`, `Quote Draft`, `Review Queue` |
| `test_pipeline.py` | Offline regression coverage including input failures and workbook-integrity assertions |
| `run_demo.sh` | One-command run and test script |

## Offline prerequisites

- Python 3.10+ standard library for the **main** program and Excel workbook. It uses **no OpenAI API, other remote model, n8n server, spreadsheet service, or internet access**.
- `pdfinfo` and `pdftotext` executables from **Poppler** on the local `PATH` to read text-layer PDFs. This input parser deliberately does **not** support scans/OCR.
- Only if you want to *rebuild* the provided synthetic PDF, `reportlab` Python package is needed (`python3 make_fixture.py`). It is already present in the machine where this demo was built. You can run the main pipeline with the provided PDF without ReportLab.

## Re-run

```bash
# From the cos-money-agent repository root:
cd client-prep/rfq-quote-complete-demo-20261012
bash run_demo.sh
```

Equivalent separate commands, without any external transmission:

```bash
python3 pipeline.py \
  --rfq samples/synthetic_rfq.pdf \
  --catalogue samples/catalogue.csv \
  --prices samples/approved_prices.csv \
  --out outputs/quote_demo.xlsx
python3 -m unittest discover -s . -p 'test_*.py' -v
```

Expected verified synthetic result: **10 requested lines, 2 confirmed/priced, 8 held**. Only the 2 accepted lines contribute to the **USD 61.25 approved-lines subtotal** (`4 x 12.50 + 3 x 3.75`); **there is no complete quotation grand total** while 8 lines are unresolved. The output is a **DRAFT / DO NOT SEND**.

## Data contract and review safety

The *one deliberately supported* PDF layout contains exactly one `RFQ ID: ...` and `Currency: ...` header, then item rows like:

```text
LINE | CODE | DESCRIPTION | QTY | UOM
001 | BRK-20A | Miniature circuit breaker 20A | 4 | EA
```

Each numbered row is retained in exactly one quote decision. Malformed rows/duplicate row numbers/unsupported document layout fail rather than silently omitting products; an invalid document produces **no new XLSX**. Only one text-based layout, up to **5 pages/50 RFQ lines**, and **1,000 rows per catalogue/price CSV** are supported. Inputs are limited to 5 MB PDF and 2 MB per CSV. PDF text extraction uses a local subprocess without a shell and with timeouts. The reader does not extract arbitrary tables or interpret handwritten/scanned content.

Matching is **only by exact product code**, with all requested quantities as positive whole numbers. The only accepted units are `EA`, `M`, `BOX`, and `PK`. Unit/pack conversion, substitutions, fuzzy matching and description-based automatic assignments are **intentionally prohibited**. Only an active unique catalogue row, matching unit, and a unique `approved=yes` price in the **same currency** can be priced. Money arithmetic uses Decimal, prices are limited to two decimal places, and prices cannot be negative.

Held cases in the synthetic fixture: unknown SKU, wrong unit, no approved price row, duplicate catalogue SKU, multiple price-list rows, explicitly unapproved price, price currency mismatch, inactive SKU. Extra tests exercise repeated RFQ codes, invalid zero quantity and malformed rows. **Every hold remains unpriced; its source references and reason appear on the Review Queue.** Repeated SKU in different RFQ lines is treated as a potential duplicate and all instances are held until a person checks it.

Each workbook line has a persistent source reference: **RFQ line number**, `CAT-DEMO-V1:rowN`, and `PR-DEMO-V1:rowN` (physical CSV lines, starting at 2 after the header). The summary also records complete SHA-256 hashes of the input PDF and reference CSVs; after an input change the workbook is regenerated from the new snapshot. Input text is stored as Excel strings, not interpreted as a user-supplied formula. `Quote Draft` calculates line totals with formulas **only for approved rows**; `Review Queue` offers blank fields for manual reviewer decisions/notes, with **no auto-accept or repricing**.

## Optional self-hosted n8n starter

The `n8n-integration/` directory now includes an **inactive, manual-only starter workflow export** wrapping this synthetic demo. It has a fixed local shell execution step and a Code node that reports draft/review counts; it does not send a quote, require remote APIs, or install/deploy n8n. Import requires a suitably configured and authorized self-hosted n8n instance with Execute Command enabled. It was **not live-import tested**.

Its exported command and Code node were exercised locally in **4 additional deterministic offline integration tests**, alongside the existing **17 core tests**:

```sh
python3 n8n-integration/test_offline_integration.py -v
```

See [n8n integration instructions](n8n-integration/README.md). No customer data, paid assignment, contract or additional buyer contact is implied.

## Handover / outside-world boundary

This is a synthetic proof of local technical capabilities only. It does **not** prove compatibility with Rami's actual PDF, product catalogue or price file, or with a live n8n runtime; those formats/access have not been provided. A paid test requires separate original-buyer **written acceptance of exact scope, samples, price, timing and delivery channel**, and confirmation from the buyer **and** payment provider that a truthful **17-year-old Georgian performer** with a **different, independently owned adult Luara commercial G&S/Georgian bank beneficiary** is permitted. Only after an actual verified recipient-side completed payment could any campaign revenue be counted. **The prime agent must review the original buyer's current paid terms before anyone initiates first contact.**

No direct external sends, signup, buyer DMs, PRs or changes to campaign finances are part of this demo.
