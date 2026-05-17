import { z } from "zod";
import { createRouter, publicQuery } from "../middleware";
import { getDb } from "../queries/connection";
import { factures, societes } from "@db/schema";
import { eq, and, desc } from "drizzle-orm";
import { extractInvoice } from "../services/gemini";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";

export const factureRouter = createRouter({
  listBySociete: publicQuery
    .input(z.object({ societeId: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      return db
        .select()
        .from(factures)
        .where(eq(factures.societeId, input.societeId))
        .orderBy(desc(factures.createdAt));
    }),

  listBySocieteAndType: publicQuery
    .input(z.object({ societeId: z.number(), type: z.string() }))
    .query(async ({ input }) => {
      const db = getDb();
      return db
        .select()
        .from(factures)
        .where(
          and(
            eq(factures.societeId, input.societeId),
            eq(factures.type, input.type as "client" | "fournisseur" | "acompte")
          )
        )
        .orderBy(desc(factures.createdAt));
    }),

  getById: publicQuery
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const results = await db
        .select()
        .from(factures)
        .where(eq(factures.id, input.id));
      return results[0] || null;
    }),

  create: publicQuery
    .input(
      z.object({
        societeId: z.number(),
        type: z.enum(["client", "fournisseur", "acompte"]),
        numeroFacture: z.string(),
        designation: z.string().optional(),
        nomClientFournisseur: z.string().optional(),
        iceClientFournisseur: z.string().optional(),
        identifiantFiscalFrs: z.string().optional(),
        montantHt: z.number().optional(),
        montantTva: z.number().optional(),
        tauxTva: z.number().optional(),
        montantTtc: z.number().optional(),
        dateFacture: z.string().optional(),
        datePaiement: z.string().optional(),
        modePaiement: z.string().optional(),
        fichierPath: z.string().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const result = await db.insert(factures).values({
        ...input,
        dateFacture: input.dateFacture ? new Date(input.dateFacture) : null,
        datePaiement: input.datePaiement ? new Date(input.datePaiement) : null,
      } as any);
      return { id: Number(result[0].insertId) };
    }),

  update: publicQuery
    .input(
      z.object({
        id: z.number(),
        type: z.enum(["client", "fournisseur", "acompte"]).optional(),
        numeroFacture: z.string().optional(),
        designation: z.string().optional(),
        nomClientFournisseur: z.string().optional(),
        iceClientFournisseur: z.string().optional(),
        identifiantFiscalFrs: z.string().optional(),
        montantHt: z.number().optional(),
        montantTva: z.number().optional(),
        tauxTva: z.number().optional(),
        montantTtc: z.number().optional(),
        dateFacture: z.string().optional(),
        datePaiement: z.string().optional(),
        modePaiement: z.string().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const { id, ...data } = input;
      const db = getDb();
      await db.update(factures).set(data as any).where(eq(factures.id, id));
      return { success: true };
    }),

  delete: publicQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db.delete(factures).where(eq(factures.id, input.id));
      return { success: true };
    }),

  // ─── Upload + extraction Gemini ───
  uploadAndExtract: publicQuery
    .input(
      z.object({
        societeId: z.number(),
        type: z.enum(["client", "fournisseur", "acompte"]).optional(),
        base64: z.string(),
        filename: z.string(),
        mimeType: z.string(),
      })
    )
    .mutation(async ({ input }) => {
      try {
        // Get societe name
        const db = getDb();
        const socResults = await db
          .select()
          .from(societes)
          .where(eq(societes.id, input.societeId));
        const nomSociete = socResults[0]?.nom || "";

        // Save file
        const uploadDir = join(process.cwd(), "uploads", "factures");
        await mkdir(uploadDir, { recursive: true });
        const filePath = join(uploadDir, `${Date.now()}_${input.filename}`);
        const buffer = Buffer.from(input.base64, "base64");
        await writeFile(filePath, buffer);

        // Extract with Gemini
        const extracted = await extractInvoice(buffer, input.mimeType, nomSociete);

        // Override type if specified
        if (input.type) {
          extracted.type = input.type;
        }

        // Save to DB
        const result = await db.insert(factures).values({
          societeId: input.societeId,
          type: extracted.type,
          numeroFacture: extracted.numero_facture,
          designation: extracted.designation,
          nomClientFournisseur: extracted.nom_client_fournisseur,
          iceClientFournisseur: extracted.ice_client_fournisseur,
          identifiantFiscalFrs: extracted.identifiant_fiscal_frs,
          montantHt: extracted.montant_ht,
          montantTva: extracted.montant_tva,
          tauxTva: extracted.taux_tva,
          montantTtc: extracted.montant_ttc,
          dateFacture: extracted.date_facture ? new Date(extracted.date_facture) : null,
          datePaiement: extracted.date_paiement ? new Date(extracted.date_paiement) : null,
          modePaiement: extracted.mode_paiement,
          fichierPath: filePath,
          estAcompte: extracted.est_acompte ? 1 : 0,
          extractedData: extracted as any,
        } as any);

        return {
          success: true,
          id: Number(result[0].insertId),
          extracted,
        };
      } catch (error: any) {
        return {
          success: false,
          error: error.message || "Extraction failed",
        };
      }
    }),
});
