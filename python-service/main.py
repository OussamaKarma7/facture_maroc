#!/usr/bin/env python3
"""
Releveim Bank Statement Parser — CLI entry point.
Called by the Node.js backend to parse Moroccan bank statements.

Usage:
    python main.py parse <file_path> [--bank BANK]
    python main.py detect <file_path>
"""

import sys, os, json, argparse

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.bp_parser import BanquePopulaireParser
from parsers.attijari_parser import AttijariwafaParser
from parsers.cih_parser import CIHParser
from parsers.bmce_parser import BMCEParser
from parsers.bmci_parser import BMCIParser
from utils.common import detect_bank_from_text, norm


def detect_bank(filepath: str) -> str:
    """Quick bank detection from first page OCR."""
    # Try with Attijari parser (has OCR)
    parser = AttijariwafaParser()
    try:
        pages = parser.load_pages(filepath)
        if pages:
            h, w = pages[0].shape[:2]
            text = parser.ocr_string(pages[0][:int(h*0.45), :], psm="6")
            bank = detect_bank_from_text(text)
            if bank != "INCONNUE":
                return bank
    except Exception:
        pass
    return "INCONNUE"


def get_parser(bank_name: str):
    """Get the right parser for the bank."""
    parsers = {
        "BANQUE POPULAIRE": BanquePopulaireParser(),
        "ATTIJARIWAFA BANK": AttijariwafaParser(),
        "CIH": CIHParser(),
        "CIH BANK": CIHParser(),
        "BMCE": BMCEParser(),
        "BMCE BANK": BMCEParser(),
        "BMCI": BMCIParser(),
    }
    return parsers.get(bank_name.upper())


def parse_statement(filepath: str, bank_hint: str = None) -> dict:
    """Parse a bank statement file and return structured data."""
    # Step 1: Detect bank if not provided
    if not bank_hint or bank_hint == "AUTO":
        bank_name = detect_bank(filepath)
    else:
        bank_name = bank_hint.upper()

    # Step 2: Get parser
    parser = get_parser(bank_name)
    if not parser:
        # Fallback: try all parsers and pick the one with most transactions
        best_result = None
        best_count = -1
        for name, p in {
            "BANQUE POPULAIRE": BanquePopulaireParser(),
            "ATTIJARIWAFA BANK": AttijariwafaParser(),
            "CIH BANK": CIHParser(),
            "BMCE BANK": BMCEParser(),
            "BMCI": BMCIParser(),
        }.items():
            try:
                result = p.parse_file(filepath)
                count = result.get("_nb_transactions", 0)
                if count > best_count:
                    best_count = count
                    best_result = result
                    best_result["banque"]["nom"] = name
            except Exception:
                continue
        if best_result and best_count > 0:
            return best_result
        return {
            "error": f"Banque non supportee ou fichier illisible: {bank_name}",
            "banque_detectee": bank_name,
        }

    # Step 3: Parse
    try:
        result = parser.parse_file(filepath)
        return result
    except Exception as e:
        return {
            "error": str(e),
            "banque_detectee": bank_name,
        }


def main():
    parser = argparse.ArgumentParser(description="Releveim Bank Statement Parser")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse a bank statement")
    parse_parser.add_argument("filepath", help="Path to PDF or image file")
    parse_parser.add_argument("--bank", default="AUTO",
                             help="Bank name hint (AUTO, Banque Populaire, Attijariwafa, CIH, BMCE, BMCI)")
    parse_parser.add_argument("--output", "-o", help="Output JSON file")

    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect bank from statement")
    detect_parser.add_argument("filepath", help="Path to PDF or image file")

    args = parser.parse_args()

    if args.command == "parse":
        result = parse_statement(args.filepath, args.bank)
        json_output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Result saved to {args.output}")
        else:
            print(json_output)

    elif args.command == "detect":
        bank = detect_bank(args.filepath)
        print(json.dumps({"bank": bank}, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
