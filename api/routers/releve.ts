import { z } from "zod";
import { createRouter, publicQuery } from "../middleware";
import { getDb } from "../queries/connection";
import { relevesBancaires, transactions, societes } from "@db/schema";
import { eq, desc } from "drizzle-orm";
import { extractReleveWithPython } from "../services/extraction";
import { categorizeTransactions } from "../services/gemini";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";

export const releveRouter = createRouter({
  listBySociete: publicQuery
    .input(z.object({ societeId: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      return db
        .select()
        .from(relevesBancaires)
        .where(eq(relevesBancaires.societeId, input.societeId))
        .orderBy(desc(relevesBancaires.createdAt));
    }),

  getById: publicQuery
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const results = await db
        .select()
        .from(relevesBancaires)
        .where(eq(relevesBancaires.id, input.id));
      return results[0] || null;
    }),

  getTransactions: publicQuery
    .input(z.object({ releveId: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      return db
        .select()
        .from(transactions)
        .where(eq(transactions.releveId, input.releveId))
        .orderBy(transactions.ligne);
    }),

  delete: publicQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db
        .delete(transactions)
        .where(eq(transactions.releveId, input.id));
      await db
        .delete(relevesBancaires)
        .where(eq(relevesBancaires.id, input.id));
      return { success: true };
    }),

  // ─── Upload + extraction OCR + catégorisation Gemini ───
  uploadAndExtract: publicQuery
    .input(
      z.object({
        societeId: z.number(),
        base64: z.string(),
        filename: z.string(),
        bankHint: z.string().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      try {
        // Save file
        const uploadDir = join(process.cwd(), "uploads", "releves");
        await mkdir(uploadDir, { recursive: true });
        const filePath = join(uploadDir, `${Date.now()}_${input.filename}`);
        const buffer = Buffer.from(input.base64, "base64");
        await writeFile(filePath, buffer);

        // Get societe name
        const socResults = await db
          .select()
          .from(societes)
          .where(eq(societes.id, input.societeId));
        const nomSociete = socResults[0]?.nom || "";

        // Extract with Python OCR
        const parsed = await extractReleveWithPython(
          filePath,
          input.bankHint
        );

        if (parsed.error) {
          return {
            success: false,
            error: parsed.error,
            rawText: parsed._ocr_text_brut || "",
          };
        }

        // Save releve
        const releveResult = await db.insert(relevesBancaires).values({
          societeId: input.societeId,
          banque: parsed.banque?.nom || "Inconnue",
          rib: parsed.compte?.rib_complet || null,
          codeBanque: parsed.compte?.code_banque || null,
          codeLocalite: parsed.compte?.code_localite || null,
          numeroCompte: parsed.compte?.numero_principal || null,
          cleRib: parsed.compte?.cle_rib || null,
          titulaire: parsed.titulaire?.raison_sociale || null,
          nomAgence: parsed.banque?.nom_agence || null,
          dateDebut: parsed.soldes?.ancien_solde_date
            ? new Date(parsed.soldes.ancien_solde_date)
            : null,
          dateFin: parsed.releve?.date_arrete
            ? new Date(parsed.releve.date_arrete)
            : null,
          soldeInitial: parsed.soldes?.ancien_solde_montant?.toString() || null,
          soldeFinal: parsed.soldes?.solde_reporter?.toString() || null,
          totalDebits: parsed.soldes?.total_debits?.toString() || null,
          totalCredits: parsed.soldes?.total_credits?.toString() || null,
          fichierPath: filePath,
          rawText: parsed._ocr_text_brut || null,
          status: "completed",
        });

        const releveId = Number(releveResult[0].insertId);

        // Save transactions
        if (parsed.transactions?.length) {
          const txData = parsed.transactions.map((tx) => ({
            releveId,
            ligne: tx.ligne,
            dateOperation: tx.date_operation ? new Date(tx.date_operation) : null,
            dateValeur: tx.date_valeur ? new Date(tx.date_valeur) : null,
            reference: tx.reference || null,
            natureOperation: tx.nature_operation || null,
            typeOperation: tx.type_operation || null,
            operationCategorie: tx.operation_categorie || null,
            montantDebit: tx.montant_debit?.toString() || null,
            montantCredit: tx.montant_credit?.toString() || null,
          }));

          // Batch insert in chunks of 50
          for (let i = 0; i < txData.length; i += 50) {
            await db.insert(transactions).values(txData.slice(i, i + 50));
          }
        }

        // ─── Categorization with Gemini ───
        let categorized: any[] = [];
        if (parsed.transactions?.length && parsed.transactions.length <= 100) {
          try {
            const txForGemini = parsed.transactions.map((tx) => ({
              ligne: tx.ligne,
              nature_operation: tx.nature_operation || "",
              montant_debit: tx.montant_debit,
              montant_credit: tx.montant_credit,
            }));
            categorized = await categorizeTransactions(
              txForGemini,
              nomSociete
            );

            // Update transactions with accounting codes
            for (const cat of categorized) {
              await db
                .update(transactions)
                .set({
                  codeComptable: cat.code_comptable,
                  intituleCompte: cat.intitule_compte,
                  categorieComptable: cat.categorie,
                })
                .where(
                  eq(transactions.releveId, releveId) &&
                    eq(transactions.ligne, cat.ligne)
                );
            }
          } catch (catErr) {
            console.error("Categorization error:", catErr);
          }
        }

        return {
          success: true,
          releveId,
          nbTransactions: parsed.transactions?.length || 0,
          banque: parsed.banque?.nom,
          titulaire: parsed.titulaire?.raison_sociale,
          soldeInitial: parsed.soldes?.ancien_solde_montant,
          soldeFinal: parsed.soldes?.solde_reporter,
          verificationOk: parsed.soldes?.verification_ok,
          categorized,
        };
      } catch (error: any) {
        console.error("Releve extraction error:", error);
        return {
          success: false,
          error: error.message || "Extraction failed",
        };
      }
    }),
});
