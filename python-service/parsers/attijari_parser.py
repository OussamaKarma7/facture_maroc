"""
Parser Attijariwafa Bank — adapté du code original.
Format: CODE6 DD MM description ... JJ MM YYYY montant
"""

import re, cv2, numpy as np
from .base_parser import BaseBankParser
from utils.common import (
    norm, clean_amount, clean_date, clean_date_parts,
    classify_operation, looks_credit, clean_nature_text, AMOUNT_RE
)


class AttijariwafaParser(BaseBankParser):
    BANK_NAME = "Attijariwafa Bank"
    BANK_CODE = "007"

    def parse_header(self, text: str) -> dict:
        out = {
            "banque": {"nom": "Attijariwafa bank"},
            "titulaire": {},
            "releve": {},
        }
        lines = [norm(x) for x in text.splitlines() if norm(x)]

        # Agency
        m = re.search(r"(?:AGENCE|AGENCY)\s*[:;]?\s*([A-Z0-9 .'-]+)", text, re.I)
        if m:
            ag = norm(re.split(r"COMPTE|DEVISE|RELEVE|\n", m.group(1), flags=re.I)[0])
            ag = re.sub(r"^(SUCC\.?\s*)", "", ag, flags=re.I).strip()
            out["banque"]["nom_agence"] = clean_nature_text(ag).title()

        # Titulaire: after RELEVE DE COMPTE BANCAIRE
        for i, line in enumerate(lines):
            if "RELEVE DE COMPTE" in line.upper():
                for cand in lines[i+1:i+5]:
                    up = cand.upper()
                    if (len(cand) > 4 and
                        not any(x in up for x in ["AGENCE", "COMPTE", "RIB",
                                                  "DIRHAM", "BANCAIRE"])):
                        cand = re.sub(r"^[^A-Z]*(?=[A-Z])", "", cand).strip()
                        out["titulaire"]["raison_sociale"] = clean_nature_text(cand)
                        break
                break

        if not out["titulaire"].get("raison_sociale"):
            for line in lines:
                up = line.upper()
                if re.search(r"\b(SARL|SA|SOCIETE|STRATEGY|INVEST|UNIVERSAL)\b", up):
                    if not any(bad in up for bad in ["BANQUE", "ATTIJARI", "AGENCE",
                                                      "COMPTE", "DEVISE", "RIB"]):
                        line = re.sub(r"^[^A-Z]*(?=[A-Z])", "", line).strip()
                        out["titulaire"]["raison_sociale"] = clean_nature_text(line)
                        break

        # Adresse
        titulaire = out["titulaire"].get("raison_sociale", "")
        addr = []
        if titulaire:
            started = False
            for line in lines:
                if not started and titulaire.split()[0] in line.upper():
                    started = True
                    continue
                if started:
                    up = line.upper()
                    if any(stop in up for stop in ["RELEVE D", "IDENTITE", "RIB",
                                                   "NOUS", "SOLDE", "PAGE", "CODE", "DATE"]):
                        break
                    if not any(bad in up for bad in ["AGENCE", "COMPTE", "DEVISE", "DIRHAM"]):
                        clean_line = clean_nature_text(line)
                        if clean_line and clean_line not in addr:
                            addr.append(clean_line)
        if addr:
            out["titulaire"]["adresse"] = " ".join(addr)[:180]

        # Type societe
        if out["titulaire"].get("raison_sociale"):
            up = out["titulaire"]["raison_sociale"].upper()
            if "SARL" in up:
                out["titulaire"]["type"] = "SARL"
            elif re.search(r"\bSA\b", up):
                out["titulaire"]["type"] = "SA"

        out["releve"]["type_document"] = "RELEVE DE COMPTE BANCAIRE"
        m = re.search(r"SOLDE\s+DEPART\s+AU\s+(\d{1,2}\s+\d{1,2}\s+\d{4})", text, re.I)
        if m:
            out["soldes_date_depart"] = clean_date(m.group(1))
        m = re.search(r"SOLDE\s+FINAL\s+AU\s+(\d{1,2}\s+\d{1,2}\s+\d{4})", text, re.I)
        if m:
            out["releve"]["date_arrete"] = clean_date(m.group(1))
        return out

    def extract_rib(self, text_or_img) -> dict:
        if isinstance(text_or_img, np.ndarray):
            h, w = text_or_img.shape[:2]
            zone = text_or_img[int(h*0.34):int(h*0.46), :]
            text = self.ocr_string(zone, psm="6", whitelist="0123456789 ")
        else:
            text = text_or_img

        t = norm(text).replace("O", "0").replace("E", "5")

        # Pattern: RELEVE D'IDENTITE BANCAIRE 007 780 00 01265000004691 35
        m = re.search(r"\b(007)\s+(\d{3})\s+((?:\d\s*){16})\s+(\d{2})\b", t)
        if not m:
            m = re.search(r"\b(007)\s+(\d{3})\s+(\d{2})\s*(\d{16})\s+(\d{2})\b", t)
            if m:
                return {
                    "code_banque": m.group(1),
                    "code_localite": m.group(2),
                    "numero_principal": m.group(3) + m.group(4),
                    "cle_rib": m.group(5),
                    "rib_complet": m.group(1) + m.group(2) + m.group(3) + m.group(4) + m.group(5),
                }
        if m:
            principal = re.sub(r"\D+", "", m.group(3))
            if len(principal) > 16:
                principal = principal[-16:]
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
        return extract_soldes(text, "awb")

    def _line_to_tx(self, line: str, year: int) -> dict:
        raw = norm(line).replace("@", "0")
        parse_raw = raw.replace("O", "0").replace("o", "0")
        parse_raw = re.sub(r"(?<=[A-Z0-9])[lI](?=\d{2}\s+\d{2})", " ", parse_raw)
        parse_raw = parse_raw.replace("/", " ")

        # Pattern: CODE6 DD MM rest
        m = re.match(
            r"^(?P<code>[A-Z0-9]{6,7})\s*(?P<d1>\d{2})\s+(?P<m1>\d{2})\s+(?P<rest>.+)$",
            parse_raw, re.I,
        )
        if not m:
            # OCR sometimes glues code and date
            m = re.match(
                r"^(?P<code>[A-Z0-9]{6})(?P<d1>\d{2})\s+(?P<m1>\d{2})\s+(?P<rest>.+)$",
                parse_raw, re.I,
            )
        if not m:
            return None

        gd = m.groupdict()
        code = gd["code"].upper()
        d1, m1 = gd["d1"], gd["m1"]
        rest = norm(gd["rest"])

        # Find value date near end
        date_matches = list(re.finditer(r"(\d{2})\s+(\d{2})\s+(20\d{2})", rest))
        if not date_matches:
            return None

        dm = date_matches[-1]
        d2, m2, y2 = dm.group(1), dm.group(2), dm.group(3)
        nature = clean_nature_text(rest[:dm.start()])
        tail = norm(rest[dm.end():])

        amounts = AMOUNT_RE.findall(tail)
        amount = clean_amount(amounts[0]) if amounts else None
        if amount is None:
            amounts = AMOUNT_RE.findall(rest)
            amount = clean_amount(amounts[0]) if amounts else None
            if amounts:
                nature = clean_nature_text(nature.replace(amounts[0], ""))

        debit = credit = None
        if amount is not None:
            if looks_credit(nature):
                credit = amount
            else:
                debit = amount

        date_op = clean_date_parts(d1, m1, year)
        date_val = clean_date_parts(d2, m2, y2)

        return {
            "ligne": None,
            "date_operation": date_op,
            "date_valeur": date_val,
            "reference": code,
            "nature_operation": clean_nature_text(nature),
            "type_operation": clean_nature_text(nature),
            "operation_categorie": classify_operation(nature),
            "montant_debit": debit,
            "montant_credit": credit,
        }

    def extract_transactions(self, page_img, **kwargs) -> list:
        h, w = page_img.shape[:2]
        crop = page_img[int(h*0.43):int(h*0.86), int(w*0.04):int(w*0.94)]
        raw = self.ocr_string(crop, psm="6")
        year = kwargs.get("default_year", datetime.now().year)

        txs = []
        for line in [norm(x) for x in raw.splitlines() if norm(x)]:
            if re.search(r"CODE|DATE|LIBELLE|VALEUR|DEBIT|CREDIT|TOTAL|SOLDE",
                        line, re.I):
                continue
            tx = self._line_to_tx(line, year)
            if tx:
                tx["ligne"] = len(txs) + 1
                txs.append(tx)
        return txs
