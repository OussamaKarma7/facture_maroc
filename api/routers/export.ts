import { z } from "zod";
import { createRouter, publicQuery } from "../middleware";
import { getDb } from "../queries/connection";
import {
  transactions,
  factures,
  matchings,
  societes,
} from "@db/schema";
import { eq } from "drizzle-orm";
import * as XLSX from "xlsx";

export const exportRouter = createRouter({
  // ─── Export EDI (DGI TVA) ───
  generateEdi: publicQuery
    .input(
      z.object({
        societeId: z.number(),
        releveId: z.number(),
        annee: z.number(),
        mois: z.number(),
      })
    )
    .mutation(async ({ input }) => {
      try {
        const db = getDb();

        // Get societe
        const soc = await db
          .select()
          .from(societes)
          .where(eq(societes.id, input.societeId));
        const societe = soc[0];
        if (!societe) {
          return { success: false, error: "Societe not found" };
        }

        // Get matched transactions with factures
        const txs = await db
          .select()
          .from(transactions)
          .where(eq(transactions.releveId, input.releveId));

        // Build EDI data
        const ediData: any[] = [];
        let ordre = 1;

        for (const tx of txs) {
          // Check if there's a matching
          const m = await db
            .select()
            .from(matchings)
            .where(eq(matchings.transactionId, tx.id));

          let fac = null;
          if (m.length) {
            const f = await db
              .select()
              .from(factures)
              .where(eq(factures.id, m[0].factureId));
            fac = f[0] || null;
          }

          // Only include if we have a facture with TVA
          if (fac && fac.montantHt && parseFloat(fac.montantHt) > 0) {
            const montantHt = parseFloat(fac.montantHt);
            const montantTva = fac.montantTva
              ? parseFloat(fac.montantTva)
              : 0;
            const montantTtc = fac.montantTtc
              ? parseFloat(fac.montantTtc)
              : montantHt + montantTva;
            const tauxTva = fac.tauxTva ? parseFloat(fac.tauxTva) : 20;

            ediData.push({
              OR: ordre++,
              FACT_NUM: fac.numeroFacture || `TX${tx.ligne}`,
              DESIGNATION: fac.designation || tx.natureOperation || "",
              M_HT: montantHt,
              TVA: montantTva,
              M_TTC: montantTtc,
              IF: fac.identifiantFiscalFrs || "",
              LIB_FRSS: fac.nomClientFournisseur || "",
              ICE_FRS: fac.iceClientFournisseur || "",
              TAUX: tauxTva,
              ID_PAIE: 5, // Default payment method
              DATE_PAIE: fac.datePaiement
                ? fac.datePaiement.toISOString().split("T")[0]
                : tx.dateOperation
                  ? tx.dateOperation.toISOString().split("T")[0]
                  : "",
              DATE_FAC: fac.dateFacture
                ? fac.dateFacture.toISOString().split("T")[0]
                : "",
            });
          }
        }

        // Create workbook
        const ws = XLSX.utils.json_to_sheet(ediData);

        // Add headers
        const headerRow = {
          RAISON_SOCIAL: societe.raisonSociale || societe.nom,
          ID_FISCAL: societe.identifiantFiscal || "",
          ANNEE: input.annee,
          PERIODE: input.mois,
          REGIME: 1,
        };

        // Prepend header info
        XLSX.utils.sheet_add_aoa(ws, [
          ["RAISON SOCIAL", headerRow.RAISON_SOCIAL],
          ["ID_FISCAL", headerRow.ID_FISCAL],
          ["ANNEE", headerRow.ANNEE],
          ["PERIODE (Mois)", headerRow.PERIODE],
          ["REGIME (Encais-1)", headerRow.REGIME],
          [],
        ]);

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Releve Deductions");

        const buffer = XLSX.write(wb, {
          type: "buffer",
          bookType: "xlsx",
        });

        return {
          success: true,
          data: buffer.toString("base64"),
          filename: `EDI_TVA_${societe.nom}_${input.annee}_${input.mois}.xlsx`,
          count: ediData.length,
        };
      } catch (error: any) {
        console.error("EDI export error:", error);
        return {
          success: false,
          error: error.message || "Export failed",
        };
      }
    }),

  // ─── Export Sage (Journal Banque) ───
  generateSage: publicQuery
    .input(z.object({ releveId: z.number() }))
    .mutation(async ({ input }) => {
      try {
        const db = getDb();

        const txs = await db
          .select()
          .from(transactions)
          .where(eq(transactions.releveId, input.releveId));

        // Build Sage journal data
        const sageData = txs.map((tx) => ({
          JOURNAL: "BQ", // Banque
          DATE: tx.dateOperation
            ? tx.dateOperation.toISOString().split("T")[0]
            : "",
          NUM_PIECE: tx.reference || `L${tx.ligne}`,
          NUM_COMPTE: tx.codeComptable || "5141",
          LIBELLE: tx.natureOperation || "",
          DEBIT: tx.montantDebit || 0,
          CREDIT: tx.montantCredit || 0,
          CODE_COMPTABLE_TIERS:
            tx.categorieComptable === "ACHAT"
              ? "4411"
              : tx.categorieComptable === "VENTE"
                ? "3421"
                : "",
          NOM_TIERS: "",
          MODE_PAIEMENT: tx.typeOperation?.includes("CB")
            ? "CB"
            : tx.typeOperation?.includes("VIR")
              ? "Virement"
              : tx.typeOperation?.includes("CHEQUE")
                ? "Cheque"
                : "",
        }));

        const ws = XLSX.utils.json_to_sheet(sageData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Journal Banque");

        const buffer = XLSX.write(wb, {
          type: "buffer",
          bookType: "xlsx",
        });

        return {
          success: true,
          data: buffer.toString("base64"),
          filename: `SAGE_Journal_BQ_${input.releveId}.xlsx`,
          count: sageData.length,
        };
      } catch (error: any) {
        console.error("Sage export error:", error);
        return {
          success: false,
          error: error.message || "Export failed",
        };
      }
    }),

  // ─── Export transactions CSV ───
  generateCsv: publicQuery
    .input(z.object({ releveId: z.number() }))
    .mutation(async ({ input }) => {
      try {
        const db = getDb();
        const txs = await db
          .select()
          .from(transactions)
          .where(eq(transactions.releveId, input.releveId));

        const csvData = txs.map((tx) => ({
          Ligne: tx.ligne,
          "Date Operation": tx.dateOperation
            ? tx.dateOperation.toISOString().split("T")[0]
            : "",
          "Date Valeur": tx.dateValeur
            ? tx.dateValeur.toISOString().split("T")[0]
            : "",
          Reference: tx.reference || "",
          "Nature Operation": tx.natureOperation || "",
          "Code Comptable": tx.codeComptable || "",
          "Intitule Compte": tx.intituleCompte || "",
          Categorie: tx.categorieComptable || "",
          Debit: tx.montantDebit || 0,
          Credit: tx.montantCredit || 0,
        }));

        const ws = XLSX.utils.json_to_sheet(csvData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Transactions");

        const buffer = XLSX.write(wb, {
          type: "buffer",
          bookType: "xlsx",
        });

        return {
          success: true,
          data: buffer.toString("base64"),
          filename: `Transactions_${input.releveId}.xlsx`,
        };
      } catch (error: any) {
        return {
          success: false,
          error: error.message || "Export failed",
        };
      }
    }),
});
