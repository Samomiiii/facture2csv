Automatically extracts key data from your PDF invoices (supplier, invoice number, date, HT/VAT/TTC amounts) and exports them to a CSV or Excel file ready to import into your accounting software.

No more manual re-entry invoice by invoice.

## Example

```bash
python facture2csv.py factures/*.pdf -o resultat.csv
```

**Input**: a folder of invoice PDFs
**Output** (`resultat.csv`):

| fichier | fournisseur | numero_facture | date | montant_ht | montant_tva | montant_ttc |
|---|---|---|---|---|---|---|
| facture_01.pdf | ACME Fournitures SARL | FA-2026-0456 | 15/08/2026 | 850.0 | 170.0 | 1020.0 |
| facture_02.pdf | Studio Design Co | INV-2026-0089 | 20/08/2026 | 300.0 | 60.0 | 360.0 |

## Installation

```bash
pip install pdfplumber pandas openpyxl
```

(`openpyxl` is only needed if you want to export to `.xlsx`.)

## Usage

```bash
# A single file
python facture2csv.py facture.pdf

# An entire folder
python facture2csv.py factures/ -o resultat.csv

# Glob pattern
python facture2csv.py factures/*.pdf -o resultat.csv

# Export to Excel instead of CSV
python facture2csv.py factures/ -o resultat.xlsx

# Verbose mode (shows each invoice processed)
python facture2csv.py factures/ --verbose
```

## How it works

The script uses `pdfplumber` to extract raw text from each PDF, then regular expressions to identify:
- the **supplier** (heuristic: first relevant line at the top of the document)
- the **invoice number** (keywords: "Facture n°", "Invoice", "Référence"...)
- the **date** (DD/MM/YYYY formats and French text)
- the **HT / VAT / TTC amounts** (keywords: "Total HT", "Total TTC", "Net à payer"...)

Scanned image invoices (without selectable text) are not currently supported — see the Limitations section.

## Known limitations

- Works on PDFs with selectable text (not raw image scans).
- The regex patterns cover the most common French invoice formats — an unusual format may require adjusting the patterns in `facture2csv.py`.
- Only one supplier/number/amount is extracted per invoice (no multi-page invoices with several subtotals).

## Contributing

PRs are welcome, especially for:
- new regex patterns for unrecognized invoice formats
- OCR support for scanned PDFs (e.g. via `pytesseract`)
- currency detection (currently assumes euros)

Open an issue with an example invoice (anonymized) if a format isn't detected well.

## License

MIT
