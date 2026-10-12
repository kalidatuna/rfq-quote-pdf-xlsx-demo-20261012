# Self-hosted n8n RFQ starter, synthetic files only

**LOCAL DEMONSTRATION. No contracted work, customer data, authorized quote, external submission, payment or receivable.** This companion wraps the existing offline Python implementation in the parent folder without altering its Python implementation. It has one manual trigger, one local shell command and one Code node to present the review summary. It contains no webhook, schedule, email, credentials, AI API, or automatic customer delivery.

## Import and execute on a self-hosted instance

1. Install Python 3.10+, Poppler `pdfinfo` and `pdftotext` in the same host/container that runs n8n's **Execute Command** node. This node must be enabled by the self-hosted administrator. It is not available on n8n Cloud and may be disabled in recent self-hosted versions. This demonstration does not adjust server security settings.
2. Mount or copy the entire `rfq-quote-complete-demo-20261012` folder to a writable path accessible to the n8n process. Set the n8n process/container environment variable `RFQ_DEMO_HOME` to that absolute path. For example, if the demo is available **inside** the container at `/data/rfq-demo`, set `RFQ_DEMO_HOME=/data/rfq-demo`. Ensure `outputs/` is writable by the n8n user. Relative paths in the workflow resolve from this variable.
3. Import `workflow.json` using n8n's **Import from File** action. Leave it inactive. Click **Execute Workflow** manually. The workflow runs the demo's fixed, synthetic fixture and generates `outputs/quote_n8n_demo.xlsx` under the mounted folder. It displays the counts and review status; it does **not** attach, upload or send the workbook.

Expected Code node output:

```json
{"status":"DRAFT / DO NOT SEND","rows":10,"priced":2,"review":8,"approvedLinesSubtotalUSD":"61.25","outputRelativePath":"outputs/quote_n8n_demo.xlsx","requiresHumanReview":true}
```

This is only an **approved-lines subtotal**. Eight unresolved lines make a final quotation total unavailable. The draft workbook has `Run Summary`, `Quote Draft` and `Review Queue` sheets. File path `outputs/quote_n8n_demo.xlsx` is local to the n8n runtime and its mounted volume, not a hosted download link. Repeated manual runs replace this one synthetic demo output.

## Offline verification without n8n

```sh
python3 test_offline_integration.py -v
```

Requires a local Node.js binary for the exported Code node. The test executes the **exact shell command stored in the workflow**, with an environment variable pointing to a fresh temporary copy of the synthetic files, then executes the **exact Code node source** in local Node.js. It also checks import wiring, missing mount configuration and invalid summary rejection. The original Python suite was run independently. Running n8n itself was unavailable in this workspace, so live import compatibility and runtime behavior remain unverified.

The buyer's original reference [n8n RFQ estimate discussion](https://community.n8n.io/t/312281) does not establish a paid assignment, valid customer dataset, permission to submit this work, or a lawful payment route. No contact or upload is authorized by this file.
