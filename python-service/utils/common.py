"""
Utilitaires communs pour le parsing des relevés bancaires marocains.
Adapté du code original — version générique multi-banques.
"""

import re, os, sys, json
from pathlib import Path
from datetime import datetime

# ─── Regex montant ───
AMOUNT_RE = re.compile(
    r"\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2}|\d+[,.]\s*\d{2}|\d{1,3}(?:[\s.]?\d{3})*[,.](?!\d)|\d+[,.](?!\d)"
)


def norm(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    s = s.replace("|", " ").replace("[", " ").replace("]", " ")
    s = s.replace("{", " ").replace("}", " ").replace("!", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def clean_amount(s: str):
    if not s:
        return None
    s = str(s).strip().replace("\xa0", " ")
    s = s.replace("O", "0").replace("o", "0").replace("@", "0")
    s = re.sub(r"[^\d,.\s]", "", s)
    s = re.sub(r"\s+", "", s)
    if not s:
        return None
    if s.endswith(",") or s.endswith("."):
        s += "00"
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except Exception:
        return None


def clean_date_parts(d, m, y):
    try:
        d = str(d).replace("O", "0").replace("o", "0")
        m = str(m).replace("O", "0").replace("o", "0")
        y = str(y).replace("O", "0").replace("o", "0")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:
        return None


def clean_date(s: str):
    if not s:
        return None
    s = str(s).replace("O", "0").replace("o", "0")
    m = re.search(r"(\d{1,2})[ /\-]+(\d{1,2})[ /\-]+(\d{4})", s)
    if m:
        return clean_date_parts(*m.groups())
    return None


def classify_operation(nature: str) -> str:
    n = (nature or "").upper()
    if "RECU" in n or "REÇU" in n or "REMISE" in n or "VERSEMENT" in n:
        return "CREDIT"
    if "VIR" in n and ("EMIS" in n or "AG EMIS" in n):
        return "VIR_EMIS"
    if "RETRAIT" in n:
        return "RETRAIT"
    if "PAIEMENT" in n or "PRELEVEMENT" in n:
        return "PAIEMENT_PRELEVEMENT"
    if "COMMISSION" in n or "FRAIS" in n:
        return "FRAIS_COMMISSIONS"
    if "TAXE" in n or "TVA" in n:
        return "TAXE"
    return "AUTRE"


def looks_credit(nature: str) -> bool:
    n = (nature or "").upper()
    return any(k in n for k in [
        "RECU", "REÇU", "REMISE", "VERSEMENT RECU",
        "VIR.WEB RECU", "VIR INST RECU", "VIREMENT RECU"
    ])


def clean_nature_text(text: str) -> str:
    if not text:
        return ""
    t = norm(text).upper()
    replacements = {
        "C0MMISSI0N": "COMMISSION", "C0MMISSION": "COMMISSION",
        "COMMISSI0N": "COMMISSION", "C0M ": "COM ", " C0M": " COM",
        "S0CIETE": "SOCIETE", "S0C1ETE": "SOCIETE",
        "D0CUMENT": "DOCUMENT", "C0MPTE": "COMPTE",
        "AMR0UCHE": "AMROUCHE", "0RDINAIRE": "ORDINAIRE",
        "M0NETIQUE": "MONETIQUE", "CHE0UE": "CHEQUE",
        "CHE0UES": "CHEQUES", "ESPECES": "ESPECES",
    }
    for a, b in replacements.items():
        t = t.replace(a, b)
    t = re.sub(r"(?<=[A-Z])0(?=[A-Z])", "O", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ─── RIB helpers ───
def extract_rib_generic(text: str, bank_code: str = None) -> dict:
    """Extract RIB using known Moroccan bank codes."""
    t = norm(text).replace("O", "0").replace("E", "5")
    rib_patterns = {
        "007": r"\b(007)\s+(\d{3})\s+((?:\d\s*){16})\s+(\d{2})\b",  # Attijari
        "190": r"\b(190)\s+(\d{3})\s+(\d{5})\s+(\d{6,8})\s+(\d{3})\s+(\d)\b",  # BP
        "230": r"\b(230)\s+(\d{3})\s+(\d{16,24})\s+(\d{2})\b",  # CIH
        "011": r"\b(011)\s+(\d{3})\s+(\d{16,24})\s+(\d{2})\b",  # BMCE
        "007810": r"\b(007)\s+(810)\s+(\d{16,24})\s+(\d{2})\b",  # Attijari v2
    }

    result = {"code_banque": None, "code_localite": None,
              "numero_principal": None, "cle_rib": None, "rib_complet": None}

    # Try specific patterns first
    for code, pattern in rib_patterns.items():
        if bank_code and code != bank_code and not bank_code.startswith(code):
            continue
        m = re.search(pattern, t)
        if m:
            groups = m.groups()
            if len(groups) == 4:
                result["code_banque"] = groups[0]
                result["code_localite"] = groups[1]
                principal = re.sub(r"\D+", "", groups[2])
                result["numero_principal"] = principal
                result["cle_rib"] = groups[3]
                result["rib_complet"] = groups[0] + groups[1] + principal + groups[3]
                return result
            elif len(groups) == 5:
                result["code_banque"] = groups[0]
                result["code_localite"] = groups[1]
                principal = "".join(groups[2:-1])
                result["numero_principal"] = principal
                result["cle_rib"] = groups[-1]
                result["rib_complet"] = groups[0] + groups[1] + principal + groups[-1]
                return result

    # Generic fallback: look for 20+ digit sequences
    all_nums = re.findall(r"\d+", t)
    for i, n in enumerate(all_nums):
        if len(n) >= 20:
            # Could be a concatenated RIB
            cb = n[:3]
            cl = n[3:6]
            cp = n[6:-2]
            cle = n[-2:]
            if cb in ("007", "190", "230", "011"):
                result["code_banque"] = cb
                result["code_localite"] = cl
                result["numero_principal"] = cp
                result["cle_rib"] = cle
                result["rib_complet"] = n
                return result

    return result


def detect_bank_from_text(text: str) -> str:
    """Detect which Moroccan bank based on header text."""
    up = text.upper()
    scores = {
        "ATTIJARIWAFA BANK": 0, "BANQUE POPULAIRE": 0,
        "CIH": 0, "BMCE": 0, "BMCI": 0,
    }

    if "ATTIJARI" in up or "ATTIJARIWAFA" in up or "WAFABANK" in up:
        scores["ATTIJARIWAFA BANK"] += 5
    if "BANQUE POPULAIRE" in up or "BP ":
        scores["BANQUE POPULAIRE"] += 5
    if "CIH" in up or "CREDIT IMMOBILIER" in up:
        scores["CIH"] += 5
    if "BMCE" in up or "BANK OF AFRICA" in up:
        scores["BMCE"] += 5
    if "BMCI" in up:
        scores["BMCI"] += 5

    # RIB codes as hints
    if " 007 " in up:
        scores["ATTIJARIWAFA BANK"] += 3
    if " 190 " in up:
        scores["BANQUE POPULAIRE"] += 3
    if " 230 " in up:
        scores["CIH"] += 3
    if " 011 " in up:
        scores["BMCE"] += 3

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return "INCONNUE"


# ─── Transaction helpers ───
def find_amounts_in_text(text: str):
    """Find all monetary amounts in text."""
    return AMOUNT_RE.findall(text)


def determine_transaction_sign(nature: str, amount: float = None) -> tuple:
    """Determine if a transaction is debit or credit."""
    is_credit = looks_credit(nature)
    if amount is not None:
        if is_credit:
            return None, amount
        else:
            return amount, None
    return None, None


# ─── Balance extraction ───
def extract_soldes(text: str, bank_type: str = None) -> dict:
    """Extract opening/closing balances from text."""
    s = {}
    t = norm(text)

    # Generic patterns for Moroccan bank statements
    patterns = {
        "ancien_solde": [
            r"ANCIEN\s+SOLDE\s+AU\s*[:.]?\s*(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4}).{0,80}?(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
            r"SOLDE\s+DEPART\s+AU\s*[:.]?\s*(\d{1,2}\s+\d{1,2}\s+\d{4}).{0,80}?(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
            r"SOLDE\s+DEPART\s+AU\s*[:.]?\s*(\d{1,2}/\d{1,2}/\d{4}).{0,80}?(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
            r"SOLDE\s+REPORT\s*[:.]?\s*(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
        ],
        "solde_reporter": [
            r"SOLDE\s+A\s+REPORTER\s*[:.]?\s*(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
            r"SOLDE\s+FINAL\s+AU\s*[:.]?\s*\d{1,2}\s+\d{1,2}\s+\d{4}\s+(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
            r"SOLDE\s+FINAL\s+AU\s*[:.]?\s*\d{1,2}/\d{1,2}/\d{4}\s+(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
            r"NOUVEAU\s+SOLDE\s+AU\s*[:.]?\s*\d{1,2}/\d{1,2}/\d{4}\s+(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
        ],
        "total_mouvements": [
            r"TOTAL\s+MOUVEMENTS\s+(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})\s+(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
            r"TOTAL\s+DES\s+MOUVEMENTS\s+(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})\s+(\d{1,3}(?:[\s.]?\d{3})*[,.]\s*\d{2})",
        ],
    }

    for pat in patterns["ancien_solde"]:
        m = re.search(pat, t, re.I)
        if m:
            s["ancien_solde_date"] = clean_date(m.group(1))
            s["ancien_solde_montant"] = clean_amount(m.group(2))
            break

    for pat in patterns["solde_reporter"]:
        m = re.search(pat, t, re.I)
        if m:
            s["solde_reporter"] = clean_amount(m.group(1))
            break

    for pat in patterns["total_mouvements"]:
        m = re.search(pat, t, re.I)
        if m:
            s["total_debits_banque"] = clean_amount(m.group(1))
            s["total_credits_banque"] = clean_amount(m.group(2))
            break

    return s


# ─── Header extraction ───
def extract_header_generic(text: str, bank_name: str) -> dict:
    """Generic header extraction — tries to find company name, agency, etc."""
    out = {
        "banque": {"nom": bank_name},
        "titulaire": {},
        "releve": {},
    }
    lines = [norm(x) for x in text.splitlines() if norm(x)]

    # Agency name
    m = re.search(r"(?:AGENCE|AG)\s*[:;]?\s*([A-Z0-9\-' .]+)", text, re.I)
    if m:
        ag = norm(re.split(r"COMPTE|DEVISE|RELEVE|\n", m.group(1), flags=re.I)[0])
        ag = re.sub(r"^(SUCC\.?\s*)", "", ag, flags=re.I).strip()
        out["banque"]["nom_agence"] = ag

    # Company type patterns
    company_patterns = [
        r"\b(SARL\s+AU|SARLAU|SARL|SA)\b",
        r"\b(SOCIETE\s+[A-Z\s]+SARL|SOCIETE\s+[A-Z\s]+SA)\b",
    ]

    for i, line in enumerate(lines):
        up = line.upper()
        for pat in company_patterns:
            m = re.search(pat, up, re.I)
            if m:
                out["titulaire"]["raison_sociale"] = line.strip()
                type_match = re.search(r"\b(SARL\s+AU|SARLAU|SARL|SA)\b", up)
                if type_match:
                    t = type_match.group(1)
                    out["titulaire"]["type"] = "SARL AU" if "SARL AU" in t else (
                        "SARLAU" if "SARLAU" in t else (
                            "SARL" if "SARL" in t else "SA" if t == "SA" else ""
                        )
                    )
                break
        if out["titulaire"].get("raison_sociale"):
            break

    # Date arrete
    m = re.search(r"(?:AU|ARRETE\s+AU)\s+(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4})", text, re.I)
    if m:
        out["releve"]["date_arrete"] = clean_date(m.group(1))

    out["releve"]["type_document"] = (
        "EXTRAIT DE COMPTE" if re.search(r"EXTRAIT\s+DE\s+COMPTE", text, re.I)
        else "RELEVE DE COMPTE"
    )

    return out
