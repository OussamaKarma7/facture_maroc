import { createRouter, publicQuery } from "./middleware";
import { societeRouter } from "./routers/societe";
import { factureRouter } from "./routers/facture";
import { releveRouter } from "./routers/releve";
import { matchingRouter } from "./routers/matching";
import { exportRouter } from "./routers/export";

export const appRouter = createRouter({
  ping: publicQuery.query(() => ({ ok: true, ts: Date.now() })),

  societe: societeRouter,
  facture: factureRouter,
  releve: releveRouter,
  matching: matchingRouter,
  export: exportRouter,
});

export type AppRouter = typeof appRouter;
