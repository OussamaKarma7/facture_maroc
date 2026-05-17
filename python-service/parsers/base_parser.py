"""
Classe de base abstraite pour les parsers de relevés bancaires.
Tous les parsers spécifiques doivent hériter de cette classe.
"""

import re, os, sys, cv2, numpy as np, fitz
from pathlib import Path
from PIL import Image
from datetime import datetime
from abc import ABC, abstractmethod

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.common import (
    norm, clean_amount, clean_date, clean_date_parts,
    classify_operation, looks_credit, clean_nature_text,
    AMOUNT_RE
)

# Tesseract config
TESSERACT_PATHS = [
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    r"/usr/bin/tesseract",
]
for p in TESSERACT_PATHS:
    if os.path.exists(p):
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = p
        break
else:
    import pytesseract


class BaseBankParser(ABC):
    """Base class for all Moroccan bank statement parsers."""

    BANK_NAME = "UNKNOWN"
    BANK_CODE = None

    def __init__(self):
        self.tesseract_available = self._check_tesseract()

    def _check_tesseract(self):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def load_pages(self, filepath: str) -> list:
        """Load PDF or image and return list of cv2 images."""
        p = Path(filepath)
        ext = p.suffix.lower()
        pages = []
        if ext == ".pdf":
            doc = fitz.open(filepath)
            for i, page in enumerate(doc):
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                arr = np.frombuffer(pix.tobytes("png"), np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    pages.append(img)
            doc.close()
        elif ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"):
            img = cv2.imread(filepath)
            if img is None:
                raise ValueError("Impossible de lire l'image")
            if img.shape[1] < 1400:
                scale = 1400 / img.shape[1]
                img = cv2.resize(img, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)
            pages.append(img)
        else:
            raise ValueError(f"Format non supporté : {ext}")
        return pages

    def preprocess(self, img: np.ndarray) -> Image.Image:
        """Preprocess image for OCR."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if gray.shape[1] < 1500:
            gray = cv2.resize(gray, None, fx=1.5, fy=1.5,
                            interpolation=cv2.INTER_CUBIC)
        gray = cv2.fastNlMeansDenoising(gray, h=8,
                templateWindowSize=7, searchWindowSize=21)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        _, th = cv2.threshold(gray, 0, 255,
              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(th)

    def ocr_string(self, img: np.ndarray, psm="6", whitelist=None,
                   timeout=45) -> str:
        """Run OCR on image region."""
        if not self.tesseract_available:
            return ""
        import pytesseract
        pil = self.preprocess(img)
        config = f"--psm {psm} --oem 3"
        if whitelist:
            config += f" -c tessedit_char_whitelist={whitelist}"
        for lang in ("fra+eng", "fra", "eng"):
            try:
                return pytesseract.image_to_string(
                    pil, lang=lang, config=config, timeout=timeout)
            except Exception:
                continue
        return ""

    @abstractmethod
    def parse_header(self, text: str) -> dict:
        """Parse header info from OCR text."""
        pass

    @abstractmethod
    def extract_rib(self, text_or_img) -> dict:
        """Extract RIB from text or image."""
        pass

    @abstractmethod
    def extract_transactions(self, page_img, **kwargs) -> list:
        """Extract transaction lines from page image."""
        pass

    @abstractmethod
    def extract_soldes(self, text: str) -> dict:
        """Extract balances from text."""
        pass

    def parse_file(self, filepath: str) -> dict:
        """Main entry point: parse a bank statement file."""
        pages = self.load_pages(filepath)
        if not pages:
            raise ValueError("Aucune page trouvée dans le fichier")

        # OCR all pages
        page_texts = []
        for i, img in enumerate(pages):
            h, w = img.shape[:2]
            # Header region (top 45%)
            header_img = img[:int(h*0.45), :]
            header_text = self.ocr_string(header_img, psm="6")
            # Table region (middle)
            table_img = img[int(h*0.38):int(h*0.90), :]
            table_text = self.ocr_string(table_img, psm="6")
            full_text = header_text + "\n" + table_text
            page_texts.append(full_text)

        full_text = "\n".join(page_texts)
        header_data = self.parse_header(full_text)
        rib_data = self.extract_rib(full_text)
        soldes_data = self.extract_soldes(full_text)

        # Extract transactions from all pages
        all_txs = []
        year = self._extract_year(full_text)
        for img in pages:
            txs = self.extract_transactions(img, default_year=year)
            all_txs.extend(txs)

        # Deduplicate and renumber
        seen = set()
        clean_txs = []
        for tx in all_txs:
            key = (tx.get("date_operation"), tx.get("date_valeur"),
                   tx.get("reference"), tx.get("nature_operation"),
                   tx.get("montant_debit"), tx.get("montant_credit"))
            if key not in seen:
                seen.add(key)
                clean_txs.append(tx)

        for i, tx in enumerate(clean_txs, 1):
            tx["ligne"] = i

        # Build result
        data = {
            "banque": {"nom": self.BANK_NAME},
            "titulaire": {},
            "compte": {},
            "releve": {},
            "soldes": {},
            "transactions": clean_txs,
            "meta": {
                "source": f"Tesseract OCR {self.BANK_NAME}",
                "confiance": "MOYENNE",
            },
            "_ocr_text_brut": full_text,
            "_extracted_at": datetime.now().isoformat(),
        }
        data["banque"].update(header_data.get("banque", {}))
        data["titulaire"].update(header_data.get("titulaire", {}))
        data["releve"].update(header_data.get("releve", {}))
        data["compte"].update(rib_data)
        data["soldes"].update(soldes_data)

        # Calculated totals
        total_d = round(sum(tx.get("montant_debit") or 0
                          for tx in clean_txs), 2)
        total_c = round(sum(tx.get("montant_credit") or 0
                          for tx in clean_txs), 2)
        data["soldes"]["total_debits"] = total_d
        data["soldes"]["total_credits"] = total_c

        # Verification
        ancien = data["soldes"].get("ancien_solde_montant") or 0
        reporter = data["soldes"].get("solde_reporter") or 0
        theorique = round(ancien + total_c - total_d, 2)
        if reporter and (total_d or total_c) and abs(theorique - reporter) > 2:
            data["soldes"]["ancien_solde_montant"] = round(
                reporter - total_c + total_d, 2)
            data["soldes"]["ancien_solde_corrige_auto"] = True
            theorique = round(data["soldes"]["ancien_solde_montant"]
                            + total_c - total_d, 2)
        data["soldes"]["solde_theorique"] = theorique
        data["soldes"]["verification_ok"] = (
            abs(theorique - reporter) < 2 if reporter else False
        )
        data["_nb_transactions"] = len(clean_txs)

        return data

    def _extract_year(self, text: str) -> int:
        """Try to find the year from the statement text."""
        m = re.search(r"SOLDE\s+(?:FINAL|DEPART)\s+AU\s+(\d{1,2})\s+(\d{1,2})\s+(\d{4})",
                     text, re.I)
        if m:
            return int(m.group(3))
        m = re.search(r"(\d{1,2}[ /\-]\d{1,2}[ /\-])(\d{4})", text)
        if m:
            return int(m.group(2))
        return datetime.now().year
