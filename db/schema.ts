import {
  mysqlTable,
  serial,
  varchar,
  text,
  timestamp,
  decimal,
  int,
  bigint,
  json,
  date,
  mysqlEnum,
} from "drizzle-orm/mysql-core";

// ─── Sociétés (dossiers clients du cabinet comptable) ───
export const societes = mysqlTable("societes", {
  id: serial("id").primaryKey(),
  nom: varchar("nom", { length: 255 }).notNull(),
  raisonSociale: varchar("raison_sociale", { length: 255 }).notNull(),
  ice: varchar("ice", { length: 20 }),
  identifiantFiscal: varchar("identifiant_fiscal", { length: 20 }),
  rc: varchar("rc", { length: 50 }),
  cnss: varchar("cnss", { length: 50 }),
  adresse: text("adresse"),
  ville: varchar("ville", { length: 100 }),
  telephone: varchar("telephone", { length: 50 }),
  email: varchar("email", { length: 100 }),
  typeSociete: varchar("type_societe", { length: 20 }), // SARL, SA, SARL AU...
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow().onUpdateNow(),
});

// ─── Factures (clients et fournisseurs) ───
export const factures = mysqlTable("factures", {
  id: serial("id").primaryKey(),
  societeId: bigint("societe_id", { mode: "number", unsigned: true })
    .notNull(),
  type: mysqlEnum("type", ["client", "fournisseur", "acompte"]).notNull(),
  numeroFacture: varchar("numero_facture", { length: 100 }).notNull(),
  designation: text("designation"),
  nomClientFournisseur: varchar("nom_client_fournisseur", { length: 255 }),
  iceClientFournisseur: varchar("ice_client_fournisseur", { length: 20 }),
  identifiantFiscalFrs: varchar("identifiant_fiscal_frs", { length: 20 }),
  montantHt: decimal("montant_ht", { precision: 14, scale: 2 }),
  montantTva: decimal("montant_tva", { precision: 14, scale: 2 }),
  tauxTva: decimal("taux_tva", { precision: 5, scale: 2 }),
  montantTtc: decimal("montant_ttc", { precision: 14, scale: 2 }),
  dateFacture: date("date_facture"),
  datePaiement: date("date_paiement"),
  modePaiement: varchar("mode_paiement", { length: 50 }),
  fichierPath: varchar("fichier_path", { length: 500 }),
  extractedData: json("extracted_data"), // Données brutes extraites par Gemini
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ─── Relevés Bancaires ───
export const relevesBancaires = mysqlTable("releves_bancaires", {
  id: serial("id").primaryKey(),
  societeId: bigint("societe_id", { mode: "number", unsigned: true })
    .notNull(),
  banque: varchar("banque", { length: 100 }).notNull(), // Banque Populaire, Attijariwafa, CIH, BMCE, BMCI...
  rib: varchar("rib", { length: 50 }),
  codeBanque: varchar("code_banque", { length: 10 }),
  codeLocalite: varchar("code_localite", { length: 10 }),
  numeroCompte: varchar("numero_compte", { length: 50 }),
  cleRib: varchar("cle_rib", { length: 5 }),
  titulaire: varchar("titulaire", { length: 255 }),
  nomAgence: varchar("nom_agence", { length: 255 }),
  dateDebut: date("date_debut"),
  dateFin: date("date_fin"),
  soldeInitial: decimal("solde_initial", { precision: 14, scale: 2 }),
  soldeFinal: decimal("solde_final", { precision: 14, scale: 2 }),
  totalDebits: decimal("total_debits", { precision: 14, scale: 2 }),
  totalCredits: decimal("total_credits", { precision: 14, scale: 2 }),
  fichierPath: varchar("fichier_path", { length: 500 }),
  rawText: text("raw_text"), // Texte OCR brut
  status: mysqlEnum("status", ["pending", "processing", "completed", "error"])
    .notNull()
    .default("pending"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ─── Transactions Bancaires ───
export const transactions = mysqlTable("transactions", {
  id: serial("id").primaryKey(),
  releveId: bigint("releve_id", { mode: "number", unsigned: true })
    .notNull(),
  ligne: int("ligne").notNull(),
  dateOperation: date("date_operation"),
  dateValeur: date("date_valeur"),
  reference: varchar("reference", { length: 50 }),
  natureOperation: text("nature_operation"),
  typeOperation: varchar("type_operation", { length: 100 }),
  operationCategorie: varchar("operation_categorie", { length: 50 }),
  montantDebit: decimal("montant_debit", { precision: 14, scale: 2 }),
  montantCredit: decimal("montant_credit", { precision: 14, scale: 2 }),
  // ─── Catégorisation comptable (par Gemini) ───
  codeComptable: varchar("code_comptable", { length: 20 }),
  intituleCompte: varchar("intitule_compte", { length: 255 }),
  categorieComptable: varchar("categorie_comptable", { length: 100 }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ─── Matchings Transaction ↔ Facture ───
export const matchings = mysqlTable("matchings", {
  id: serial("id").primaryKey(),
  transactionId: bigint("transaction_id", { mode: "number", unsigned: true })
    .notNull(),
  factureId: bigint("facture_id", { mode: "number", unsigned: true })
    .notNull(),
  confiance: varchar("confiance", { length: 20 }), // high, medium, low
  statut: mysqlEnum("statut", ["auto", "manuel", "verifie", "rejete"])
    .notNull()
    .default("auto"),
  criteres: json("criteres"), // Quels critères ont matché
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ─── Plan Comptable Marocain (référence) ───
export const planComptable = mysqlTable("plan_comptable", {
  id: serial("id").primaryKey(),
  code: varchar("code", { length: 20 }).notNull(),
  intitule: varchar("intitule", { length: 255 }).notNull(),
  usageType: text("usage_type"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});
