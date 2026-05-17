import { GoogleGenAI } from "@google/genai";
import { env } from "../lib/env";

const API_KEY = env.geminiApiKey || "";

function getClient() {
  if (!API_KEY) {
    throw new Error("GEMINI_API_KEY not configured");
  }
  return new GoogleGenAI({ apiKey: API_KEY });
}

const PLAN_COMPTABLE_MAROCAIN = `
1111 Capital social
1121 Resultats reportes
1481 Emprunts aupres des etablissements de credit
1486 Fournisseurs d immobilisations
2111 Frais de constitution
2113 Frais de prospection
2130 Brevets, marques, droits et valeurs similaires
2151 Logiciels informatiques
2210 Terrains
2220 Constructions
2332 Materiel et outillage
2340 Materiel de transport
2355 Materiel informatique
2356 Materiel de bureautique
2411 Droits de mutation
2833 Amortissement des installations techniques
2834 Amortissement du materiel de transport
2835 Amortissement du materiel de bureau et informatique
3111 Marchandises
3121 Matieres premieres
3151 Produits finis
3211 Matieres consommables
3421 Clients
3424 Clients - effets a recevoir
3455 Etat - TVA recuperable sur charges
3487 Regularisation des creances sur l Etat
4411 Fournisseurs
4421 Fournisseurs - effets a payer
4455 Etat - TVA facturee
4456 Etat - TVA due
4457 Etat - Taxes sur le CA a regulariser
4465 Organismes sociaux - CNSS, AMO
4487 Regularisation des dettes de l Etat
4501 Provisions pour litiges
5141 Banques (Solde debiteur)
5161 Caisse
6111 Achats de marchandises
6121 Achats de matieres premieres
6122 Achats de matieres consommables
6124 Achats de materiel et outillage
6125 Achats de materiel de bureau
6131 Locations et charges locatives
6133 Entretien et reparations
6134 Primes d assurance
6141 Etudes, recherches et documentation
6142 Transport
6143 Deplacements, missions et receptions
6144 Publicite, publications et relations publiques
6145 Frais postaux et frais de telecommunications
6147 Services bancaires
6148 Divers
6161 Impots et taxes directs
6165 Taxes indirectes
6171 Remunerations du personnel
6174 Charges sociales
6181 Dotations aux amortissements
6182 Dotations aux provisions
6311 Charges d interets
6386 Pertes de change
6411 Impots sur les benefices
6586 Pertes sur creances irrecouvrables
7111 Ventes de marchandises
7121 Ventes de produits finis
7122 Ventes de produits intermediaires
7124 Ventes de services produits
7129 RRR accordes par l entreprise
7161 Subventions d exploitation
7181 Profits sur operations faites en commun
7381 Interets et produits assimiles
7386 Gains de change
7512 Revenus des immeubles non affectes a l exploitation
7581 Penalites et amendes diverses recues
7582 Subventions d equilibre
7588 Autres produits non courants
7612 Produits des participations
`;

export interface CategorizedTransaction {
  ligne: number;
  nature_operation: string;
  code_comptable: string;
  intitule_compte: string;
  categorie: string;
  confiance: "high" | "medium" | "low";
}

export async function categorizeTransactions(
  transactions: Array<{
    ligne: number;
    nature_operation: string;
    montant_debit: number | null;
    montant_credit: number | null;
  }>,
  nomSociete: string
): Promise<CategorizedTransaction[]> {
  const client = getClient();

  const txText = transactions
    .map(
      (t) =>
        `Ligne ${t.ligne}: "${t.nature_operation}" | Debit:${t.montant_debit ?? 0} | Credit:${t.montant_credit ?? 0}`
    )
    .join("\n");

  const prompt = `Tu es un expert comptable marocain. Categorise chaque transaction bancaire selon le plan comptable marocain (PCM).

PLAN COMPTABLE MAROCAIN:
${PLAN_COMPTABLE_MAROCAIN}

INSTRUCTIONS:
- Pour CHAQUE transaction, retourne: ligne, code_comptable, intitule_compte, categorie (ACHAT/VENTE/CHARGE/PRODUIT/FINANCE/IMMOBILISATION/AUTRE), confiance
- Les codes les plus frequents:
  * Paiement CB restaurant/deplacement → 6143
  * CNSS/cotisations sociales → 6174 ou 4465
  * Salaire/personnel → 6171
  * Internet/telephone → 6145
  * Impots/taxes → 6161
  * Services bancaires/frais → 6147
  * Achat marchandises → 6111
  * Vente marchandises → 7111
  * Location/loyer → 6131
  * Publicite → 6144
  * Carburant/transport → 6142
  * Materiel informatique → 2355
  * Versement/remise cheque client → 3421 (client)
  * Paiement fournisseur → 4411 (fournisseur)
  * Virement emis divers → 5141
  * Virement recu client → 3421
- Si une operation contient le nom d une societe fournisseur/client, c est probablement 6111 (achat) ou 7111 (vente)
- Si montant credit avec VIREMENT RECU → 3421 Clients
- Retourne UNIQUEMENT un JSON array

TRANSACTIONS:
${txText}

Nom de la societe: ${nomSociete}

Reponds UNIQUEMENT avec un JSON array valide:
[{"ligne":1,"code_comptable":"6145","intitule_compte":"Frais postaux et telecommunications","categorie":"CHARGE","confiance":"high"},...]`;

  const result = await client.models.generateContent({
    model: "gemini-2.0-flash",
    contents: prompt,
    config: {
      responseMimeType: "application/json",
    },
  });

  try {
    const text = result.text || "[]";
    return JSON.parse(text) as CategorizedTransaction[];
  } catch {
    return transactions.map((t) => ({
      ligne: t.ligne,
      nature_operation: t.nature_operation,
      code_comptable: "",
      intitule_compte: "",
      categorie: "AUTRE",
      confiance: "low" as const,
    }));
  }
}

export interface ExtractedInvoice {
  type: "client" | "fournisseur" | "acompte";
  numero_facture: string;
  date_facture: string;
  date_paiement: string | null;
  nom_client_fournisseur: string;
  ice_client_fournisseur: string | null;
  identifiant_fiscal_frs: string | null;
  designation: string;
  montant_ht: number;
  taux_tva: number;
  montant_tva: number;
  montant_ttc: number;
  mode_paiement: string | null;
  est_acompte: boolean;
}

export async function extractInvoice(
  fileBuffer: Buffer,
  mimeType: string,
  nomSocieteDossier: string
): Promise<ExtractedInvoice> {
  const client = getClient();

  const prompt = `Tu es un expert comptable marocain. Extrais toutes les donnees de cette facture.

INSTRUCTIONS:
1. Determine si c est une FACTURE CLIENT (vendue PAR la societe ${nomSocieteDossier}) ou FACTURE FOURNISSEUR (achetee PAR la societe ${nomSocieteDossier})
2. Si le document est un ACOMPTE/VERSEMENT, marque est_acompte: true
3. Extrais toutes les donnees pertinentes
4. Le type doit etre "client" si ${nomSocieteDossier} est le VENDEUR, "fournisseur" si c est l ACHETEUR

Reponds UNIQUEMENT avec ce JSON:
{
  "type": "client" | "fournisseur" | "acompte",
  "numero_facture": "...",
  "date_facture": "YYYY-MM-DD",
  "date_paiement": "YYYY-MM-DD" | null,
  "nom_client_fournisseur": "...",
  "ice_client_fournisseur": "..." | null,
  "identifiant_fiscal_frs": "..." | null,
  "designation": "...",
  "montant_ht": 0.00,
  "taux_tva": 20,
  "montant_tva": 0.00,
  "montant_ttc": 0.00,
  "mode_paiement": "..." | null,
  "est_acompte": false
}`;

  const result = await client.models.generateContent({
    model: "gemini-2.0-flash",
    contents: [
      { text: prompt },
      {
        inlineData: {
          data: fileBuffer.toString("base64"),
          mimeType,
        },
      },
    ],
    config: {
      responseMimeType: "application/json",
    },
  });

  try {
    const text = result.text || "{}";
    return JSON.parse(text) as ExtractedInvoice;
  } catch {
    throw new Error("Failed to parse invoice data from Gemini");
  }
}

export interface MatchingResult {
  transaction_ligne: number;
  facture_id: number;
  confiance: "high" | "medium" | "low";
  criteres: string[];
  explication: string;
}

export async function matchTransactionsWithInvoices(
  transactions: Array<{
    ligne: number;
    nature_operation: string;
    date_operation: string;
    montant_debit: number | null;
    montant_credit: number | null;
  }>,
  factures: Array<{
    id: number;
    type: string;
    numero_facture: string;
    date_facture: string;
    nom_client_fournisseur: string;
    montant_ttc: number;
    designation: string;
  }>,
  nomSociete: string
): Promise<MatchingResult[]> {
  const client = getClient();

  const txText = transactions
    .map(
      (t) =>
        `TX${t.ligne}: "${t.nature_operation}" | Date:${t.date_operation} | Debit:${t.montant_debit ?? 0} | Credit:${t.montant_credit ?? 0}`
    )
    .join("\n");

  const facText = factures
    .map(
      (f) =>
        `FAC${f.id}: N ${f.numero_facture} | ${f.nom_client_fournisseur} | Date:${f.date_facture} | TTC:${f.montant_ttc} | Type:${f.type} | Designation:${f.designation}`
    )
    .join("\n");

  const prompt = `Tu es un expert comptable marocain. Associe chaque transaction bancaire avec sa facture correspondante.

CRITERES DE MATCHING:
- Montant TTC identique ou tres proche
- Date proche (plus ou moins 5 jours pour virements, plus ou moins 15 jours pour cheques)
- Nom de la societe present dans le libelle de la transaction
- Numero de facture present dans la reference
- Type coherent: debit = achat/fournisseur, credit = vente/client

Pour ACHAT/DEBIT cherche parmi factures FOURNISSEUR
Pour VENTE/CREDIT cherche parmi factures CLIENT

Si une transaction ne correspond a AUCUNE facture, ne la retourne pas.

TRANSACTIONS:
${txText}

FACTURES:
${facText}

Nom de la societe: ${nomSociete}

Reponds UNIQUEMENT avec JSON array des matchs:
[{"transaction_ligne":1,"facture_id":5,"confiance":"high","criteres":["montant_ttc_identique","date_proche","nom_societe"],"explication":"Montant TTC identique"},...]`;

  const result = await client.models.generateContent({
    model: "gemini-2.0-flash",
    contents: prompt,
    config: {
      responseMimeType: "application/json",
    },
  });

  try {
    const text = result.text || "[]";
    return JSON.parse(text) as MatchingResult[];
  } catch {
    return [];
  }
}
