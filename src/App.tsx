import { Routes, Route } from "react-router";
import SocietesPage from "./pages/SocietesPage";
import SocieteDetailPage from "./pages/SocieteDetailPage";
import ReleveDetailPage from "./pages/ReleveDetailPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SocietesPage />} />
      <Route path="/societe/:id" element={<SocieteDetailPage />} />
      <Route path="/releve/:id" element={<ReleveDetailPage />} />
    </Routes>
  );
}
