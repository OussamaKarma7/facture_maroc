import { useState } from "react";
import { useNavigate } from "react-router";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Upload,
  Landmark,
  Loader2,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Trash2,
  Calendar,
} from "lucide-react";

interface Props {
  societeId: number;
  nomSociete: string;
  releves: any[];
}

export default function RelevesTab({ societeId, nomSociete: _nomSociete, releves }: Props) {
  const navigate = useNavigate();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [bankHint, setBankHint] = useState("AUTO");

  const utils = trpc.useUtils();

  const uploadMutation = trpc.releve.uploadAndExtract.useMutation({
    onSuccess: (data) => {
      setUploading(false);
      setUploadResult(data);
      if (data.success) {
        utils.releve.listBySociete.invalidate({ societeId });
      }
    },
    onError: (err) => {
      setUploading(false);
      setUploadResult({ success: false, error: err.message });
    },
  });

  const deleteMutation = trpc.releve.delete.useMutation({
    onSuccess: () => {
      utils.releve.listBySociete.invalidate({ societeId });
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
        base64,
        filename: file.name,
        bankHint: bankHint === "AUTO" ? undefined : bankHint,
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
        <h3 className="text-sm font-medium text-gray-500">
          {releves.length} releve(s) bancaire(s)
        </h3>
        <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
          <DialogTrigger asChild>
            <Button className="bg-blue-600 hover:bg-blue-700 gap-2">
              <Upload className="w-4 h-4" />
              Scanner Releve
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Scanner un Releve Bancaire</DialogTitle>
            </DialogHeader>

            <div className="py-4 space-y-4">
              <div>
                <Label className="mb-2 block">Banque (optionnel)</Label>
                <Select value={bankHint} onValueChange={setBankHint}>
                  <SelectTrigger>
                    <SelectValue placeholder="Detection automatique" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="AUTO">Detection automatique</SelectItem>
                    <SelectItem value="BANQUE POPULAIRE">
                      Banque Populaire
                    </SelectItem>
                    <SelectItem value="ATTIJARIWAFA BANK">
                      Attijariwafa Bank
                    </SelectItem>
                    <SelectItem value="CIH">CIH Bank</SelectItem>
                    <SelectItem value="BMCE">BMCE Bank of Africa</SelectItem>
                    <SelectItem value="BMCI">BMCI</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div
                className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() =>
                  document.getElementById("releve-upload")?.click()
                }
              >
                <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400" />
                <p className="text-sm text-gray-600 mb-1">
                  Glissez-deposez un releve ici
                </p>
                <p className="text-xs text-gray-400">
                  ou cliquez pour parcourir (PDF, JPG, PNG)
                </p>
                <Input
                  id="releve-upload"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </div>

              {uploading && (
                <div className="flex items-center justify-center gap-2 text-blue-600">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">
                    Extraction OCR en cours... (peut prendre 1-2 min)
                  </span>
                </div>
              )}

              {uploadResult && (
                <div className="p-3 rounded-lg bg-gray-50">
                  {uploadResult.success ? (
                    <div>
                      <div className="flex items-center gap-2 text-green-600 mb-2">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          Extraction reussie
                        </span>
                      </div>
                      <div className="text-xs text-gray-600 space-y-1">
                        <p>
                          <strong>Banque:</strong> {uploadResult.banque}
                        </p>
                        <p>
                          <strong>Titulaire:</strong> {uploadResult.titulaire}
                        </p>
                        <p>
                          <strong>Transactions:</strong>{" "}
                          {uploadResult.nbTransactions} lignes
                        </p>
                        <p>
                          <strong>Solde initial:</strong>{" "}
                          {uploadResult.soldeInitial?.toFixed(2)} MAD
                        </p>
                        <p>
                          <strong>Solde final:</strong>{" "}
                          {uploadResult.soldeFinal?.toFixed(2)} MAD
                        </p>
                        {uploadResult.verificationOk && (
                          <p className="text-green-600">
                            Verification solde: OK
                          </p>
                        )}
                        {uploadResult.categorized?.length > 0 && (
                          <p className="text-blue-600">
                            {uploadResult.categorized.length} transactions
                            categorisees
                          </p>
                        )}
                      </div>
                      <Button
                        className="mt-3 w-full bg-blue-600 hover:bg-blue-700"
                        onClick={() => {
                          setUploadOpen(false);
                          navigate(`/releve/${uploadResult.releveId}`);
                        }}
                      >
                        Voir les resultats
                      </Button>
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

      {/* Releves List */}
      {releves.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Landmark className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500">Aucun releve bancaire</p>
            <p className="text-sm text-gray-400 mt-1">
              Scannez un releve pour extraire les transactions
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {releves.map((r) => (
            <Card
              key={r.id}
              className="hover:shadow-md transition-shadow cursor-pointer group"
              onClick={() => navigate(`/releve/${r.id}`)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Landmark className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-sm">{r.banque}</p>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            r.status === "completed"
                              ? "bg-green-100 text-green-700"
                              : r.status === "processing"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {r.status === "completed"
                            ? "Traite"
                            : r.status === "processing"
                              ? "En cours"
                              : "En attente"}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                        <span>{r.titulaire}</span>
                        {r.rib && (
                          <span className="font-mono">RIB: ...{r.rib.slice(-4)}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                        {r.dateDebut && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(r.dateDebut).toLocaleDateString("fr-FR")}
                          </span>
                        )}
                        {r.dateFin && (
                          <span>
                            au{" "}
                            {new Date(r.dateFin).toLocaleDateString("fr-FR")}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-semibold">
                        {r.soldeFinal
                          ? `${parseFloat(r.soldeFinal).toFixed(2)} MAD`
                          : "—"}
                      </p>
                      {r.totalDebits && r.totalCredits && (
                        <p className="text-xs text-gray-400">
                          D: {parseFloat(r.totalDebits).toFixed(0)} / C:{" "}
                          {parseFloat(r.totalCredits).toFixed(0)}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-gray-400 hover:text-red-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm("Supprimer ce releve ?")) {
                          deleteMutation.mutate({ id: r.id });
                        }
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
