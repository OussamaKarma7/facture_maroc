import { z } from "zod";
import { createRouter, publicQuery } from "../middleware";
import { getDb } from "../queries/connection";
import { matchings, transactions, factures } from "@db/schema";
import { eq } from "drizzle-orm";
import { matchTransactionsWithInvoices } from "../services/gemini";

export const matchingRouter = createRouter({
  listByReleve: publicQuery
    .input(z.object({ releveId: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const txs = await db
        .select()
        .from(transactions)
        .where(eq(transactions.releveId, input.releveId));

      const results = [];
      for (const tx of txs) {
        const m = await db
          .select()
          .from(matchings)
          .where(eq(matchings.transactionId, tx.id));
        if (m.length) {
          const f = await db
            .select()
            .from(factures)
            .where(eq(factures.id, m[0].factureId));
          results.push({
            ...m[0],
            transaction: tx,
            facture: f[0] || null,
          });
        }
      }
      return results;
    }),

  create: publicQuery
    .input(
      z.object({
        transactionId: z.number(),
        factureId: z.number(),
        confiance: z.string().optional(),
        statut: z.enum(["auto", "manuel", "verifie", "rejete"]).optional(),
        criteres: z.array(z.string()).optional(),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const result = await db.insert(matchings).values(input);
      return { id: Number(result[0].insertId) };
    }),

  updateStatut: publicQuery
    .input(
      z.object({
        id: z.number(),
        statut: z.enum(["auto", "manuel", "verifie", "rejete"]),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      await db
        .update(matchings)
        .set({ statut: input.statut })
        .where(eq(matchings.id, input.id));
      return { success: true };
    }),

  delete: publicQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db.delete(matchings).where(eq(matchings.id, input.id));
      return { success: true };
    }),

  // ─── Auto-match with Gemini ───
  autoMatch: publicQuery
    .input(z.object({ releveId: z.number(), societeId: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      try {
        // Get transactions for this releve
        const txs = await db
          .select()
          .from(transactions)
          .where(eq(transactions.releveId, input.releveId));

        if (!txs.length) {
          return { success: false, error: "No transactions found" };
        }

        // Get all factures for this societe
        const facs = await db
          .select()
          .from(factures)
          .where(eq(factures.societeId, input.societeId));

        if (!facs.length) {
          return {
            success: false,
            error: "No invoices found for this company",
          };
        }

        // Get societe name
        const { societes } = await import("@db/schema");
        const socResults = await db
          .select()
          .from(societes)
          .where(eq(societes.id, input.societeId));
        const nomSociete = socResults[0]?.nom || "";

        // Prepare data for Gemini
        const txForGemini = txs.map((tx) => ({
          ligne: tx.ligne,
          nature_operation: tx.natureOperation || "",
          date_operation: tx.dateOperation
            ? tx.dateOperation.toISOString().split("T")[0]
            : "",
          montant_debit: tx.montantDebit ? parseFloat(tx.montantDebit) : null,
          montant_credit: tx.montantCredit
            ? parseFloat(tx.montantCredit)
            : null,
        }));

        const facForGemini = facs.map((f) => ({
          id: f.id,
          type: f.type,
          numero_facture: f.numeroFacture || "",
          date_facture: f.dateFacture
            ? f.dateFacture.toISOString().split("T")[0]
            : "",
          nom_client_fournisseur: f.nomClientFournisseur || "",
          montant_ttc: f.montantTtc ? parseFloat(f.montantTtc) : 0,
          designation: f.designation || "",
        }));

        // Call Gemini for matching
        const matchResults = await matchTransactionsWithInvoices(
          txForGemini,
          facForGemini,
          nomSociete
        );

        // Save matchings
        const matchingsCreated = [];
        for (const match of matchResults) {
          // Find the transaction DB id by ligne
          const txRecord = txs.find(
            (t) => t.ligne === match.transaction_ligne
          );
          if (!txRecord) continue;

          // Delete existing matching for this transaction
          await db
            .delete(matchings)
            .where(eq(matchings.transactionId, txRecord.id));

          const result = await db.insert(matchings).values({
            transactionId: txRecord.id,
            factureId: match.facture_id,
            confiance: match.confiance,
            statut: "auto",
            criteres: match.criteres as any,
          });

          matchingsCreated.push({
            id: Number(result[0].insertId),
            ...match,
          });
        }

        return {
          success: true,
          matchingsCreated: matchingsCreated.length,
          matchings: matchingsCreated,
          unmatchedCount: txs.length - matchingsCreated.length,
        };
      } catch (error: any) {
        console.error("Auto-match error:", error);
        return {
          success: false,
          error: error.message || "Matching failed",
        };
      }
    }),
});
