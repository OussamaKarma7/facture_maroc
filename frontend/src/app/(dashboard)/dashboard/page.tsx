"use client";

import { useEffect, useState } from "react";
import { 
  DollarSign, 
  CreditCard, 
  TrendingUp, 
  AlertCircle,
  Activity
} from "lucide-react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { apiFetch } from "../../../lib/api";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  // MOCK DATA for MVP (Simulating API fetch)
  useEffect(() => {
    setMounted(true);
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const dashboardData = await apiFetch("/reports/dashboard");
      setData(dashboardData);
    } catch (err: any) {
      console.error("Failed to fetch dashboard data:", err);
      // Fallback for demonstration if API fails
      setData({
        kpis: {
          monthly_revenue: 0,
          unpaid_invoices_count: 0,
          unpaid_invoices_total: 0,
          total_expenses: 0,
          vat_due: 0
        },
        revenue_chart: [],
        expense_chart: []
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading || !mounted) return <div className="p-8 text-center text-slate-500">Chargement du tableau de bord...</div>;

  const lineChartData = {
    labels: data?.revenue_chart ? data.revenue_chart.map((d: any) => d.label) : [],
    datasets: [
      {
        label: 'Revenus HT (MAD)',
        data: data?.revenue_chart ? data.revenue_chart.map((d: any) => d.value) : [],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
        tension: 0.3
      }
    ],
  };

  const barChartData = {
    labels: data?.expense_chart ? data.expense_chart.map((d: any) => d.label) : [],
    datasets: [
      {
        label: 'Dépenses (MAD)',
        data: data?.expense_chart ? data.expense_chart.map((d: any) => d.value) : [],
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
      }
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' as const },
    },
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Tableau de bord</h1>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          Télécharger le rapport
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm flex flex-col hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-medium text-slate-500">Chiffre d'affaires mensuel</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">
                {data.kpis.monthly_revenue.toLocaleString("fr-MA")} <span className="text-sm font-normal text-slate-500">MAD</span>
              </h3>
            </div>
            <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <p className="text-xs text-green-600 flex items-center font-medium">
            <TrendingUp className="w-3 h-3 mr-1" /> +12,5% par rapport au mois dernier
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm flex flex-col hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-medium text-slate-500">Factures impayées</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">
                {data.kpis.unpaid_invoices_total.toLocaleString("fr-MA")} <span className="text-sm font-normal text-slate-500">MAD</span>
              </h3>
            </div>
            <div className="p-3 bg-red-50 text-red-600 rounded-lg">
              <AlertCircle className="w-5 h-5" />
            </div>
          </div>
          <p className="text-xs text-red-600 font-medium">
            {data.kpis.unpaid_invoices_count} factures en attente
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm flex flex-col hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-medium text-slate-500">Dépenses totales</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">
                {data.kpis.total_expenses.toLocaleString("fr-MA")} <span className="text-sm font-normal text-slate-500">MAD</span>
              </h3>
            </div>
            <div className="p-3 bg-orange-50 text-orange-600 rounded-lg">
              <CreditCard className="w-5 h-5" />
            </div>
          </div>
          <p className="text-xs text-slate-500 flex items-center">
            Ce mois-ci
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm flex flex-col hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm font-medium text-slate-500">TVA due</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">
                {data.kpis.vat_due.toLocaleString("fr-MA")} <span className="text-sm font-normal text-slate-500">MAD</span>
              </h3>
            </div>
            <div className="p-3 bg-purple-50 text-purple-600 rounded-lg">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <p className="text-xs text-slate-500 flex items-center">
            Estimée pour la période en cours
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Tendance des revenus</h3>
          <div className="h-72">
            <Line options={chartOptions} data={lineChartData} />
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Analyse des dépenses</h3>
          <div className="h-72">
            <Bar options={chartOptions} data={barChartData} />
          </div>
        </div>
      </div>
      
    </div>
  );
}
