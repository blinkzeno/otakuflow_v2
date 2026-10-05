import { BrowserRouter, Route, Routes } from "react-router-dom";
import ProjectsPage from "./pages/ProjectsPage.tsx";
import WorkspacePage from "./pages/WorkspacePage.tsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/p/:id" element={<WorkspacePage />} />
      </Routes>
    </BrowserRouter>
  );
}
