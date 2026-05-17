import { useState } from "react";
import { trpc } from "@/providers/trpc";
import { useNavigate } from "react-router";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Building2,
  Plus,
  Search,
  FileText,
  Landmark,
  ArrowRight,
} from "lucide-react";

export default function SocietesPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    nom: "",
    raisonSociale: "",
    ice: "",
    identifiantFiscal: "",
    rc: "",
    cnss: "",
    adresse: "",
    ville: "",
    telephone: "",
    email: "",
    typeSociete: "SARL",
  });

  const utils = trpc.useUtils();
  const { data: societes, isLoading } = trpc.societe.list.useQuery();
  const createSociete = trpc.societe.create.useMutation({
    onSuccess: () => {
      utils.societe.list.invalidate();
      setOpen(false);
      setForm({
        nom: "",
        raisonSociale: "",
        ice: "",
        identifiantFiscal: "",
        rc: "",
        cnss: "",
        adresse: "",
        ville: "",
        telephone: "",
        email: "",
        typeSociete: "SARL",
      });
    },
  });

  const filtered = societes?.filter(
    (s) =>
      s.nom.toLowerCase().includes(search.toLowerCase()) ||
      s.raisonSociale?.toLowerCase().includes(search.toLowerCase()) ||
      s.ice?.includes(search)
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <Landmark className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Releveim</h1>
              <p className="text-xs text-gray-500">
                Cabinet Comptable — Gestion des dossiers
              </p>
            </div>
          </div>
          <div className="text-sm text-gray-500">
            {societes?.length || 0} dossier(s)
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Search + Add */}
        <div className="flex items-center gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Rechercher un dossier..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700">
                <Plus className="w-4 h-4 mr-2" />
                Nouveau Dossier
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Nouveau Dossier Societe</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div>
                  <Label>Nom *</Label>
                  <Input
                    value={form.nom}
                    onChange={(e) =>
                      setForm({ ...form, nom: e.target.value })
                    }
                    placeholder="AMAYE"
                  />
                </div>
                <div>
                  <Label>Raison Sociale *</Label>
                  <Input
                    value={form.raisonSociale}
                    onChange={(e) =>
                      setForm({ ...form, raisonSociale: e.target.value })
                    }
                    placeholder="STE AMAYE SARL"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>ICE</Label>
                    <Input
                      value={form.ice}
                      onChange={(e) =>
                        setForm({ ...form, ice: e.target.value })
                      }
                      placeholder="001542240000068"
                    />
                  </div>
                  <div>
                    <Label>ID Fiscal</Label>
                    <Input
                      value={form.identifiantFiscal}
                      onChange={(e) =>
                        setForm({ ...form, identifiantFiscal: e.target.value })
                      }
                      placeholder="50567940"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>RC</Label>
                    <Input
                      value={form.rc}
                      onChange={(e) =>
                        setForm({ ...form, rc: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <Label>CNSS</Label>
                    <Input
                      value={form.cnss}
                      onChange={(e) =>
                        setForm({ ...form, cnss: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div>
                  <Label>Type Societe</Label>
                  <select
                    value={form.typeSociete}
                    onChange={(e) =>
                      setForm({ ...form, typeSociete: e.target.value })
                    }
                    className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="SARL">SARL</option>
                    <option value="SARL AU">SARL AU</option>
                    <option value="SA">SA</option>
                    <option value="SAS">SAS</option>
                  </select>
                </div>
                <div>
                  <Label>Adresse</Label>
                  <Input
                    value={form.adresse}
                    onChange={(e) =>
                      setForm({ ...form, adresse: e.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Ville</Label>
                    <Input
                      value={form.ville}
                      onChange={(e) =>
                        setForm({ ...form, ville: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <Label>Telephone</Label>
                    <Input
                      value={form.telephone}
                      onChange={(e) =>
                        setForm({ ...form, telephone: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div>
                  <Label>Email</Label>
                  <Input
                    value={form.email}
                    onChange={(e) =>
                      setForm({ ...form, email: e.target.value })
                    }
                    type="email"
                  />
                </div>
                <Button
                  onClick={() => createSociete.mutate(form)}
                  disabled={!form.nom || !form.raisonSociale || createSociete.isPending}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {createSociete.isPending ? "Creation..." : "Creer le dossier"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Societes Grid */}
        {isLoading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : filtered?.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <Building2 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-lg">Aucun dossier trouve</p>
            <p className="text-sm">
              Creez votre premier dossier pour commencer
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered?.map((societe) => (
              <Card
                key={societe.id}
                className="cursor-pointer hover:shadow-lg transition-shadow group"
                onClick={() => navigate(`/societe/${societe.id}`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Building2 className="w-5 h-5 text-blue-600" />
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-blue-600 transition-colors" />
                  </div>
                  <CardTitle className="text-base mt-2">
                    {societe.nom}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-500 mb-2">
                    {societe.raisonSociale}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    {societe.typeSociete && (
                      <span className="bg-gray-100 px-2 py-0.5 rounded">
                        {societe.typeSociete}
                      </span>
                    )}
                    {societe.ice && (
                      <span className="bg-gray-100 px-2 py-0.5 rounded">
                        ICE: {societe.ice.slice(-6)}
                      </span>
                    )}
                  </div>
                  <div className="mt-3 flex items-center gap-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" /> Factures
                    </span>
                    <span className="flex items-center gap-1">
                      <Landmark className="w-3 h-3" /> Releves
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
