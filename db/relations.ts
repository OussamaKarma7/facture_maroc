import { relations } from "drizzle-orm";
import {
  societes,
  factures,
  relevesBancaires,
  transactions,
  matchings,
} from "./schema";

export const societesRelations = relations(societes, ({ many }) => ({
  factures: many(factures),
  relevesBancaires: many(relevesBancaires),
}));

export const facturesRelations = relations(factures, ({ one, many }) => ({
  societe: one(societes, {
    fields: [factures.societeId],
    references: [societes.id],
  }),
  matchings: many(matchings),
}));

export const relevesBancairesRelations = relations(
  relevesBancaires,
  ({ one, many }) => ({
    societe: one(societes, {
      fields: [relevesBancaires.societeId],
      references: [societes.id],
    }),
    transactions: many(transactions),
  })
);

export const transactionsRelations = relations(transactions, ({ one, many }) => ({
  releve: one(relevesBancaires, {
    fields: [transactions.releveId],
    references: [relevesBancaires.id],
  }),
  matchings: many(matchings),
}));

export const matchingsRelations = relations(matchings, ({ one }) => ({
  transaction: one(transactions, {
    fields: [matchings.transactionId],
    references: [transactions.id],
  }),
  facture: one(factures, {
    fields: [matchings.factureId],
    references: [factures.id],
  }),
}));
