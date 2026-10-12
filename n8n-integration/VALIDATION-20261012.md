# Offline validation of self-hosted n8n RFQ starter (October 12, 2026)

This is a **synthetic-data-only proof of concept**. It is not a deployed n8n instance, accepted client deliverable, invoice, payable claim, or incoming payment. The underlying source code is stored in the **parent directory**.

From the repository root:

```sh
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 n8n-integration/test_offline_integration.py -v
python3 -m json.tool n8n-integration/workflow.json >/dev/null
```

Independently repeated on the original Linux workspace **after moving into this repository**:

- Core PDF->catalogue->approved price->XLSX: **17 tests passed**.
- n8n export graph and exact shell/Code node offline execution: **4 tests passed**.
- Exported JSON parses. The workflow has only inactive Manual Trigger -> Execute Command -> Code nodes; no webhook, schedule, external credentials, email or sending.
- Real synthetic example: 10 lines; two priced; eight held for human review; fictional approved-lines subtotal USD61.25. A complete quotation is **not** computed while holds exist.
- Testing includes an unset mount environment variable and rejection of an inconsistent report.

No n8n server/import was available; **live compatibility is not claimed**. Use only an explicitly configured and administrator-authorized *self-hosted* instance with the command node enabled and Python/Poppler accessible. Do not mistake the synthetic quote for a real customer quote.

Original buyer Eng_Rami_Sebai already received **one public demonstration link**, forum post [#394](https://community.n8n.io/t/312281/394), after which all further contact is forbidden. This companion is an in-place improvement to the user's own repository **without any additional buyer message**; buyer did not commission or accept paid work. New verified income: USD0. Historical verified income: USD120.
