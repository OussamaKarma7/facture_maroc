import { getDb } from "api/queries/connection";
import { planComptable } from "./schema";

const PLAN_COMPTABLE_DATA = [
  { code: "1111", intitule: "Capital social", usageType: "Constitution de l'entreprise" },
  { code: "1121", intitule: "Resultats reportes", usageType: "Benefices non distribues" },
  { code: "1481", intitule: "Emprunts aupres des etablissements de credit", usageType: "Financement externe" },
  { code: "1486", intitule: "Fournisseurs d'immobilisations", usageType: "Dettes fournisseurs d'actifs" },
  { code: "2111", intitule: "Frais de constitution", usageType: "Charges d'installation" },
  { code: "2113", intitule: "Frais de prospection", usageType: "Developpement commercial" },
  { code: "2130", intitule: "Brevets, marques, droits et valeurs similaires", usageType: "Propriete intellectuelle" },
  { code: "2151", intitule: "Logiciels informatiques", usageType: "Logiciels et licences" },
  { code: "2210", intitule: "Terrains", usageType: "Biens immobiliers" },
  { code: "2220", intitule: "Constructions", usageType: "Batiments et locaux" },
  { code: "2332", intitule: "Materiel et outillage", usageType: "Immobilisations techniques" },
  { code: "2340", intitule: "Materiel de transport", usageType: "Vehicules de l'entreprise" },
  { code: "2355", intitule: "Materiel informatique", usageType: "Ordinateurs, serveurs, etc." },
  { code: "2356", intitule: "Materiel de bureautique", usageType: "Imprimantes, scanners" },
  { code: "2411", intitule: "Droits de mutation", usageType: "Frais d'acquisition" },
  { code: "2833", intitule: "Amortissement des installations techniques", usageType: "Amortissements" },
  { code: "2834", intitule: "Amortissement du materiel de transport", usageType: "Amortissements" },
  { code: "2835", intitule: "Amortissement du materiel de bureau et informatique", usageType: "Amortissements" },
  { code: "3111", intitule: "Marchandises", usageType: "Stocks en magasin" },
  { code: "3121", intitule: "Matieres premieres", usageType: "Pour la production" },
  { code: "3151", intitule: "Produits finis", usageType: "Stocks produits finis" },
  { code: "3421", intitule: "Clients", usageType: "Creances sur les ventes" },
  { code: "3424", intitule: "Clients - effets a recevoir", usageType: "Effets de commerce clients" },
  { code: "3455", intitule: "Etat - TVA recuperable sur charges", usageType: "TVA sur achats et immo" },
  { code: "3487", intitule: "Regularisation des creances sur l'Etat", usageType: "Regularisations fiscales" },
  { code: "4411", intitule: "Fournisseurs", usageType: "Dettes sur achats de biens/services" },
  { code: "4421", intitule: "Fournisseurs - effets a payer", usageType: "Effets a payer" },
  { code: "4455", intitule: "Etat - TVA facturee", usageType: "TVA collectee sur les ventes" },
  { code: "4456", intitule: "Etat - TVA due (mouvements periodiques TVA)", usageType: "TVA a payer" },
  { code: "4465", intitule: "Organismes sociaux - CNSS, AMO", usageType: "Cotisations sociales" },
  { code: "4487", intitule: "Regularisation des dettes de l'Etat", usageType: "Regularisations fiscales" },
  { code: "4501", intitule: "Provisions pour litiges", usageType: "Risques et charges" },
  { code: "5141", intitule: "Banques (Solde debiteur)", usageType: "Compte bancaire principal" },
  { code: "5161", intitule: "Caisse", usageType: "Operations en especes" },
  { code: "6111", intitule: "Achats de marchandises", usageType: "Achat destine a la revente" },
  { code: "6121", intitule: "Achats de matieres premieres", usageType: "Pour la production" },
  { code: "6122", intitule: "Achats de matieres consommables", usageType: "Fournitures, consommables" },
  { code: "6124", intitule: "Achats de materiel et outillage", usageType: "Petit outillage" },
  { code: "6125", intitule: "Achats de materiel de bureau", usageType: "Fournitures de bureau" },
  { code: "6131", intitule: "Locations et charges locatives", usageType: "Loyers des bureaux" },
  { code: "6133", intitule: "Entretien et reparations", usageType: "Maintenance technique" },
  { code: "6134", intitule: "Primes d'assurance", usageType: "Assurances entreprise" },
  { code: "6141", intitule: "Etudes, recherches et documentation", usageType: "Services techniques / Honoraires" },
  { code: "6142", intitule: "Transport", usageType: "Frais de transport, livraison" },
  { code: "6143", intitule: "Deplacements, missions et receptions", usageType: "Restaurant, voyage, mission" },
  { code: "6144", intitule: "Publicite, publications et relations publiques", usageType: "Marketing" },
  { code: "6145", intitule: "Frais postaux et frais de telecommunications", usageType: "Internet, telephone, timbres" },
  { code: "6147", intitule: "Services bancaires", usageType: "Commissions et frais de tenue de compte" },
  { code: "6148", intitule: "Divers (frais de recrutement, cotisations syndicales...)", usageType: "Autres charges externes" },
  { code: "6161", intitule: "Impots et taxes directs", usageType: "Taxes locales ou professionnelles" },
  { code: "6165", intitule: "Taxes indirectes", usageType: "Timbres, vignettes" },
  { code: "6171", intitule: "Remunerations du personnel", usageType: "Salaires bruts" },
  { code: "6174", intitule: "Charges sociales", usageType: "CNSS, AMO, CIMR" },
  { code: "6181", intitule: "Dotations aux amortissements de l'exercice", usageType: "Amortissements" },
  { code: "6182", intitule: "Dotations aux provisions", usageType: "Provisions" },
  { code: "6311", intitule: "Charges d'interets", usageType: "Interets bancaires" },
  { code: "6386", intitule: "Pertes de change", usageType: "Ecarts de change" },
  { code: "6411", intitule: "Impots sur les benefices", usageType: "IS" },
  { code: "6586", intitule: "Pertes sur creances irrecouvrables", usageType: "Creances douteuses" },
  { code: "7111", intitule: "Ventes de marchandises", usageType: "Revenus principaux (negoce)" },
  { code: "7121", intitule: "Ventes de produits finis", usageType: "Revenus principaux (production)" },
  { code: "7122", intitule: "Ventes de produits intermediaires", usageType: "Revenus secondaires" },
  { code: "7124", intitule: "Ventes de services produits", usageType: "Prestations de services" },
  { code: "7129", intitule: "RRR accordes par l'entreprise", usageType: "Remises, rabais, ristournes" },
  { code: "7161", intitule: "Subventions d'exploitation", usageType: "Aides publiques" },
  { code: "7181", intitule: "Profits sur operations faites en commun", usageType: "Copropriete" },
  { code: "7381", intitule: "Interets et produits assimiles", usageType: "Produits financiers" },
  { code: "7386", intitule: "Gains de change", usageType: "Ecarts de change positifs" },
  { code: "7512", intitule: "Revenus des immeubles non affectes a l'exploitation", usageType: "Locations immobilieres" },
  { code: "7581", intitule: "Penalites et amendes diverses recues", usageType: "Indemnites recues" },
  { code: "7582", intitule: "Subventions d'equilibre", usageType: "Aides exceptionnelles" },
  { code: "7588", intitule: "Autres produits non courants", usageType: "Produits divers" },
  { code: "7612", intitule: "Produits des participations", usageType: "Dividendes" },
];

async function seed() {
  const db = getDb();
  console.log("Seeding plan comptable...");

  // Check if already seeded
  const existing = await db.select().from(planComptable).limit(1);
  if (existing.length > 0) {
    console.log("Plan comptable already seeded, skipping.");
    return;
  }

  // Insert in batches
  for (const item of PLAN_COMPTABLE_DATA) {
    await db.insert(planComptable).values(item);
  }

  console.log(`Seeded ${PLAN_COMPTABLE_DATA.length} plan comptable entries.`);
}

seed().catch(console.error);
