import { useState } from "react";
import { useParams, useNavigate } from "react-router";
import { trpc } from "@/providers/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowLeft,
  Landmark,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Download,
  Link2,
  Receipt,
  FileSpreadsheet,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function ReleveDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const releveId = parseInt(id || "0");

  const { data: releve, isLoading: releveLoading } =
    trpc.releve.getById.useQuery({ id: releveId });
  const {
    data: transactions,
    isLoading: txLoading,
  } = trpc.releve.getTransactions.useQuery({ releveId });
  const { data: matchings } = trpc.matching.listByReleve.useQuery({
    releveId,
  });

  const [matchingLoading, setMatchingLoading] = useState(false);
  const [showExports, setShowExports] = useState(false);

  const utils = trpc.useUtils();

  const autoMatchMutation = trpc.matching.autoMatch.useMutation({
    onMutate: () => setMatchingLoading(true),
    onSettled: () => {
      setMatchingLoading(false);
      utils.matching.listByReleve.invalidate({ releveId });
    },
  });

  const ediMutation = trpc.export.generateEdi.useMutation();
  const sageMutation = trpc.export.generateSage.useMutation();
  const csvMutation = trpc.export.generateCsv.useMutation();

  const handleExport = async (
    type: "edi" | "sage" | "csv",
    annee?: number,
    mois?: number
  ) => {
    let result: any;
    if (type === "edi" && annee && mois) {
      result = await ediMutation.mutateAsync({
        societeId: releve?.societeId || 0,
        releveId,
        annee,
        mois,
      });
    } else if (type === "sage") {
      result = await sageMutation.mutateAsync({ releveId });
    } else {
      result = await csvMutation.mutateAsync({ releveId });
    }

    if (result?.success && result.data) {
      const blob = new Blob(
        [Uint8Array.from(atob(result.data), (c) => c.charCodeAt(0))],
        {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const getCategoryColor = (cat?: string | null) => {
    switch (cat) {
      case "ACHAT":
        return "bg-orange-100 text-orange-700";
      case "VENTE":
        return "bg-green-100 text-green-700";
      case "CHARGE":
        return "bg-red-100 text-red-700";
      case "PRODUIT":
        return "bg-blue-100 text-blue-700";
      case "FINANCE":
        return "bg-purple-100 text-purple-700";
      case "IMMOBILISATION":
        return "bg-amber-100 text-amber-700";
      default:
        return "bg-gray-100 text-gray-600";
    }
  };

  if (releveLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex justify-center items-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!releve) {
    return (
      <div className="min-h-screen bg-gray-50 flex justify-center items-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-amber-500" />
          <p className="text-lg">Releve non trouve</p>
          <Button variant="link" onClick={() => navigate(-1)}>
            Retour
          </Button>
        </div>
      </div>
    );
  }

  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3 mb-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              className="gap-1"
            >
              <ArrowLeft className="w-4 h-4" />
              Retour
            </Button>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <Landmark className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-xl font-bold">{releve.banque}</h1>
                <p className="text-sm text-gray-500">
                  {releve.titulaire} {releve.rib && `— RIB: ...${releve.rib.slice(-6)}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => {
                  const socId = releve.societeId;
                  autoMatchMutation.mutate({
                    releveId,
                    societeId: socId,
                  });
                }}
                disabled={matchingLoading}
              >
                {matchingLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Link2 className="w-4 h-4" />
                )}
                Matching Auto
              </Button>
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => setShowExports(!showExports)}
              >
                <Download className="w-4 h-4" />
                Exports
                {showExports ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </Button>
            </div>
          </div>

          {/* Info bar */}
          <div className="flex items-center gap-6 mt-4 text-sm text-gray-500">
            <span>
              <strong>Solde Initial:</strong>{" "}
              {releve.soldeInitial
                ? `${parseFloat(releve.soldeInitial).toFixed(2)} MAD`
                : "—"}
            </span>
            <span>
              <strong>Solde Final:</strong>{" "}
              {releve.soldeFinal
                ? `${parseFloat(releve.soldeFinal).toFixed(2)} MAD`
                : "—"}
            </span>
            <span>
              <strong>Periode:</strong>{" "}
              {releve.dateDebut
                ? new Date(releve.dateDebut).toLocaleDateString("fr-FR")
                : "—"}{" "}
              -{" "}
              {releve.dateFin
                ? new Date(releve.dateFin).toLocaleDateString("fr-FR")
                : "—"}
            </span>
            <span>
              <strong>Transactions:</strong> {transactions?.length || 0}
            </span>
          </div>

          {/* Export options */}
          {showExports && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg flex items-center gap-3">
              <Button
                size="sm"
                variant="outline"
                className="gap-2"
                onClick={() => handleExport("edi", currentYear, currentMonth)}
                disabled={ediMutation.isPending}
              >
                <FileSpreadsheet className="w-4 h-4" />
                EDI TVA ({currentMonth}/{currentYear})
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="gap-2"
                onClick={() => handleExport("sage")}
                disabled={sageMutation.isPending}
              >
                <FileSpreadsheet className="w-4 h-4" />
                Journal Sage
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="gap-2"
                onClick={() => handleExport("csv")}
                disabled={csvMutation.isPending}
              >
                <Download className="w-4 h-4" />
                CSV Transactions
              </Button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Matchings summary */}
        {matchings && matchings.length > 0 && (
          <Card className="mb-4 bg-blue-50 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-blue-800">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">
                  {matchings.length} transaction(s) associee(s) a des factures
                </span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Transactions Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Receipt className="w-5 h-5" />
              Transactions Extraites
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {txLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              </div>
            ) : !transactions?.length ? (
              <div className="py-10 text-center text-gray-500">
                Aucune transaction extraite
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="w-12 text-xs">#</TableHead>
                      <TableHead className="text-xs">Date Op.</TableHead>
                      <TableHead className="text-xs">Date Val.</TableHead>
                      <TableHead className="text-xs">Reference</TableHead>
                      <TableHead className="text-xs min-w-[200px]">
                        Nature / Libelle
                      </TableHead>
                      <TableHead className="text-xs text-right">Debit</TableHead>
                      <TableHead className="text-xs text-right">Credit</TableHead>
                      <TableHead className="text-xs">Code Comptable</TableHead>
                      <TableHead className="text-xs">Categorie</TableHead>
                      <TableHead className="text-xs">Facture</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {transactions?.map((tx) => {
                      const matching = matchings?.find(
                        (m) => m.transaction?.ligne === tx.ligne
                      );
                      return (
                        <TableRow key={tx.id} className="hover:bg-gray-50">
                          <TableCell className="text-xs font-medium">
                            {tx.ligne}
                          </TableCell>
                          <TableCell className="text-xs">
                            {tx.dateOperation
                              ? new Date(tx.dateOperation).toLocaleDateString(
                                  "fr-FR"
                                )
                              : "—"}
                          </TableCell>
                          <TableCell className="text-xs">
                            {tx.dateValeur
                              ? new Date(tx.dateValeur).toLocaleDateString(
                                  "fr-FR"
                                )
                              : "—"}
                          </TableCell>
                          <TableCell className="text-xs font-mono">
                            {tx.reference || "—"}
                          </TableCell>
                          <TableCell className="text-xs max-w-[250px] truncate">
                            {tx.natureOperation}
                          </TableCell>
                          <TableCell className="text-xs text-right text-red-600">
                            {tx.montantDebit
                              ? parseFloat(tx.montantDebit).toFixed(2)
                              : "—"}
                          </TableCell>
                          <TableCell className="text-xs text-right text-green-600">
                            {tx.montantCredit
                              ? parseFloat(tx.montantCredit).toFixed(2)
                              : "—"}
                          </TableCell>
                          <TableCell className="text-xs">
                            {tx.codeComptable ? (
                              <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded text-xs">
                                {tx.codeComptable}
                              </span>
                            ) : (
                              "—"
                            )}
                          </TableCell>
                          <TableCell>
                            {tx.categorieComptable ? (
                              <Badge
                                variant="secondary"
                                className={`text-xs ${getCategoryColor(tx.categorieComptable)}`}
                              >
                                {tx.categorieComptable}
                              </Badge>
                            ) : (
                              "—"
                            )}
                          </TableCell>
                          <TableCell>
                            {matching ? (
                              <Badge
                                variant="outline"
                                className="text-xs gap-1 border-green-300 text-green-700"
                              >
                                <CheckCircle className="w-3 h-3" />
                                {matching.facture?.numeroFacture}
                              </Badge>
                            ) : (
                              <span className="text-xs text-gray-300">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
