#!/usr/bin/env python3
"""
facture2csv — Extracts key data from PDF invoices and exports it to CSV/Excel.

Usage:
    python facture2csv.py invoices/*.pdf -o result.csv
    python facture2csv.py invoices/*.pdf -o result.xlsx
    python facture2csv.py one_invoice.pdf --verbose
"""

import argparse
import glob
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

# ---------------------------------------------------------------------------
# Recognition patterns (regex) — cover the most common French invoice
# formats. Built to be easily extended: add your own regex here if a format
# isn't detected well.
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    r"\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b",
    r"\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|"
    r"septembre|octobre|novembre|décembre)\s+\d{4})\b",
]

INVOICE_NUMBER_PATTERNS = [
    r"(?:facture|invoice|n°\s*facture|n°\s*fact\.?)\s*[:n°#]*\s*([A-Z0-9\-/]{3,20})",
    r"(?:référence|ref\.?)\s*[:]*\s*([A-Z0-9\-/]{3,20})",
]

TOTAL_TTC_PATTERNS = [
    r"(?:total\s*ttc|montant\s*ttc|net\s*à\s*payer|total\s*à\s*payer)\s*[:]*\s*"
    r"([\d\s]+[.,]\d{2})\s*€?",
]

TOTAL_HT_PATTERNS = [
    r"(?:total\s*ht|montant\s*ht|sous-total)\s*[:]*\s*([\d\s]+[.,]\d{2})\s*€?",
]

TVA_PATTERNS = [
    r"(?:tva|montant\s*tva)\s*[:]*\s*([\d\s]+[.,]\d{2})\s*€?",
]

# The supplier is often the first "solid" line of the document (company name
# at the top of the page). Simple heuristic: first non-empty line that looks
# neither like a date nor a generic keyword.
SKIP_WORDS = ("facture", "invoice", "devis", "page", "date", "n°")


def _search_first(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1).strip()
    return None


def _clean_amount(raw):
    if not raw:
        return None
    cleaned = raw.replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def guess_fournisseur(lines):
    for line in lines[:8]:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(word in lower for word in SKIP_WORDS):
            continue
        if re.search(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", stripped):
            continue
        if len(stripped) < 3:
            continue
        return stripped
    return None


def extract_from_pdf(path):
    """Extracts the key fields from a PDF invoice. Returns a dict."""
    with pdfplumber.open(path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    lines = full_text.splitlines()

    data = {
        "fichier": Path(path).name,
        "fournisseur": guess_fournisseur(lines),
        "numero_facture": _search_first(INVOICE_NUMBER_PATTERNS, full_text),
        "date": _search_first(DATE_PATTERNS, full_text),
        "montant_ht": _clean_amount(_search_first(TOTAL_HT_PATTERNS, full_text)),
        "montant_tva": _clean_amount(_search_first(TVA_PATTERNS, full_text)),
        "montant_ttc": _clean_amount(_search_first(TOTAL_TTC_PATTERNS, full_text)),
    }
    return data


def resolve_input_paths(patterns):
    """Expands glob patterns and folders into a list of PDF files."""
    paths = []
    for pattern in patterns:
        p = Path(pattern)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.pdf")))
        else:
            expanded = glob.glob(pattern)
            paths.extend(Path(x) for x in sorted(expanded))
    # deduplicate while preserving order
    seen = set()
    unique = []
    for p in paths:
        if p not in seen and p.suffix.lower() == ".pdf":
            seen.add(p)
            unique.append(p)
    return unique


def main():
    parser = argparse.ArgumentParser(
        description="Extracts data from PDF invoices to a CSV or Excel file."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="PDF file(s), folder, or glob pattern (e.g. invoices/*.pdf)",
    )
    parser.add_argument(
        "-o", "--output",
        default="result.csv",
        help="Output file (.csv or .xlsx). Default: result.csv",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print details of each processed invoice to the terminal.",
    )
    args = parser.parse_args()

    pdf_paths = resolve_input_paths(args.inputs)

    if not pdf_paths:
        print("No PDF file found for these arguments.", file=sys.stderr)
        sys.exit(1)

    rows = []
    errors = []

    for path in pdf_paths:
        try:
            row = extract_from_pdf(path)
            rows.append(row)
            if args.verbose:
                print(f"✓ {path.name} → {row}")
        except Exception as exc:  # noqa: BLE001 — keep going on error
            errors.append((path.name, str(exc)))
            print(f"✗ Error on {path.name}: {exc}", file=sys.stderr)

    if not rows:
        print("No invoice could be processed.", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(rows)

    output_path = Path(args.output)
    if output_path.suffix.lower() == ".xlsx":
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\n{len(rows)} invoice(s) processed → {output_path}")
    if errors:
        print(f"{len(errors)} file(s) failed (see above).")

    # Small useful summary
    n_missing_ttc = df["montant_ttc"].isna().sum()
    if n_missing_ttc:
        print(
            f"⚠ Total (TTC) amount not detected on {n_missing_ttc} invoice(s) "
            "— check manually or add a matching regex pattern."
        )


if __name__ == "__main__":
    main()
