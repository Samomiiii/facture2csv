#!/usr/bin/env python3
"""
facture2csv — Extrait les données clés de factures PDF et les exporte en CSV/Excel.

Usage:
    python facture2csv.py factures/*.pdf -o resultat.csv
    python facture2csv.py factures/*.pdf -o resultat.xlsx
    python facture2csv.py une_facture.pdf --verbose
"""

import argparse
import glob
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

# ---------------------------------------------------------------------------
# Patterns de reconnaissance (regex) — couvrent les formats de factures FR les
# plus courants. Fait pour être étendu facilement : ajoute tes propres regex
# ici si un format n'est pas bien détecté.
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

# Le fournisseur est souvent la première ligne "solide" du document
# (nom d'entreprise en haut de page). Heuristique simple : première ligne
# non vide qui ne ressemble ni à une date ni à un mot-clé générique.
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
    """Extrait les champs clés d'une facture PDF. Retourne un dict."""
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
    """Étend les patterns glob et dossiers en une liste de fichiers PDF."""
    paths = []
    for pattern in patterns:
        p = Path(pattern)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.pdf")))
        else:
            expanded = glob.glob(pattern)
            paths.extend(Path(x) for x in sorted(expanded))
    # dédoublonnage en conservant l'ordre
    seen = set()
    unique = []
    for p in paths:
        if p not in seen and p.suffix.lower() == ".pdf":
            seen.add(p)
            unique.append(p)
    return unique


def main():
    parser = argparse.ArgumentParser(
        description="Extrait les données de factures PDF vers un CSV ou Excel."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Fichier(s) PDF, dossier, ou pattern glob (ex: factures/*.pdf)",
    )
    parser.add_argument(
        "-o", "--output",
        default="resultat.csv",
        help="Fichier de sortie (.csv ou .xlsx). Défaut : resultat.csv",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Affiche le détail de chaque facture traitée dans le terminal.",
    )
    args = parser.parse_args()

    pdf_paths = resolve_input_paths(args.inputs)

    if not pdf_paths:
        print("Aucun fichier PDF trouvé pour ces arguments.", file=sys.stderr)
        sys.exit(1)

    rows = []
    errors = []

    for path in pdf_paths:
        try:
            row = extract_from_pdf(path)
            rows.append(row)
            if args.verbose:
                print(f"✓ {path.name} → {row}")
        except Exception as exc:  # noqa: BLE001 — on veut continuer sur erreur
            errors.append((path.name, str(exc)))
            print(f"✗ Erreur sur {path.name} : {exc}", file=sys.stderr)

    if not rows:
        print("Aucune facture n'a pu être traitée.", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(rows)

    output_path = Path(args.output)
    if output_path.suffix.lower() == ".xlsx":
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\n{len(rows)} facture(s) traitée(s) → {output_path}")
    if errors:
        print(f"{len(errors)} fichier(s) en erreur (voir ci-dessus).")

    # Petit résumé utile
    n_missing_ttc = df["montant_ttc"].isna().sum()
    if n_missing_ttc:
        print(
            f"⚠ Montant TTC non détecté sur {n_missing_ttc} facture(s) "
            "— vérifie manuellement ou ajoute un pattern regex adapté."
        )


if __name__ == "__main__":
    main()
