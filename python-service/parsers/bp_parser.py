"""
Parser Banque Populaire — adapté du code original.
Format: DD MM YYYY DD MM YYYY REF nature montant
"""

import re, cv2, numpy as np
from .base_parser import BaseBankParser
from utils.common import (
    norm, clean_amount, clean_date, clean_date_parts,
    classify_operation, looks_credit, clean_nature_text, AMOUNT_RE
)


class BanquePopulaireParser(BaseBankParser):
    BANK_NAME = "Banque Populaire"
    BANK_CODE = "190"

    def parse_header(self, text: str) -> dict:
        lines = [norm(x) for x in text.splitlines() if norm(x)]
        out = {
            "banque": {"nom": "Banque Populaire"},
            "titulaire": {},
            "releve": {},
        }

        # Agency number
        for line in lines[:12]:
            m = re.search(r"\b(\d{4})\b", line)
            if m:
                out["banque"]["numero_agence"] = m.group(1)
                break

        # Agency name + company
        m = re.search(r"Ag\s*ence\s*[:;]?\s*([A-Z0-9\- ]+)", text, re.I)
        if m:
            nom = norm(m.group(1))
            nom = re.split(r"Adresse|T[eé]l|EXTRAIT|\n", nom,
                          flags=re.I)[0].strip()
            sp = re.search(r"\b(STE|SOCIETE|SARL|SA)\b", nom, re.I)
            if sp and sp.start() > 0:
                out["banque"]["nom_agence"] = nom[:sp.start()].strip()
                out["titulaire"]["raison_sociale"] = nom[sp.start():].strip()
            else:
                out["banque"]["nom_agence"] = nom

        # Address
        m = re.search(r"Adresse\s*[:;=]?\s*(.*?)(?:T[eé]l|EXTRAIT|$)",
                     text, re.I | re.S)
        if m:
            out["banque"]["adresse_agence"] = norm(m.group(1))[:180]

        # Phone
        m = re.search(r"T[eé]l\s*[:;=>]?\s*([\d .\-]+)", text, re.I)
        if m:
            out["banque"]["telephone"] = norm(m.group(1))

        # Document type
        out["releve"]["type_document"] = (
            "EXTRAIT DE COMPTE"
            if re.search(r"EXTRAIT\s+DE\s+COMPTE", text, re.I)
            else "RELEVE DE COMPTE"
        )

        # Date arrete
        m = re.search(r"AU\s+(\d{1,2}[ /\-]\d{1,2}[ /\-]\d{4})", text, re.I)
        if m:
            out["releve"]["date_arrete"] = clean_date(m.group(1))

        # Company type
        if out["titulaire"].get("raison_sociale"):
            up = out["titulaire"]["raison_sociale"].upper()
            out["titulaire"]["type"] = (
                "SARL AU" if "SARL AU" in up else
                "SARLAU" if "SARLAU" in up else
                "SARL" if "SARL" in up else
                "SA" if "SA" in up else ""
            )
        return out

    def extract_rib(self, text_or_img) -> dict:
        if isinstance(text_or_img, str):
            return self._extract_rib_text(text_or_img)
        return self._extract_rib_image(text_or_img)

    def _extract_rib_text(self, text: str) -> dict:
        t = norm(text).replace("O", "0")
        nums = re.findall(r"\d+", t)
        joined = " ".join(nums)
        cb = "190" if re.search(r"\b190\b", joined) else None
        cl = None
        for n in nums:
            if len(n) == 3 and n != "190" and n != "000":
                cl = n
                break
        m = re.search(r"(\d{5})\s*(\d{6,8})\s*(\d{3})\s*(\d)", joined)
        principal = None
        principal_sp = None
        if m:
            principal = "".join(m.groups())
            principal_sp = f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}"
        cle = None
        for n in nums[::-1]:
            if len(n) == 2:
                cle = n
                break
        if cb and cl and principal and cle:
            return {
                "code_banque": cb, "code_localite": cl,
                "numero_principal": principal_sp,
                "cle_rib": cle, "rib_complet": cb + cl + principal + cle,
            }
        return {}

    def _extract_rib_image(self, page_img) -> dict:
        h, w = page_img.shape[:2]
        zone = page_img[int(h*0.34):int(h*0.46), 0:int(w*0.62)]
        txt = (self.ocr_string(zone, psm="6", whitelist="0123456789 ") +
               " " +
               self.ocr_string(zone, psm="11", whitelist="0123456789 "))
        return self._extract_rib_text(txt)

    def _split_line(self, line: str) -> dict:
        raw = norm(line)
        s = re.sub(r"(?<=\d)[lI](?=\d)", " ", raw.replace("/", " "))
        s = norm(s)

        # Pattern: DD MM YYYY [D2TAIL] D2? M2 YYYY rest
        m = re.search(
            r"^(?P<d1>\d{2})\s+(?P<m1>\d{2})\s+(?P<y1>20\d{2})"
            r"(?P<d2tail>\d{0,3})\s+(?P<d2>\d{1,3})?\s*"
            r"(?P<m2>\d{2})\s+(?P<y2>20\d{2})\s*(?P<rest>.*)$",
            s,
        )
        if not m:
            m3 = re.search(
                r"^(?P<d1>\d{2})\s+(?P<m1>\d{2})\s+(?P<y1>20\d{2})\s+"
                r"(?P<d2>\d{2})\s+(?P<m2>\d{2})\s+(?P<rest>.*)$",
                s,
            )
            if not m3:
                return None
            gd = m3.groupdict()
            d1, m1, y1 = gd["d1"], gd["m1"], gd["y1"]
            d2, m2 = gd["d2"], gd["m2"]
            y2 = str(int(y1) - 1 if int(m2) > int(m1) else int(y1))
            rest = norm(gd["rest"])
        else:
            gd = m.groupdict()
            d1, m1, y1 = gd["d1"], gd["m1"], gd["y1"]
            d2 = (gd.get("d2tail") or gd.get("d2") or "")[-2:]
            m2, y2 = gd["m2"], gd["y2"]
            rest = norm(gd["rest"])

        date_op = clean_date_parts(d1, m1, y1)
        date_val = clean_date_parts(d2, m2, y2)
        if not date_op or not date_val:
            return None

        # Extract reference
        rest_ref = rest.replace("O", "0")
        ref = ""
        rm = re.match(r"^([A-Z0-9]{4,12})\s*(.*)$", rest_ref, re.I)
        if rm:
            cand = rm.group(1).upper()
            if cand not in {"PAIEMENT", "RETRAIT", "COMMISSION", "TAXE", "FRAIS", "VIR"}:
                if len(cand) > 6 and cand[0] in "01519":
                    cand = cand[-6:]
                ref = cand
                rest = norm(rest[len(rm.group(1)):])

        # Extract amount
        amounts = AMOUNT_RE.findall(rest)
        amount = clean_amount(amounts[-1]) if amounts else None

        nature = rest
        if amounts:
            nature = norm(nature.replace(amounts[-1], "", 1))

        debit = credit = None
        if amount is not None:
            if looks_credit(nature):
                credit = amount
            else:
                debit = amount

        return {
            "ligne": None,
            "date_operation": date_op,
            "date_valeur": date_val,
            "reference": ref,
            "nature_operation": norm(nature),
            "type_operation": norm(nature),
            "operation_categorie": classify_operation(nature),
            "montant_debit": debit,
            "montant_credit": credit,
        }

    def extract_transactions(self, page_img, **kwargs) -> list:
        h, w = page_img.shape[:2]
        crop = page_img[int(h*0.39):int(h*0.95), int(w*0.01):int(w*0.99)]
        crop = cv2.resize(crop, None, fx=0.72, fy=0.72,
                         interpolation=cv2.INTER_AREA)
        raw = self.ocr_string(crop, psm="6")
        lines = [norm(x) for x in raw.splitlines() if norm(x)]

        txs = []
        current = None

        def flush():
            nonlocal current
            if current:
                current["nature_operation"] = norm(current.get("nature_operation", ""))
                current["type_operation"] = current["nature_operation"]
                current["operation_categorie"] = classify_operation(
                    current["nature_operation"])
                current["ligne"] = len(txs) + 1
                txs.append(current)
                current = None

        for line in lines:
            if re.search(r"DATE|VALEUR|REFERENCE|NATURE|MONTANT|RELEVE|EXTRAIT|CODE BANQUE|C\. RIB",
                        line, re.I):
                continue
            if re.search(r"ANCIEN\s+SOLDE|SOLDE\s+A\s+REPORTER", line, re.I):
                flush()
                continue

            tx = self._split_line(line)
            if tx:
                flush()
                current = tx
                continue

            if current:
                amounts = AMOUNT_RE.findall(line)
                if (current.get("montant_debit") is None and
                    current.get("montant_credit") is None and amounts):
                    amt = clean_amount(amounts[-1])
                    if looks_credit(current.get("nature_operation", "")):
                        current["montant_credit"] = amt
                    else:
                        current["montant_debit"] = amt
                cl = line
                for a in amounts:
                    cl = cl.replace(a, "")
                cl = norm(cl)
                if cl and not re.fullmatch(r"[\d\s.,:=\-\/]+", cl):
                    current["nature_operation"] += " " + cl

        flush()
        return txs

    def extract_soldes(self, text: str) -> dict:
        from utils.common import extract_soldes
        return extract_soldes(text, "bp")
