"""
Parser BMCE Bank (Bank of Africa).
BMCE utilise souvent des formats similaires à BP/Attijari.
Code banque: 011
"""

import re, cv2, numpy as np
from datetime import datetime
from .base_parser import BaseBankParser
from utils.common import (
    norm, clean_amount, clean_date, clean_date_parts,
    classify_operation, looks_credit, clean_nature_text, AMOUNT_RE
)


class BMCEParser(BaseBankParser):
    BANK_NAME = "BMCE Bank"
    BANK_CODE = "011"

    def parse_header(self, text: str) -> dict:
        out = {
            "banque": {"nom": "BMCE Bank"},
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
                if not any(bad in up for bad in ["BANQUE", "BMCE", "AGENCE",
                                                  "COMPTE", "DEVISE", "RELEVE"]):
                    out["titulaire"]["raison_sociale"] = line.strip()
                    break

        # Date arrete
        for pat in [
            r"SOLDE\s+FINAL\s+AU\s+(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4})",
            r"ARRETE\s+AU\s+(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4})",
            r"AU\s+(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4})",
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

        # BMCE RIB: 011 XXX XXXXXXXXXXXXXXXX XX
        m = re.search(r"\b(011)\s+(\d{3})\s+(\d{16,20})\s+(\d{2})\b", t)
        if m:
            return {
                "code_banque": m.group(1),
                "code_localite": m.group(2),
                "numero_principal": m.group(3),
                "cle_rib": m.group(4),
                "rib_complet": m.group(1) + m.group(2) + m.group(3) + m.group(4),
            }

        # Generic fallback
        m = re.search(r"\b(011)\s+(\d{3})\s+((?:\d\s*){16,20})\s+(\d{2})\b", t)
        if m:
            principal = re.sub(r"\D+", "", m.group(3))
            return {
                "code_banque": m.group(1),
                "code_localite": m.group(2),
                "numero_principal": principal,
                "cle_rib": m.group(4),
                "rib_complet": m.group(1) + m.group(2) + principal + m.group(4),
            }
        return {}

    def extract_soldes(self, text: str) -> dict:
        from utils.common import extract_soldes
        return extract_soldes(text, "bmce")

    def _line_to_tx(self, line: str, year: int) -> dict:
        """Parse BMCE transaction line.
        Format flexible: date_op date_val ref nature montant
        """
        raw = norm(line).replace("@", "0").replace("O", "0")

        # Try pattern: DD MM YYYY DD MM YYYY ref nature montant
        m = re.match(
            r"^(?P<d1>\d{2})\s+(?P<m1>\d{2})\s+(?P<y1>20\d{2})\s+"
            r"(?P<d2>\d{2})\s+(?P<m2>\d{2})\s+(?P<y2>20\d{2})\s+(?P<rest>.+)$",
            raw,
        )
        if not m:
            # Try: DD/MM/YYYY DD/MM/YYYY rest
            m = re.match(
                r"^(?P<d1>\d{2})/(?P<m1>\d{2})/(?P<y1>\d{4})\s+"
                r"(?P<d2>\d{2})/(?P<m2>\d{2})/(?P<y2>\d{4})\s+(?P<rest>.+)$",
                raw,
            )
        if not m:
            # Try: DD/MM DD/MM rest (short year)
            m = re.match(
                r"^(?P<d1>\d{2})/(?P<m1>\d{2})\s+(?P<d2>\d{2})/(?P<m2>\d{2})\s+(?P<rest>.+)$",
                raw,
            )
            if m:
                gd = m.groupdict()
                y1 = y2 = year
                if int(gd["m2"]) < int(gd["m1"]):
                    y2 = year + 1
                raw_rest = gd["rest"]
                amounts = AMOUNT_RE.findall(raw_rest)
                amount = clean_amount(amounts[-1]) if amounts else None
                nature = raw_rest
                ref = ""
                if amounts:
                    nature = norm(raw_rest[:raw_rest.rfind(amounts[-1])])
                rm = re.match(r"^([A-Z0-9\-]{3,12})\s+(.+)$", nature, re.I)
                if rm:
                    ref = rm.group(1)
                    nature = norm(rm.group(2))

                debit = credit = None
                if amount is not None:
                    if looks_credit(nature):
                        credit = amount
                    else:
                        debit = amount

                return {
                    "ligne": None,
                    "date_operation": clean_date_parts(gd["d1"], gd["m1"], str(y1)),
                    "date_valeur": clean_date_parts(gd["d2"], gd["m2"], str(y2)),
                    "reference": ref,
                    "nature_operation": clean_nature_text(nature),
                    "type_operation": clean_nature_text(nature),
                    "operation_categorie": classify_operation(nature),
                    "montant_debit": debit,
                    "montant_credit": credit,
                }
            return None

        gd = m.groupdict()
        rest = norm(gd["rest"])
        amounts = AMOUNT_RE.findall(rest)
        amount = clean_amount(amounts[-1]) if amounts else None

        nature = rest
        ref = ""
        if amounts:
            nature = norm(rest[:rest.rfind(amounts[-1])])
        rm = re.match(r"^([A-Z0-9\-]{3,12})\s+(.+)$", nature, re.I)
        if rm:
            ref = rm.group(1)
            nature = norm(rm.group(2))

        debit = credit = None
        if amount is not None:
            if looks_credit(nature):
                credit = amount
            else:
                debit = amount

        return {
            "ligne": None,
            "date_operation": clean_date_parts(gd["d1"], gd["m1"], gd["y1"]),
            "date_valeur": clean_date_parts(gd["d2"], gd["m2"], gd["y2"]),
            "reference": ref,
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
