"use client";

import { useState, useEffect } from "react";
import { Calculator, FileText, CheckCircle, AlertCircle, BookOpen } from "lucide-react";
import { apiFetch } from "../../../lib/api";

type Tab = "ledger" | "journal";

export default function AccountingPage() {
  const [activeTab, setActiveTab] = useState<Tab>("ledger");
  const [ledger, setLedger] = useState<any[]>([]);
  const [journal, setJournal] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [ledgerData, journalData] = await Promise.all([
        apiFetch("/accounting/ledger"),
        apiFetch("/accounting/journal")
      ]);
      setLedger(ledgerData || []);
      setJournal(journalData || []);
      setError("");
    } catch (err: any) {
      setError("Erreur lors du chargement des données. " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!mounted) return null;

  const totalLedgerDebit = ledger.reduce((acc, row) => acc + (row.total_debit || 0), 0);
  const totalLedgerCredit = ledger.reduce((acc, row) => acc + (row.total_credit || 0), 0);
  const isBalanced = Math.abs(totalLedgerDebit - totalLedgerCredit) < 0.01;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Comptabilité</h1>
          <p className="text-sm text-slate-500 mt-1">Consultez le Grand Livre et le Journal des écritures.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-600 rounded-lg flex items-center shadow-sm border border-red-100">
          <AlertCircle className="w-5 h-5 mr-3" />
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab("ledger")}
            className={`${activeTab === "ledger" ? "border-blue-500 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
          >
            <BookOpen className="w-4 h-4 mr-2" />
            Grand Livre (Balance)
          </button>
          <button
            onClick={() => setActiveTab("journal")}
            className={`${activeTab === "journal" ? "border-blue-500 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
          >
            <FileText className="w-4 h-4 mr-2" />
            Journal des écritures
          </button>
        </nav>
      </div>

      {isLoading ? (
        <div className="py-12 flex justify-center items-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : activeTab === "ledger" ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-sm font-medium text-slate-500 mb-1">Total Débit</p>
              <h3 className="text-2xl font-bold text-slate-800">{totalLedgerDebit.toLocaleString("fr-MA", { minimumFractionDigits: 2 })} MAD</h3>
            </div>
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-sm font-medium text-slate-500 mb-1">Total Crédit</p>
              <h3 className="text-2xl font-bold text-slate-800">{totalLedgerCredit.toLocaleString("fr-MA", { minimumFractionDigits: 2 })} MAD</h3>
            </div>
            <div className={`p-6 rounded-xl border shadow-sm flex flex-col justify-center ${isBalanced ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
              <div className="flex items-center space-x-2 mb-1">
                {isBalanced ? <CheckCircle className="w-5 h-5 text-green-600" /> : <AlertCircle className="w-5 h-5 text-red-600" />}
                <p className="text-sm font-medium">{isBalanced ? "Balance Équilibrée" : "Déséquilibre"}</p>
              </div>
              <h3 className="text-2xl font-bold">{Math.abs(totalLedgerDebit - totalLedgerCredit).toLocaleString("fr-MA", { minimumFractionDigits: 2 })} MAD {isBalanced ? "" : "d'écart"}</h3>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-sm font-medium">
                    <th className="py-3 px-6 text-left">N° Compte</th>
                    <th className="py-3 px-6 text-left">Intitulé</th>
                    <th className="py-3 px-6 text-right">Débit</th>
                    <th className="py-3 px-6 text-right">Crédit</th>
                    <th className="py-3 px-6 text-right">Solde</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ledger.map((acc, i) => (
                    <tr key={acc.id || i} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-6 text-sm font-bold text-slate-700">{acc.code}</td>
                      <td className="py-3 px-6 text-sm text-slate-600">{acc.name}</td>
                      <td className="py-3 px-6 text-sm text-slate-900 text-right font-medium">{(acc.total_debit || 0).toLocaleString("fr-MA", { minimumFractionDigits: 2 })}</td>
                      <td className="py-3 px-6 text-sm text-slate-900 text-right font-medium">{(acc.total_credit || 0).toLocaleString("fr-MA", { minimumFractionDigits: 2 })}</td>
                      <td className={`py-3 px-6 text-sm text-right font-bold ${acc.balance > 0 ? 'text-blue-600' : acc.balance < 0 ? 'text-rose-600' : 'text-slate-500'}`}>
                        {(acc.balance || 0).toLocaleString("fr-MA", { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  ))}
                  {ledger.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-slate-500">Aucune donnée trouvée.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {journal.length === 0 ? (
             <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 shadow-sm">
                Aucune écriture trouvée dans le journal.
             </div>
          ) : (
            <div className="space-y-4">
              {journal.map((entry) => (
                <div key={entry.id} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                  <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
                    <div className="flex items-center space-x-4">
                      <span className="text-sm font-bold text-slate-700 bg-white px-2 py-1 border border-slate-200 rounded shadow-sm">{entry.date}</span>
                      <span className="text-sm font-medium text-slate-800">{entry.description}</span>
                    </div>
                    {entry.reference && (
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">RÉF: {entry.reference}</span>
                    )}
                  </div>
                  <div className="p-0">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="text-xs text-slate-400 uppercase tracking-wider bg-white border-b border-slate-100">
                          <th className="py-2 px-4 w-24">Compte</th>
                          <th className="py-2 px-4">Libellé</th>
                          <th className="py-2 px-4 text-right w-32">Débit</th>
                          <th className="py-2 px-4 text-right w-32">Crédit</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {entry.lines?.map((line: any) => (
                          <tr key={line.id} className="hover:bg-slate-50">
                            <td className="py-2 px-4 text-sm font-medium text-slate-600">{line.account?.code}</td>
                            <td className="py-2 px-4 text-sm text-slate-500">{line.account?.name}</td>
                            <td className="py-2 px-4 text-sm text-slate-900 text-right">{line.debit > 0 ? line.debit.toLocaleString("fr-MA", { minimumFractionDigits: 2 }) : "-"}</td>
                            <td className="py-2 px-4 text-sm text-slate-900 text-right">{line.credit > 0 ? line.credit.toLocaleString("fr-MA", { minimumFractionDigits: 2 }) : "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
