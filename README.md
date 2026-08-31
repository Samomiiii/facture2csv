# facture2csv

Extrait automatiquement les données clés de tes factures PDF (fournisseur, numéro, date, montants HT/TVA/TTC) et les exporte dans un fichier CSV ou Excel prêt à importer dans ta compta.

Fini la ressaisie manuelle facture par facture.

## Exemple

```bash
python facture2csv.py factures/*.pdf -o resultat.csv
```

**Entrée** : un dossier de PDF de factures
**Sortie** (`resultat.csv`) :

| fichier | fournisseur | numero_facture | date | montant_ht | montant_tva | montant_ttc |
|---|---|---|---|---|---|---|
| facture_01.pdf | ACME Fournitures SARL | FA-2026-0456 | 15/08/2026 | 850.0 | 170.0 | 1020.0 |
| facture_02.pdf | Studio Design Co | INV-2026-0089 | 20/08/2026 | 300.0 | 60.0 | 360.0 |

## Installation

```bash
pip install pdfplumber pandas openpyxl
```

(`openpyxl` n'est nécessaire que si tu veux exporter en `.xlsx`.)

## Utilisation

```bash
# Un seul fichier
python facture2csv.py facture.pdf

# Un dossier entier
python facture2csv.py factures/ -o resultat.csv

# Pattern glob
python facture2csv.py factures/*.pdf -o resultat.csv

# Export Excel au lieu de CSV
python facture2csv.py factures/ -o resultat.xlsx

# Mode verbeux (affiche chaque facture traitée)
python facture2csv.py factures/ --verbose
```

## Comment ça marche

Le script utilise `pdfplumber` pour extraire le texte brut de chaque PDF, puis des expressions régulières pour repérer :
- le **fournisseur** (heuristique : première ligne pertinente en haut du document)
- le **numéro de facture** (mots-clés : "Facture n°", "Invoice", "Référence"...)
- la **date** (formats JJ/MM/AAAA et texte français)
- les **montants HT / TVA / TTC** (mots-clés : "Total HT", "Total TTC", "Net à payer"...)

Les factures scannées en image (sans texte sélectionnable) ne sont pas supportées pour l'instant — voir la section Limites.

## Limites connues

- Fonctionne sur des PDF avec texte sélectionnable (pas des scans image bruts).
- Les regex couvrent les formats de factures français les plus courants — un format inhabituel peut nécessiter d'ajuster les patterns dans `facture2csv.py`.
- Un seul fournisseur/numéro/montant par facture est extrait (pas de factures multi-pages avec plusieurs sous-totaux).

## Contribuer

Les PR sont bienvenues, en particulier :
- nouveaux patterns regex pour des formats de facture non reconnus
- support de l'OCR pour les PDF scannés (ex: via `pytesseract`)
- détection de la devise (actuellement suppose l'euro)

Ouvre une issue avec un exemple de facture (anonymisée) si un format n'est pas bien détecté.

## Licence

MIT
