import { useParams, useNavigate } from "react-router";
import { trpc } from "@/providers/trpc";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Building2,
  ArrowLeft,
  FileText,
  Landmark,
  Receipt,
  AlertTriangle,
} from "lucide-react";
import FacturesTab from "@/sections/FacturesTab";
import RelevesTab from "@/sections/RelevesTab";

export default function SocieteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const societeId = parseInt(id || "0");

  const { data: societe, isLoading } = trpc.societe.getById.useQuery({
    id: societeId,
  });
  const { data: factures } = trpc.facture.listBySociete.useQuery({
    societeId,
  });
  const { data: releves } = trpc.releve.listBySociete.useQuery({
    societeId,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex justify-center items-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!societe) {
    return (
      <div className="min-h-screen bg-gray-50 flex justify-center items-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-amber-500" />
          <p className="text-lg text-gray-700">Dossier non trouve</p>
        </div>
      </div>
    );
  }

  const nbFacturesClients =
    factures?.filter((f) => f.type === "client").length || 0;
  const nbFacturesFournisseurs =
    factures?.filter((f) => f.type === "fournisseur").length || 0;
  const nbReleves = releves?.length || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3 mb-3">
            <Button variant="ghost" size="sm" onClick={() => navigate("/")} className="gap-1">
              <ArrowLeft className="w-4 h-4" />
              Retour
            </Button>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold">{societe.nom}</h1>
                <p className="text-sm text-gray-500">
                  {societe.raisonSociale} {societe.typeSociete && `— ${societe.typeSociete}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              {societe.ice && (
                <span className="bg-gray-100 px-3 py-1 rounded-full">ICE: {societe.ice}</span>
              )}
              {societe.identifiantFiscal && (
                <span className="bg-gray-100 px-3 py-1 rounded-full">IF: {societe.identifiantFiscal}</span>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                  <Receipt className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{nbFacturesClients}</p>
                  <p className="text-xs text-gray-500">Factures Clients</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{nbFacturesFournisseurs}</p>
                  <p className="text-xs text-gray-500">Factures Fournisseurs</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Landmark className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{nbReleves}</p>
                  <p className="text-xs text-gray-500">Releves Bancaires</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Receipt className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {societe.cnss ? "Actif" : "—"}
                  </p>
                  <p className="text-xs text-gray-500">CNSS</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="factures" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="factures" className="gap-2">
              <FileText className="w-4 h-4" />
              Factures
            </TabsTrigger>
            <TabsTrigger value="releves" className="gap-2">
              <Landmark className="w-4 h-4" />
              Releves Bancaires
            </TabsTrigger>
          </TabsList>

          <TabsContent value="factures" className="mt-4">
            <FacturesTab societeId={societeId} nomSociete={societe.nom} />
          </TabsContent>

          <TabsContent value="releves" className="mt-4">
            <RelevesTab
              societeId={societeId}
              nomSociete={societe.nom}
              releves={releves || []}
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
