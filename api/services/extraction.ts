/**
 * Service d'extraction des relevés bancaires.
 * Appelle le script Python OCR pour extraire les transactions.
 */
import { spawn } from "child_process";

export interface ParsedReleve {
  banque: {
    nom: string;
    nom_agence?: string;
    adresse_agence?: string;
    telephone?: string;
    numero_agence?: string;
  };
  titulaire: {
    raison_sociale?: string;
    type?: string;
    adresse?: string;
  };
  compte: {
    code_banque?: string;
    code_localite?: string;
    numero_principal?: string;
    cle_rib?: string;
    rib_complet?: string;
  };
  releve: {
    type_document?: string;
    date_arrete?: string;
    date_debut?: string;
  };
  soldes: {
    ancien_solde_date?: string;
    ancien_solde_montant?: number;
    ancien_solde_montant_ocr?: number;
    ancien_solde_corrige_auto?: boolean;
    solde_reporter?: number;
    solde_theorique?: number;
    verification_ok?: boolean;
    total_debits?: number;
    total_credits?: number;
    total_debits_banque?: number;
    total_credits_banque?: number;
  };
  transactions: Array<{
    ligne: number;
    date_operation: string;
    date_valeur: string;
    reference: string;
    nature_operation: string;
    type_operation: string;
    operation_categorie: string;
    montant_debit: number | null;
    montant_credit: number | null;
  }>;
  meta: {
    source: string;
    confiance: string;
  };
  _nb_transactions: number;
  _ocr_text_brut?: string;
  _extracted_at: string;
  error?: string;
  banque_detectee?: string;
}

export async function extractReleveWithPython(
  filePath: string,
  bankHint?: string
): Promise<ParsedReleve> {
  const pythonScript = process.cwd() + "/python-service/main.py";

  return new Promise((resolve, _reject) => {
    const args = [pythonScript, "parse", filePath, "--bank", bankHint || "AUTO"];
    const proc = spawn("python3", args, {
      timeout: 120000,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data: Buffer) => {
      stdout += data.toString("utf-8");
    });

    proc.stderr.on("data", (data: Buffer) => {
      stderr += data.toString("utf-8");
    });

    proc.on("close", (code) => {
      if (code !== 0 && code !== null) {
        console.error("Python OCR stderr:", stderr);
        // Return error in structured format
        resolve({
          banque: { nom: "UNKNOWN" },
          titulaire: {},
          compte: {},
          releve: {},
          soldes: {},
          transactions: [],
          meta: { source: "error", confiance: "none" },
          _nb_transactions: 0,
          _extracted_at: new Date().toISOString(),
          error: `Python exited with code ${code}: ${stderr.slice(0, 200)}`,
        } as ParsedReleve);
        return;
      }

      try {
        // Find JSON in stdout
        const jsonStart = stdout.indexOf("{");
        const jsonEnd = stdout.lastIndexOf("}") + 1;
        if (jsonStart === -1) {
          resolve({
            banque: { nom: "UNKNOWN" },
            titulaire: {},
            compte: {},
            releve: {},
            soldes: {},
            transactions: [],
            meta: { source: "error", confiance: "none" },
            _nb_transactions: 0,
            _extracted_at: new Date().toISOString(),
            error: "No JSON output from Python parser",
          } as ParsedReleve);
          return;
        }
        const jsonStr = stdout.slice(jsonStart, jsonEnd);
        const result = JSON.parse(jsonStr) as ParsedReleve;
        resolve(result);
      } catch (e) {
        resolve({
          banque: { nom: "UNKNOWN" },
          titulaire: {},
          compte: {},
          releve: {},
          soldes: {},
          transactions: [],
          meta: { source: "error", confiance: "none" },
          _nb_transactions: 0,
          _extracted_at: new Date().toISOString(),
          error: `JSON parse error: ${(e as Error).message}`,
        } as ParsedReleve);
      }
    });

    proc.on("error", (err) => {
      console.error("Failed to start Python:", err);
      resolve({
        banque: { nom: "UNKNOWN" },
        titulaire: {},
        compte: {},
        releve: {},
        soldes: {},
        transactions: [],
        meta: { source: "error", confiance: "none" },
        _nb_transactions: 0,
        _extracted_at: new Date().toISOString(),
        error: `Python not available: ${err.message}. Install python3, tesseract-ocr, and requirements.txt`,
      } as ParsedReleve);
    });
  });
}
