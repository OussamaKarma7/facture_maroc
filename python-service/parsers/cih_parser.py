"""
Parser CIH Bank — Credit Immobilier et Hotelier.
Format spécifique: dates collées DD/MMDD/MM, bilingue FR/AR.
"""

import re, cv2, numpy as np
from datetime import datetime
from .base_parser import BaseBankParser
from utils.common import (
    norm, clean_amount, clean_date, clean_date_parts,
    classify_operation, looks_credit, clean_nature_text, AMOUNT_RE
)


class CIHParser(BaseBankParser):
    BANK_NAME = "CIH Bank"
    BANK_CODE = "230"

    def parse_header(self, text: str) -> dict:
        out = {
            "banque": {"nom": "CIH Bank"},
            "titulaire": {},
            "releve": {},
        }
        lines = [norm(x) for x in text.splitlines() if norm(x)]

        # Agency
        m = re.search(r"AGENCE\s*[:;]?\s*([A-Z0-9\-' .]+)", text, re.I)
        if m:
            ag = norm(m.group(1))
            ag = re.split(r"N\s*[°°]|T[EÉ]L|COMPTE|\n", ag, flags=re.I)[0].strip()
            out["banque"]["nom_agence"] = ag

        # Phone
        m = re.search(r"T[EÉ]L\s*[:;/.]?\s*([\d ./\-]+)", text, re.I)
        if m:
            out["banque"]["telephone"] = norm(m.group(1))

        # Titulaire
        for i, line in enumerate(lines):
            up = line.upper()
            if re.search(r"\b(SARL|SA|S\.A\.R\.L|S\.A\b)", up):
                if not any(bad in up for bad in ["BANQUE", "CIH", "AGENCE",
                                                  "COMPTE", "DEVISE", "RELEVE"]):
                    out["titulaire"]["raison_sociale"] = line.strip()
                    break

        # Date arrete
        m = re.search(r"NOUVEAU\s+SOLDE\s+AU\s*[:.]?\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.I)
        if m:
            out["releve"]["date_arrete"] = clean_date(m.group(1))

        m = re.search(r"SOLDE\s+DEPART\s+AU\s*[:.]?\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.I)
        if m:
            out["releve"]["date_debut"] = clean_date(m.group(1))

        out["releve"]["type_document"] = "RELEVE DE COMPTE BANCAIRE"

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

        # CIH RIB: 230 XXX XXXXXXXXXXXXXXXX XX
        m = re.search(r"\b(230)\s+(\d{3})\s+(\d{16,20})\s+(\d{2})\b", t)
        if m:
            return {
                "code_banque": m.group(1),
                "code_localite": m.group(2),
                "numero_principal": m.group(3),
                "cle_rib": m.group(4),
                "rib_complet": m.group(1) + m.group(2) + m.group(3) + m.group(4),
            }

        # Generic fallback for 230
        m = re.search(r"\b(230)\s+(\d{3})\s+((?:\d\s*){16,20})\s+(\d{2})\b", t)
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
        return extract_soldes(text, "cih")

    def _line_to_tx(self, line: str, year: int) -> dict:
        """Parse CIH transaction line.
        Format: DD/MMDD/MM nature montant
                ou DD/MM DD/MM nature montant
        """
        raw = norm(line).replace("@", "0").replace("O", "0")

        # Pattern 1: DD/MMDD/MM nature montant (dates collées)
        m = re.match(
            r"^(?P<d1>\d{2})/(?P<m1>\d{2})(?P<d2>\d{2})/(?P<m2>\d{2})\s+(?P<rest>.+)$",
            raw,
        )
        if not m:
            # Pattern 2: DD/MM DD/MM nature montant (dates séparées)
            m = re.match(
                r"^(?P<d1>\d{2})/(?P<m1>\d{2})\s+(?P<d2>\d{2})/(?P<m2>\d{2})\s+(?P<rest>.+)$",
                raw,
            )
        if not m:
            # Pattern 3: DD MM DD MM nature montant
            m = re.match(
                r"^(?P<d1>\d{2})\s+(?P<m1>\d{2})\s+(?P<d2>\d{2})\s+(?P<m2>\d{2})\s+(?P<rest>.+)$",
                raw,
            )

        if not m:
            return None

        gd = m.groupdict()
        d1, m1 = gd["d1"], gd["m1"]
        d2, m2 = gd["d2"], gd["m2"]
        rest = norm(gd["rest"])

        # Determine year for date operation
        y1 = year
        y2 = year
        # If month2 < month1, likely date valeur is next year
        if int(m2) < int(m1):
            y2 = year + 1
        elif int(m2) > int(m1):
            y2 = year

        # Find amount at end
        amounts = AMOUNT_RE.findall(rest)
        amount = None
        nature = rest
        if amounts:
            amount = clean_amount(amounts[-1])
            nature = norm(rest[:rest.rfind(amounts[-1])])

        # Remove reference from nature
        ref = ""
        rm = re.match(r"^([A-Z0-9\-/]{3,15})\s+(.+)$", nature, re.I)
        if rm:
            ref = rm.group(1)
            nature = norm(rm.group(2))

        debit = credit = None
        if amount is not None:
            if looks_credit(nature):
                credit = amount
            else:
                debit = amount

        date_op = clean_date_parts(d1, m1, str(y1))
        date_val = clean_date_parts(d2, m2, str(y2))

        return {
            "ligne": None,
            "date_operation": date_op,
            "date_valeur": date_val,
            "reference": ref,
            "nature_operation": clean_nature_text(nature),
            "type_operation": clean_nature_text(nature),
            "operation_categorie": classify_operation(nature),
            "montant_debit": debit,
            "montant_credit": credit,
        }

    def extract_transactions(self, page_img, **kwargs) -> list:
        h, w = page_img.shape[:2]
        # CIH transactions are usually in the middle section
        crop = page_img[int(h*0.32):int(h*0.85), int(w*0.03):int(w*0.97)]
        raw = self.ocr_string(crop, psm="6")
        year = kwargs.get("default_year", datetime.now().year)

        # Remove Arabic text lines (lines with non-Latin characters)
        lines = []
        for line in raw.splitlines():
            line = norm(line)
            # Skip if mostly Arabic characters
            if line and not re.search(r"[\u0600-\u06FF\u0750-\u077F]", line):
                lines.append(line)

        txs = []
        for line in lines:
            if re.search(r"DATE|OPER|VALEUR|OPERATION|REFERENCE|DEBIT|CREDIT|TOTAL|SOLDE|Mouvements",
                        line, re.I):
                continue
            if re.search(r"\bD\s*E\s*D\s*U\s*C\s*T\s*I\s*O\s*N\b", line, re.I):
                continue
            tx = self._line_to_tx(line, year)
            if tx:
                tx["ligne"] = len(txs) + 1
                txs.append(tx)

        return txs
