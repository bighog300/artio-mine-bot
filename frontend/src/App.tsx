import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/shared/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Sources } from "@/pages/Sources";
import { SourceDetail } from "@/pages/SourceDetail";
import { Records } from "@/pages/Records";
import { RecordDetail } from "@/pages/RecordDetail";
import { Pages } from "@/pages/Pages";
import { Images } from "@/pages/Images";
import { Export } from "@/pages/Export";
import { Settings } from "@/pages/Settings";
import { Logs } from "@/pages/Logs";
import { AdminReview } from "@/pages/AdminReview";
import { DuplicateResolution } from "@/pages/DuplicateResolution";
import { SemanticExplorer } from "@/pages/SemanticExplorer";
import { AuditTrail } from "@/pages/AuditTrail";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/sources/:id" element={<SourceDetail />} />
          <Route path="/records" element={<Records />} />
          <Route path="/admin-review" element={<AdminReview />} />
          <Route path="/duplicates" element={<DuplicateResolution />} />
          <Route path="/semantic" element={<SemanticExplorer />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/records/:id" element={<RecordDetail />} />
          <Route path="/pages" element={<Pages />} />
          <Route path="/images" element={<Images />} />
          <Route path="/export" element={<Export />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
