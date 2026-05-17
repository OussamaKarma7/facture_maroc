import { useState } from "react";
import { trpc } from "@/providers/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Upload,
  Receipt,
  FileText,
  Loader2,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";

interface Props {
  societeId: number;
  nomSociete: string;
}

export default function FacturesTab({ societeId, nomSociete: _nomSociete }: Props) {
  const [activeTab, setActiveTab] = useState("clients");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadType, setUploadType] = useState<"client" | "fournisseur">("client");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);

  const utils = trpc.useUtils();
  const typeFilter = activeTab === "clients" ? "client" : "fournisseur";

  const { data: factures, isLoading } =
    trpc.facture.listBySocieteAndType.useQuery({
      societeId,
      type: typeFilter,
    });

  const uploadMutation = trpc.facture.uploadAndExtract.useMutation({
    onSuccess: (data) => {
      setUploading(false);
      setUploadResult(data);
      if (data.success) {
        utils.facture.listBySocieteAndType.invalidate({
          societeId,
          type: typeFilter,
        });
      }
    },
    onError: (err) => {
      setUploading(false);
      setUploadResult({ success: false, error: err.message });
    },
  });

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadResult(null);

    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(",")[1];
      uploadMutation.mutate({
        societeId,
        type: uploadType,
        base64,
        filename: file.name,
        mimeType: file.type,
      });
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const input = document.createElement("input");
      input.type = "file";
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      handleFileUpload({ target: input } as any);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-auto"
        >
          <TabsList>
            <TabsTrigger value="clients" className="gap-2">
              <Receipt className="w-4 h-4" />
              Clients ({factures?.filter((f) => f.type === "client").length || 0})
            </TabsTrigger>
            <TabsTrigger value="fournisseurs" className="gap-2">
              <FileText className="w-4 h-4" />
              Fournisseurs ({factures?.filter((f) => f.type === "fournisseur").length || 0})
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
          <DialogTrigger asChild>
            <Button className="bg-blue-600 hover:bg-blue-700 gap-2">
              <Upload className="w-4 h-4" />
              Importer Facture
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Importer une Facture</DialogTitle>
            </DialogHeader>

            <div className="py-4">
              <Label className="mb-2 block">Type de facture</Label>
              <div className="flex gap-2 mb-4">
                <Button
                  variant={uploadType === "client" ? "default" : "outline"}
                  onClick={() => setUploadType("client")}
                  className="flex-1 gap-2"
                  type="button"
                >
                  <Receipt className="w-4 h-4" />
                  Client
                </Button>
                <Button
                  variant={
                    uploadType === "fournisseur" ? "default" : "outline"
                  }
                  onClick={() => setUploadType("fournisseur")}
                  className="flex-1 gap-2"
                  type="button"
                >
                  <FileText className="w-4 h-4" />
                  Fournisseur
                </Button>
              </div>

              <div
                className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() =>
                  document.getElementById("facture-upload")?.click()
                }
              >
                <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400" />
                <p className="text-sm text-gray-600 mb-1">
                  Glissez-deposez une facture ici
                </p>
                <p className="text-xs text-gray-400">
                  ou cliquez pour parcourir (PDF, JPG, PNG)
                </p>
                <Input
                  id="facture-upload"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </div>

              {uploading && (
                <div className="flex items-center justify-center gap-2 mt-4 text-blue-600">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">
                    Extraction en cours avec Gemini AI...
                  </span>
                </div>
              )}

              {uploadResult && (
                <div className="mt-4 p-3 rounded-lg bg-gray-50">
                  {uploadResult.success ? (
                    <div>
                      <div className="flex items-center gap-2 text-green-600 mb-2">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          Extraction reussie
                        </span>
                      </div>
                      {uploadResult.extracted && (
                        <div className="text-xs text-gray-600 space-y-1">
                          <p>
                            <strong>N°:</strong>{" "}
                            {uploadResult.extracted.numero_facture}
                          </p>
                          <p>
                            <strong>Tiers:</strong>{" "}
                            {uploadResult.extracted.nom_client_fournisseur}
                          </p>
                          <p>
                            <strong>TTC:</strong>{" "}
                            {uploadResult.extracted.montant_ttc?.toFixed(2)} MAD
                          </p>
                          <p>
                            <strong>Date:</strong>{" "}
                            {uploadResult.extracted.date_facture}
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-red-600">
                      <AlertTriangle className="w-4 h-4" />
                      <span className="text-sm">
                        {uploadResult.error || "Extraction echouee"}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Factures List */}
      {isLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        </div>
      ) : factures?.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <FileText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500">
              Aucune facture{" "}
              {activeTab === "clients" ? "client" : "fournisseur"}
            </p>
            <p className="text-sm text-gray-400 mt-1">
              Importez des factures pour les associer aux transactions
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {factures?.map((f) => (
            <Card
              key={f.id}
              className="hover:shadow-md transition-shadow"
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          f.type === "client"
                            ? "bg-green-100 text-green-700"
                            : "bg-orange-100 text-orange-700"
                        }`}
                      >
                        {f.type === "client" ? "Client" : "Fournisseur"}
                      </span>
                      {(f as any).estAcompte && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                          Acompte
                        </span>
                      )}
                    </div>
                    <p className="font-medium text-sm truncate">
                      {f.numeroFacture}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {f.nomClientFournisseur}
                    </p>
                    {f.designation && (
                      <p className="text-xs text-gray-400 truncate mt-0.5">
                        {f.designation}
                      </p>
                    )}
                  </div>
                  <div className="text-right ml-4">
                    <p className="font-semibold text-sm">
                      {f.montantTtc
                        ? `${parseFloat(f.montantTtc).toFixed(2)} MAD`
                        : "—"}
                    </p>
                    {f.dateFacture && (
                      <p className="text-xs text-gray-400">
                        {new Date(f.dateFacture).toLocaleDateString("fr-FR")}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  {f.montantHt && (
                    <span>HT: {parseFloat(f.montantHt).toFixed(2)}</span>
                  )}
                  {f.montantTva && (
                    <span>TVA: {parseFloat(f.montantTva).toFixed(2)}</span>
                  )}
                  {f.tauxTva && <span>({f.tauxTva}%)</span>}
                  {f.iceClientFournisseur && (
                    <span className="truncate">ICE: {f.iceClientFournisseur}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
