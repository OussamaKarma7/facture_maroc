import { z } from "zod";
import { createRouter, publicQuery } from "../middleware";
import { getDb } from "../queries/connection";
import { societes } from "@db/schema";
import { eq, like, desc } from "drizzle-orm";

export const societeRouter = createRouter({
  list: publicQuery.query(async () => {
    const db = getDb();
    return db.select().from(societes).orderBy(desc(societes.createdAt));
  }),

  getById: publicQuery
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const results = await db
        .select()
        .from(societes)
        .where(eq(societes.id, input.id));
      return results[0] || null;
    }),

  search: publicQuery
    .input(z.object({ query: z.string() }))
    .query(async ({ input }) => {
      const db = getDb();
      return db
        .select()
        .from(societes)
        .where(like(societes.nom, `%${input.query}%`))
        .orderBy(desc(societes.createdAt));
    }),

  create: publicQuery
    .input(
      z.object({
        nom: z.string().min(1),
        raisonSociale: z.string().min(1),
        ice: z.string().optional(),
        identifiantFiscal: z.string().optional(),
        rc: z.string().optional(),
        cnss: z.string().optional(),
        adresse: z.string().optional(),
        ville: z.string().optional(),
        telephone: z.string().optional(),
        email: z.string().optional(),
        typeSociete: z.string().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const result = await db.insert(societes).values(input);
      return { id: Number(result[0].insertId) };
    }),

  update: publicQuery
    .input(
      z.object({
        id: z.number(),
        nom: z.string().optional(),
        raisonSociale: z.string().optional(),
        ice: z.string().optional(),
        identifiantFiscal: z.string().optional(),
        rc: z.string().optional(),
        cnss: z.string().optional(),
        adresse: z.string().optional(),
        ville: z.string().optional(),
        telephone: z.string().optional(),
        email: z.string().optional(),
        typeSociete: z.string().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const { id, ...data } = input;
      const db = getDb();
      await db.update(societes).set(data).where(eq(societes.id, id));
      return { success: true };
    }),

  delete: publicQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db.delete(societes).where(eq(societes.id, input.id));
      return { success: true };
    }),
});
