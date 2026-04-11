"use client";

import Link from "next/link";
import { 
  Home, 
  Users, 
  Package, 
  FileText, 
  CreditCard, 
  Settings, 
  BarChart2, 
  Calculator,
  LogOut,
  FolderOpen,
  ShoppingCart,
  Bot
} from "lucide-react";

import { useRouter } from "next/navigation";
import { removeToken } from "../../lib/auth";

export default function Sidebar() {
  const router = useRouter();
  
  const handleLogout = () => {
    removeToken();
    router.push('/login');
  };

  const routes = [
    { name: "Tableau de bord", icon: Home, path: "/dashboard" },
    { name: "Clients", icon: Users, path: "/clients" },
    { name: "Produits", icon: Package, path: "/products" },
    { name: "Devis", icon: FileText, path: "/quotes" },
    { name: "Factures", icon: FileText, path: "/invoices" },
    { name: "Paiements", icon: CreditCard, path: "/payments" },
    { name: "Achats", icon: ShoppingCart, path: "/expenses" },
    { name: "Comptabilité", icon: Calculator, path: "/accounting" },
    { name: "Fiscalité", icon: BarChart2, path: "/taxes" },
    { name: "Rapports", icon: BarChart2, path: "/reports" },
    { name: "Documents", icon: FolderOpen, path: "/documents" },
    { name: "Assistant IA", icon: Bot, path: "/assistant" },
    { name: "Paramètres", icon: Settings, path: "/settings" },
  ];

  return (
    <div className="w-64 bg-slate-900 border-r h-screen text-slate-300 flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold font-sans text-white tracking-wider flex items-center space-x-2">
          <Calculator className="h-6 w-6 text-blue-500" />
          <span>Compta<span className="text-blue-500">SaaS</span></span>
        </h1>
      </div>
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        <ul className="space-y-1 px-4">
            {routes.map((route, idx) => (
                <li key={idx}>
                  <Link href={route.path}>
                    <div className="flex items-center space-x-3 p-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors cursor-pointer group">
                      <route.icon className="h-5 w-5 text-slate-400 group-hover:text-blue-400" />
                      <span className="font-medium text-sm">{route.name}</span>
                    </div>
                  </Link>
                </li>
            ))}
        </ul>
      </div>
      <div className="p-4 border-t border-slate-800">
        <button 
          onClick={handleLogout}
          className="flex items-center space-x-2 text-sm text-slate-400 hover:text-white w-full p-2 rounded-lg hover:bg-slate-800 transition-colors"
        >
            <LogOut className="h-4 w-4" />
            <span>Déconnexion</span>
        </button>
      </div>
    </div>
  );
}
