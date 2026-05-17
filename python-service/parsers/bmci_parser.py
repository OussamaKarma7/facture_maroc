"""
Parser BMCI Bank (BNP Paribas Maroc).
BMCI utilise souvent des formats avec code opération.
"""

import re, cv2, numpy as np
from datetime import datetime
from .base_parser import BaseBankParser
from utils.common import (
    norm, clean_amount, clean_date, clean_date_parts,
    classify_operation, looks_credit, clean_nature_text, AMOUNT_RE
)


class BMCIParser(BaseBankParser):
    BANK_NAME = "BMCI"
    BANK_CODE = "007"

    def parse_header(self, text: str) -> dict:
        out = {
            "banque": {"nom": "BMCI"},
            "titulaire": {},
            "releve": {},
        }
        lines = [norm(x) for x in text.splitlines() if norm(x)]

        # Agency
        m = re.search(r"(?:AGENCE|AG)\s*[:;]?\s*([A-Z0-9\-' .]+)", text, re.I)
        if m:
            ag = norm(re.split(r"COMPTE|DEVISE|RELEVE|\n", m.group(1), flags=re.I)[0])
            out["banque"]["nom_agence"] = ag

        # Titulaire
        for line in lines:
            up = line.upper()
            if re.search(r"\b(SARL|SA|S\.A\.R\.L|S\.A\b|SOCIETE)\b", up):
                if not any(bad in up for bad in ["BANQUE", "BMCI", "AGENCE",
                                                  "COMPTE", "DEVISE", "RELEVE"]):
                    out["titulaire"]["raison_sociale"] = line.strip()
                    break

        # Date arrete
        for pat in [
            r"SOLDE\s+FINAL\s+AU\s+(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4})",
            r"ARRETE\s+AU\s+(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4})",
        ]:
            m = re.search(pat, text, re.I)
            if m:
                out["releve"]["date_arrete"] = clean_date(m.group(1))
                break

        out["releve"]["type_document"] = "RELEVE DE COMPTE"

        if out["titulaire"].get("raison_sociale"):
            up = out["titulaire"]["raison_sociale"].upper()
            out["titulaire"]["type"] = (
                "SARL" if "SARL" in up else
                "SA" if re.search(r"\bSA\b", up) else ""
            )
        return out

    def extract_rib(self, text_or_img) -> dict:
        if isinstance(text_or_img, np.ndarray):
            h, w = text_or_img.shape[:2]
            zone = text_or_img[int(h*0.25):int(h*0.45), :]
            text = self.ocr_string(zone, psm="6", whitelist="0123456789 ")
        else:
            text = text_or_img

        t = norm(text).replace("O", "0")

        # BMCI uses various RIB formats
        # Try 007 first (same as Attijari)
        m = re.search(r"\b(007)\s+(\d{3})\s+(\d{16,20})\s+(\d{2})\b", t)
        if m:
            return {
                "code_banque": m.group(1),
                "code_localite": m.group(2),
                "numero_principal": m.group(3),
                "cle_rib": m.group(4),
                "rib_complet": m.group(1) + m.group(2) + m.group(3) + m.group(4),
            }

        # Generic 20+ digit sequence starting with known bank code
        m = re.search(r"\b(0\d{2})\s+(\d{3})\s+(\d{16,20})\s+(\d{2})\b", t)
        if m:
            return {
                "code_banque": m.group(1),
                "code_localite": m.group(2),
                "numero_principal": m.group(3),
                "cle_rib": m.group(4),
                "rib_complet": m.group(1) + m.group(2) + m.group(3) + m.group(4),
            }
        return {}

    def extract_soldes(self, text: str) -> dict:
        from utils.common import extract_soldes
        return extract_soldes(text, "bmci")

    def _line_to_tx(self, line: str, year: int) -> dict:
        """Parse BMCI transaction line.
        Format: CODE DD MM nature ... DD MM YYYY montant
        """
        raw = norm(line).replace("@", "0").replace("O", "0")

        # Pattern with code: XXXXXX DD MM rest
        m = re.match(
            r"^(?P<code>[A-Z0-9]{4,8})\s+(?P<d1>\d{2})\s+(?P<m1>\d{2})\s+(?P<rest>.+)$",
            raw, re.I,
        )
        if not m:
            # Without code: DD/MM rest
            m = re.match(
                r"^(?P<d1>\d{2})/(?P<m1>\d{2})\s+(?P<rest>.+)$",
                raw,
            )
            if m:
                gd = m.groupdict()
                rest = norm(gd["rest"])
                d1, m1 = gd["d1"], gd["m1"]

                # Find amount
                amounts = AMOUNT_RE.findall(rest)
                amount = clean_amount(amounts[-1]) if amounts else None
                nature = rest
                ref = ""
                if amounts:
                    nature = norm(rest[:rest.rfind(amounts[-1])])

                debit = credit = None
                if amount is not None:
                    if looks_credit(nature):
                        credit = amount
                    else:
                        debit = amount

                return {
                    "ligne": None,
                    "date_operation": clean_date_parts(d1, m1, str(year)),
                    "date_valeur": clean_date_parts(d1, m1, str(year)),
                    "reference": ref,
                    "nature_operation": clean_nature_text(nature),
                    "type_operation": clean_nature_text(nature),
                    "operation_categorie": classify_operation(nature),
                    "montant_debit": debit,
                    "montant_credit": credit,
                }
            return None

        gd = m.groupdict()
        code = gd.get("code", "").upper()
        d1, m1 = gd["d1"], gd["m1"]
        rest = norm(gd["rest"])

        # Find value date and amount at end
        date_matches = list(re.finditer(r"(\d{2})\s+(\d{2})\s+(20\d{2})", rest))
        if date_matches:
            dm = date_matches[-1]
            d2, m2, y2 = dm.group(1), dm.group(2), dm.group(3)
            nature_part = rest[:dm.start()]
            tail = norm(rest[dm.end():])
        else:
            d2, m2, y2 = d1, m1, str(year)
            nature_part = rest
            tail = rest

        amounts = AMOUNT_RE.findall(tail)
        if not amounts:
            amounts = AMOUNT_RE.findall(rest)
            nature_part = rest

        amount = clean_amount(amounts[-1]) if amounts else None
        nature = nature_part
        if amounts and amounts[-1] in nature_part:
            nature = norm(nature_part.replace(amounts[-1], "", 1))

        debit = credit = None
        if amount is not None:
            if looks_credit(nature):
                credit = amount
            else:
                debit = amount

        return {
            "ligne": None,
            "date_operation": clean_date_parts(d1, m1, str(year)),
            "date_valeur": clean_date_parts(d2, m2, y2),
            "reference": code,
            "nature_operation": clean_nature_text(nature),
            "type_operation": clean_nature_text(nature),
            "operation_categorie": classify_operation(nature),
            "montant_debit": debit,
            "montant_credit": credit,
        }

    def extract_transactions(self, page_img, **kwargs) -> list:
        h, w = page_img.shape[:2]
        crop = page_img[int(h*0.35):int(h*0.85), int(w*0.02):int(w*0.98)]
        raw = self.ocr_string(crop, psm="6")
        year = kwargs.get("default_year", datetime.now().year)

        txs = []
        for line in [norm(x) for x in raw.splitlines() if norm(x)]:
            if re.search(r"DATE|VALEUR|REFERENCE|NATURE|MONTANT|RELEVE|TOTAL|SOLDE",
                        line, re.I):
                continue
            tx = self._line_to_tx(line, year)
            if tx:
                tx["ligne"] = len(txs) + 1
                txs.append(tx)
        return txs
