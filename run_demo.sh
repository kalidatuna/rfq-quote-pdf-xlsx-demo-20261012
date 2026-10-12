#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 pipeline.py \
  --rfq samples/synthetic_rfq.pdf \
  --catalogue samples/catalogue.csv \
  --prices samples/approved_prices.csv \
  --out outputs/quote_demo.xlsx
python3 -m unittest discover -s . -p 'test_*.py' -v
