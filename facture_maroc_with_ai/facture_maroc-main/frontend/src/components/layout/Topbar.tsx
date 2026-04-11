import { Bell, Search, User } from "lucide-react";

export default function Topbar() {
  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6 shrink-0 z-10 sticky top-0">
      <div className="flex items-center w-96 bg-slate-100 rounded-lg px-3 py-2 text-slate-500 focus-within:ring-2 focus-within:ring-blue-500 transition-shadow">
        <Search className="h-4 w-4 mr-2" />
        <input type="text" placeholder="Rechercher des factures, clients..." className="bg-transparent border-none outline-none text-sm w-full placeholder-slate-400 placeholder-slate-400 text-slate-500"
        />
      </div>

      <div className="flex items-center space-x-4">
        <button className="relative p-2 text-slate-400 hover:text-slate-600 transition-colors rounded-full hover:bg-slate-100">
          <Bell className="h-5 w-5" />
          <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 border border-white"></span>
        </button>
        
        <div className="flex items-center space-x-3 pl-4 border-l border-slate-200 cursor-pointer">
          <div className="text-right hidden md:block">
            <p className="text-sm font-semibold text-slate-700">Admin User</p>
            <p className="text-xs text-slate-500">My Company SARL</p>
          </div>
          <div className="h-9 w-9 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold">
            <User className="h-5 w-5" />
          </div>
        </div>
      </div>
    </header>
  );
}
